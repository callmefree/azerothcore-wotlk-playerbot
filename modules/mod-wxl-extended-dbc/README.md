# mod-wxl-dbc

## Ascension fork integration

This fork invokes `OnAfterLoadDBCStores()` inside `LoadDBCStores()`, immediately after
all file and SQL stores load and before derived indexes and validation. Do not also
add the hook in `World.cpp`: that would inject every continuation twice. Taxi,
transport, map difficulty, spell difficulty and other secondary lookups therefore
build from the overlaid stores. `RebuildDbcDerivedIndexes()` remains available for
the subset of lookups it explicitly clears, but this module does not call it.

The injector accepts one-column game tables using implicit row IDs, matching this
core's base loader. CharacterFacialHairStyles and CharHairGeosets are client-only
here and are not registered server stores. Unregistered continuation tables are
skipped by the server; they can still be used by the client extension.

The patch examples below describe the original integration; use the hook location
above for this fork.

### WorldMapArea and offline compatibility audit

`WorldMapArea` is indexed by its actual row ID, including SQL overlays. Its signed
`area_id` preserves Ascension's `-1` sentinel. These map-only rows remain distinct
in the store; they do not create a synthetic AreaTable entry or a zone coordinate
lookup. Existing zone-coordinate consumers use a separate area-ID lookup rebuilt
after injection. When different WorldMapArea rows share an area ID, the highest
row ID supplies that zone lookup; all rows remain accessible in the primary store.

Run the read-only audit from the repository root:

```sh
python modules/mod-wxl-extended-dbc/tools/audit_ascension.py --data _data
python -m unittest discover -s modules/mod-wxl-extended-dbc/tools -p test_audit_ascension.py
```

Add `--details` to list affected spell and achievement IDs. The audit targets the
v20 baseline plus `*.dbc1-ascension`, not arbitrary manifest/tier combinations.
It checks file layouts, strings, indexes, spell dispatch bounds, talent pages,
taxi index bounds, and selected cross-table references. SQL overlays and runtime
scripts are outside its scope. Missing references are reported separately from
unsafe loader values; a zero exit status is not proof of startup or gameplay parity.

Effect 193 remains a placeholder without an established implementation contract.
Aura 173 is unused in the supplied Ascension Spell table. Null aura handlers can
also represent mechanics queried elsewhere and do not alone establish a missing
implementation. Custom achievement types 131, 133, 134 and 136 retain the existing
whole-achievement exclusion guards until their behavior is implemented.


Load WXL-style DBC continuation files into AzerothCore **in memory** after `LoadDBCStores()`.

- Base `data/dbc/*.dbc` files are **never modified**
- Continuation files live in a separate folder (default `data/dbc-continuations/`)
- Same naming and merge rules as the WXL client extension (`wxl-extended-dbc`)
- New row IDs and single-row overrides both work before world startup validation

---

## Prerequisites

1. This module folder: `modules/mod-wxl-dbc/` (already here)
2. **One-time core patch** (5 files, below) — required before compile
3. Copy `conf/mod_wxl_dbc.conf.dist` → your `etc/modules/` or merge into `worldserver.conf`

---

## Core patch (required — apply before building)

**5 files. Copy-paste each change below.** Search the file for the **NOW** block; replace it with **CHANGE TO**.

Then rebuild `worldserver`.

---

### File 1: `src/server/game/Scripting/ScriptDefines/WorldScript.h`

#### Edit 1a — end of `enum WorldHook`

**NOW:**
```cpp
    WORLDHOOK_ON_BEFORE_FINALIZE_PLAYER_WORLD_SESSION,
    WORLDHOOK_ON_BEFORE_WORLD_INITIALIZED,
    WORLDHOOK_END
```

**CHANGE TO:**
```cpp
    WORLDHOOK_ON_BEFORE_FINALIZE_PLAYER_WORLD_SESSION,
    WORLDHOOK_ON_BEFORE_WORLD_INITIALIZED,
    WORLDHOOK_ON_AFTER_LOAD_DBC_STORES,
    WORLDHOOK_END
```

#### Edit 1b — end of `class WorldScript`

**NOW:**
```cpp
    /**
     * @brief This hook runs after all scripts loading and before itialized
     */
    virtual void OnBeforeWorldInitialized() { }
};
```

**CHANGE TO:**
```cpp
    /**
     * @brief This hook runs after all scripts loading and before itialized
     */
    virtual void OnBeforeWorldInitialized() { }

    virtual void OnAfterLoadDBCStores() { }
};
```

---

### File 2: `src/server/game/Scripting/ScriptDefines/WorldScript.cpp`

#### Edit 2 — after `OnBeforeWorldInitialized()`

**NOW:**
```cpp
void ScriptMgr::OnBeforeWorldInitialized()
{
    CALL_ENABLED_HOOKS(WorldScript, WORLDHOOK_ON_BEFORE_WORLD_INITIALIZED, script->OnBeforeWorldInitialized());
}

WorldScript::WorldScript(char const* name, std::vector<uint16> enabledHooks)
```

**CHANGE TO:**
```cpp
void ScriptMgr::OnBeforeWorldInitialized()
{
    CALL_ENABLED_HOOKS(WorldScript, WORLDHOOK_ON_BEFORE_WORLD_INITIALIZED, script->OnBeforeWorldInitialized());
}

void ScriptMgr::OnAfterLoadDBCStores()
{
    CALL_ENABLED_HOOKS(WorldScript, WORLDHOOK_ON_AFTER_LOAD_DBC_STORES, script->OnAfterLoadDBCStores());
}

WorldScript::WorldScript(char const* name, std::vector<uint16> enabledHooks)
```

---

### File 3: `src/server/game/Scripting/ScriptMgr.h`

#### Edit 3 — in `public: /* WorldScript */`

**NOW:**
```cpp
    void OnBeforeWorldInitialized();
    void OnAfterUnloadAllMaps();
```

**CHANGE TO:**
```cpp
    void OnBeforeWorldInitialized();
    void OnAfterLoadDBCStores();
    void OnAfterUnloadAllMaps();
```

---

### File 4: `src/server/game/World/World.cpp`

#### Edit 4 — after `LoadDBCStores`

**NOW:**
```cpp
    LOG_INFO("server.loading", "Initialize Data Stores...");
    LoadDBCStores(_dataPath);
    DetectDBCLang();
```

**CHANGE TO:**
```cpp
    LOG_INFO("server.loading", "Initialize Data Stores...");
    LoadDBCStores(_dataPath);
    sScriptMgr->OnAfterLoadDBCStores();
    DetectDBCLang();
```

---

### File 5: `src/server/shared/DataStores/DBCStore.h`

#### Edit 5 — add `ReplaceEntry()` next to `SetEntry()` in `class DBCStorage<T>`

**Required.** `SetEntry()` (stock AzerothCore) calls `delete _indexTable.AsT[id]` before
overwriting a slot. That's safe only when the slot never held a real entry (upstream's
only callers are unit tests against an empty store). In a normally-loaded store, every
entry is a pointer into one shared allocation (`AutoProduceData`'s data table, or the
`*_dbc` SQL overlay's data table) that gets freed in bulk, not per-entry — so `SetEntry`
on an **existing** row corrupts the heap (crashes on `delete`, usually inside the
allocator, e.g. jemalloc `je_large_dalloc`). This module injects continuation rows that
can land on IDs already populated by the base file or a `*_dbc` DB overlay, so it must
use a version that never deletes the old value.

**NOW:**
```cpp
    void SetEntry(uint32 id, T* t)
    {
        if (id >= _indexTableSize)
        {
            // Resize
            typedef char* ptr;
            std::size_t newSize = id + 1;
            ptr* newArr = new ptr[newSize];
            memset(newArr, 0, newSize * sizeof(ptr));
            memcpy(newArr, _indexTable.AsChar, _indexTableSize * sizeof(ptr));
            delete[] reinterpret_cast<char*>(_indexTable.AsT);
            _indexTable.AsChar = newArr;
            _indexTableSize = newSize;
        }

        delete _indexTable.AsT[id];
        _indexTable.AsT[id] = t;
    }

    [[nodiscard]] uint32 GetNumRows() const { return _indexTableSize; }
```

**CHANGE TO:**
```cpp
    void SetEntry(uint32 id, T* t)
    {
        if (id >= _indexTableSize)
        {
            // Resize
            typedef char* ptr;
            std::size_t newSize = id + 1;
            ptr* newArr = new ptr[newSize];
            memset(newArr, 0, newSize * sizeof(ptr));
            memcpy(newArr, _indexTable.AsChar, _indexTableSize * sizeof(ptr));
            delete[] reinterpret_cast<char*>(_indexTable.AsT);
            _indexTable.AsChar = newArr;
            _indexTableSize = newSize;
        }

        delete _indexTable.AsT[id];
        _indexTable.AsT[id] = t;
    }

    // Like SetEntry(), but does not delete the previous value at `id`.
    // Use this to override an existing DBC row from outside the normal
    // load path (e.g. this module) -- see mod-wxl-dbc README for why.
    void ReplaceEntry(uint32 id, T* t)
    {
        if (id >= _indexTableSize)
        {
            // Resize
            typedef char* ptr;
            std::size_t newSize = id + 1;
            ptr* newArr = new ptr[newSize];
            memset(newArr, 0, newSize * sizeof(ptr));
            memcpy(newArr, _indexTable.AsChar, _indexTableSize * sizeof(ptr));
            delete[] reinterpret_cast<char*>(_indexTable.AsT);
            _indexTable.AsChar = newArr;
            _indexTableSize = newSize;
        }

        _indexTable.AsT[id] = t;
    }

    [[nodiscard]] uint32 GetNumRows() const { return _indexTableSize; }
```

---

## Server layout

```
data/
  dbc/                          ← vanilla extract (never touched by this module)
  dbc-continuations/            ← your continuation files (configurable)
    wxl-dbc.manifest            ← optional ordering
    Spell.dbc1-test             ← example: new or overridden rows
    CreatureDisplayInfo.dbc1-myproject
    DBFilesClient/              ← subfolders also scanned
      ItemDisplayInfo.dbc2-artpass
```

Config (`mod_wxl_dbc.conf` or `worldserver.conf`):

```ini
[WxlDbc]
WxlDbc.Enable = 1
WxlDbc.ContinuationPath = dbc-continuations
```

---

## Continuation naming (WXL contract)

```
{Table}.dbc                 base (in data/dbc/, unchanged)
{Table}.dbc{N}-{project}    continuation, N = 1..9
```

Examples:

```
Spell.dbc1-hotfix
CreatureDisplayInfo.dbc1-artpass
Item.dbc3-shared-lib
```

### Merge order (later wins on duplicate row ID)

1. Base row already loaded from `data/dbc/{Table}.dbc` (+ any `*_dbc` DB overlay)
2. Tier `1`, then `2`, … `9`
3. Within a tier: manifest line order, then project slug A–Z
4. Same row ID: **later continuation wins**

Backup files (`.bak`, `.backup`, `.old`, `.orig`, `.tmp`) are ignored.

---

## Manifest (optional on server)

On the server, the module **auto-scans** `dbc-continuations/` for `*.dbc[1-9]-*` files — you usually don’t need a manifest here. Optional `wxl-dbc.manifest` in that folder only if you want explicit load order (same format as the client extension uses for MPQ packs).

---

## Verify

After starting `worldserver`, check the log for:

```
Applying N continuation file(s) from ...
  Spell.dbc1-hotfix -> X row(s) into Spell.dbc
Done. ... Base data/dbc/ files were not modified.
```

---

## Client side

This module is the **server half** of your WXL `wxl-extended-dbc` extension — same continuation files, same naming, same merge rules. Deploy the **same** `.dbc1-*` binaries on the client (loose `Data/DBFilesClient/` or MPQ) with `wxl-extended-dbc` installed; see that extension’s README at `wxl-core/extensions/wxl-extended-dbc/`. Row IDs must match on both sides.

---

## Notes

- Continuations apply **after** file load and **after** AC's `*_dbc` DB overlays, so continuation rows **win** over DB overlays for the same ID.
- Tables must match the server's WotLK DBC layout (same as today).
- This fork applies continuations before secondary indexes are built; see the integration notes above.
