# CoA correction handoff

## Achievement-list crash follow-up

The next supplied backtrace reached AchievementGlobalMgr::LoadAchievementCriteriaList and crashed
inside std::list insertion. The full dbc2 Achievement_Criteria.dbc contains 45 active criteria with
types 131 (29 rows), 133 (2), 134 (1), and 136 (13), beyond the native 0–123 array bounds.
The previous loader indexed the criteria array with these values without validating them.

AchievementMgr.cpp now checks criteria types, both additional-condition types and active timer types
before any indexed insertion. It excludes all criteria belonging to an affected achievement, rather
than silently removing a requirement from an otherwise completable achievement. There are 33 affected
achievements in the supplied data. Their custom criteria semantics still need implementation; the
guard provides safe startup, not support for those achievement types. The criteria DBC, earned
achievement records and all other character data remain unchanged. An aggregate startup message
reports excluded criteria and achievements.

Push/pull and rebuild this C++ correction on Linux. No additional SQL or DBC replacement is required
for this particular crash. Item-set-name and spell-loot warnings preceding the crash are separate.
Static auditing and boundary controls pass, as do targeted repository lint checks. No native build,
Git operation or Linux startup was performed here. Evidence: var/dbc-sql-audit/achievement-index-audit.json.

## Superseding correction after full dbc2 installation

The user installed the entire dbc2 directory. The original archive/preflight below assumed a minimal
overlay on the old DBC baseline and must not be used as validation of that full-directory installation.

WorldMapArea.dbc in dbc2 contained 25 no-area records with area_id 0xFFFFFFFF. The core indexes this
table by area_id, not its first ID field. AutoProduceData incremented the maximum index, wrapping to
zero, then wrote outside its zero-sized index array. The repaired file uses area_id 0 for exactly
those records, matching the old baseline's no-area convention, and preserves all other bytes.
It was written directly to C:/Users/dead/Downloads/dbc2/WorldMapArea.dbc; original is WorldMapArea.dbc.bak1.
Corrected SHA-256: 1d599ca51176dc1108026326f22f4ffb5cd3a0f54fc4af3c7d0745cb4cb6d6fe.

Copy that corrected file to the Linux data/dbc directory. This data repair does not require a rebuild.
The source additionally rejects UINT32_MAX indexes and stops before string production when numeric
record production fails. These defensive changes take effect in the user's next Linux build.

Do not edit or manually reapply rev_20260911_01_coa_item_display_alignment.sql. It may already have
run before the crash. New rev_20260911_03_restore_dbc2_item_displays.sql compensates its 124 changes,
guarding each update by the exact value previously written. The normal updater can apply it on the
next startup after the user pushes/pulls it. A fresh database running 01 then 03 also returns to the
exported display values. The separate 41-row stale-reference cleanup remains applicable.

Offline validation: all 114 recognized core LOAD_DBC tables in the corrected dbc2 set passed field
count, used-field bounds, UINT32_MAX index and string-offset checks. This is not full gameplay or
native startup validation. SQLite replay verified the compensation, idempotency and preservation of
unrelated/conflicting rows. No Git operations or builds were performed for this correction.

The prior sections below describe the original minimal-overlay package, not the entire dbc2 folder.

Current package: offline candidate, not installed. You manage Git and Linux builds. No live data was changed.

## Prepared changes

- Spell.dbc contains **21 complete dbc2 records** over the existing baseline. All 239,466 spell IDs and
  their order remain; the other 239,445 records and original string pool are byte-identical.
- Three collection DBCs are staged under `dbc/Ascension/`, matching the module's default directory.
- First SQL migration: **124 guarded nonzero item-display corrections** matching the startup log.
- Second SQL migration: **41 stale metadata rows**: 15 ranks, 7 trainer_spell, 3 legacy npc_trainer,
  1 proc, 1 script binding and 14 starter skills. Valid consecutive rank prefixes remain; singleton
  rank metadata is omitted without removing the underlying spells. No character tables are touched.
- Source: Rusty Shiv's existing guarded adapter now adds the per-caster stacking flag required by
  its validation. The distributed config sets MapClass10ToWarrior to zero. Carry these source/config
  changes through your normal repository workflow; this archive contains no built executable.

The original 18 spells cover Guardian standards/recovery, two Starcaller absorbs and Infernal Bulwark.
Three additional records supply the inputs expected by existing runtime code: Vampiric Tonic 802276
gets BasePoints 39; Agonizing Presence 807727 gets Felsworn family 20; Echoes of Eternity 521211 gets
the dummy aura/no trigger required by both Zenith variants. Raw aura mismatch alone does not prove
a runtime failure when a metadata adapter converts that aura. Full native validation is still required.

Complete imported records include amounts, flags and descriptions, not merely hook types. Review all
field changes in manifest.json. Thirty-two display corrections to zero remain deferred for review.
The existing unrelated Tinker/core changes were preserved.

## Verification

Every unselected spell byte and original string byte is preserved. Selected numeric fields and decoded
strings equal dbc2. Candidate ID count, trigger references and cast-time/duration/range/radius/icon/visual
references passed. Thirty-five raw hook requirements match, and additional adapter-input checks pass.

SQLite replay proves the emitted UPDATE/DELETE predicates affect exactly the intended exported rows,
preserve other rows, and become no-ops on repeat application. This is not a MySQL integration test.
Direct repository lint checks pass for the changed C++ and both new SQL files. Full C++ lint reports
existing unrelated violations. Full SQL lint previously failed on existing violations and a fetch of
nonexistent origin/master; no Git operations were run after you reserved them for yourself.

## Linux installation preparation

1. Extract into a staging directory, separate from the live data directory.
2. Check the current baseline, substituting the actual Linux path:

   `python3 coa_data_preflight.py --bundle . --server-dbc /path/to/data/dbc --repo . --phase before`

   Hash mismatches are stop conditions. The supplied Windows data has not been proven identical to
   your live Linux data. Use `--config /path/to/mod_ascension_compat.conf` to check the active config.
3. Review live SQL against the exact before-rows in manifest.json and stale-references.json. The
   preflight checks files, not live database state. SQL files are under the normal pending updater
   path; avoid manually applying them in addition to the updater.
4. Reconcile the client's effective Spell.dbc through its actual MPQ carrier. This is a server data
   candidate, not a client MPQ. Server-only changes do not establish client parity.
5. Back up affected files and world rows. Build the updated source on Linux yourself. During the
   maintenance window, install only the supplied Spell.dbc and Ascension collection subdirectory,
   preserving other DBCs. Set active `AscensionCompat.MapClass10ToWarrior = 0`. A distributed template
   change does not update an existing live config. Confirm `AscensionCompat.DbcDirectory` resolves
   to the installed directory from the worldserver working directory (default `./data/dbc/Ascension`).
6. Repeat preflight with `--phase after`, then capture fresh startup logs and verify the exact SQL
   outcomes. Test multiple-caster Rusty Shiv, standards/Field Commander, recovery, both Starcaller
   absorbs, Infernal Bulwark, Vampiric Tonic, Agonizing Presence, Zenith and collections.

Remaining acceptance work: native startup/gameplay and client parity; separate Tinker contract work;
missing difficulty/talent references; achievement/item-set gaps; zero-display items; stock-class/bot
skill rejection. Do not fabricate achievement criteria or import the website conversion to silence logs.

Regeneration scripts remain in var/dbc-sql-audit in the Windows workspace. The portable preflight is
tracked as tools/coa_data_preflight.py. Manifest hashes identify the exact candidate and migrations.
