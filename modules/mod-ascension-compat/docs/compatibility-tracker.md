# Ascension compatibility tracker

Last reviewed: 2026-09-12. Target: stock v20 DBCs plus Ascension continuation files and the supplied
`_CURRENT-DATABASE/acore_world` export. This is the working ledger for incremental compatibility work.
Do not wipe the current database or bulk-import the partial donor package.

## Custom-class empty starter bars and Alia's rejected skills

Player::Create loads playercreateinfo_action before the custom initial-item hook grants baseline spells.
The supplied export also has no Human/class-14 action rows, and several supported class/race entries
contain only Attack. Learning spells on login does not itself initialize a starter layout.

Prepared source correction in AscensionCompat.cpp: after progression/proficiency/starter synchronization,
initialize the first 12 action slots from known, nonpassive level-one ClassSpells, starting with Attack.
Exclude generic Thrown/Shoot/Wand and profession/riding abilities. Existing buttons and spells already
placed anywhere are preserved. Apply on first login, or once to an existing level-one character with
entirely empty/Attack-only bars. The persisted core.ascension_starter_actions marker prevents refilling
deliberately cleared layouts on subsequent logins. Existing customized/higher-level layouts and original
class/playerbot initialization remain unchanged. Alia receives 6603, 801901 and 802060 (Attack, Twin Slice,
Sargeron Smite). No spells are granted by this action-button repair.

Skill 113 is Darnassian: the class-14 live baseline sampled a Night Elf. Creation now checks the actual
race/class permission before copying any language skill from that baseline. Preserve native racial
languages and let normal login validation remove already-invalid saved language skills.

New `SkillRaceClassInfo.dbc5-custom-class-thrown`: row 981 permits skill 176 for classes 14, 17-21, 25,
29-32, all races, using the existing weapon-skill flags 128. These eleven classes already receive 2764
in the live baseline; the repair changes only their missing permission. Earlier class-13 correction
and all existing DBCs remain unchanged. Identical 53-byte files staged in the server package, `_data`
and client loose DBFilesClient. The existing untracked continuation ZIP was not regenerated.

Two offline tests pass against the real starter catalog and DBCs: every custom class has active starter
abilities within one bar, Alia's exact spell names/IDs, permission mask provenance/collision checks,
and unchanged Darnassian gate. C++ lint and diff whitespace checks pass. No build, live SQL or native
login test performed. Rebuild/deploy the server source and new continuation; restart server/client.
Verify a fresh character, existing empty-bar Alia, persistence after relog, and preservation of an
existing manually arranged bar. No database wipe or new SQL migration is required.

## Client character-creation crash: September 12, 16:24

The report's Lua stack enters ResetCharCustomize from CharacterCreate_OnShow. The native crash at
004E204F writes `[EBP-0x170]` with EBP=32, producing the reported invalid address FFFFFEB0.
The default-class picker at 004E0F50 allocates 120 bytes for 30 class IDs and writes eligible classes
without checking that capacity. The client's patch-T.MPQ CharBaseInfo has 31 Troll entries, ending in
class 32. The 31st write therefore overwrites saved EBP with that class ID. This is a client stack
overflow before character creation, not a character-database save failure or a reason to remove classes.

Installed a guarded five-byte executable correction in `F:/Ascension-client/Ascension.exe`: allocate
128 bytes using ADD ESP,-128 and move all three indexed accesses from EBP-120 to EBP-128. This holds
32 entries; it is not an unbounded/dynamic array. Future class-list growth or duplicate additions above
32 require another review. Preserve class eligibility, randomness, instructions outside these operands,
and all DBC/SQL data. Installer: `apps/patch_client_default_class_buffer.py` in this module. It verifies
the entire known function, rejects unknown bytes/running clients/conflicting backups, and is idempotent.

Original executable: `F:/Ascension-client/Ascension.exe.pre-default-class-buffer`.
Installed SHA256: `44dd3098dbc56d7d804b63b1d957fbdaad5e97b2d6d8b7d826189f5f4b0118e7`.
Three offline tests pass: disassembled operands and stack-write reproduction/capacity; exact five-byte
change and unknown-function rejection; running-process/backup/idempotence guards. These are static and
modeled checks, not native gameplay execution. No build performed. Reopen the client, click Create New
Character repeatedly, and check race/class selection and existing-character login. In-game acceptance
remains pending. To roll back, close the client and restore the named executable backup.

## Prepared NPC and encounter targeting batch

Two additional DBC-only continuations preserve the Ascension spell records outside the reviewed
target fields. Existing base files and continuations are unchanged. Matching binaries are staged in
the server package, `_data/dbc-continuations`, and the client's loose `patch-ZZ.MPQ/DBFilesClient`.

- `Spell.dbc4-conditioned-npc-targets`: 20 rows restore effect-zero nearby-entry target 38. Each
  still matches the v20 spell name, effect types and aura types, and has current effect-zero SQL
  conditions identifying existing creature templates. Every OR branch has a creature-entry constraint.
  This restores selection for encounter channels, quest interactions and corpse selection, including
  Encage Emberseer, Thaddius Shock, Kael'thas beams, Sacrifice Anveena, Temper and Corpse Explode.
  Only TargetA changes; current ranges, other effects and condition predicates remain intact.
  Addresses 40 of the 109 ignored-condition messages in the supplied run (expected remainder 69).
- `Spell.dbc5-scripted-encounter-targets`: ten rows restore stock target selectors and their radii
  required by existing native area filters: five Nefarian class calls, Dream Fog Sleep, Malchezaar
  Enfeeble, Anetheron Sleep and both Stone Grip variants. This reconnects existing class filtering,
  tank exclusions, target limits and sleep exclusion logic. It does not change those scripts or
  spell magnitudes. Addresses ten targeting-hook messages. Combined with the separate pending
  Fixate correction, the expected hook-mismatch count is 155 -> 143, subject to startup verification.

Three offline tests pass against the real DBC files, current SQL export and native hook registrations:
exact field/string preservation and no later override collisions; condition branches and creature
dependencies; exported script bindings and all active effects' area selectors/radii. Installed copies
match the package bytes. No build, live database application or encounter combat test was performed.
These files need deployment to the running server and a server/client restart; no new rebuild is
required for this data-only batch.

Acceptance: verify the relevant NPC channels select their conditioned creatures, corpse spells select
dead targets, Stone Grip excludes the tank and selects one/three players, Enfeeble excludes the tank
and selects up to five, and Anetheron Sleep excludes the tank and selects up to three. Verify Nefarian
class calls select their intended original class. Custom-class encounter design is not reconstructed.
Nefarian's separate Wild Magic/Siphon Blessing periodic-aura mismatches remain unresolved; restoring
their target filters is not full encounter compatibility. Missing achievement requirements, item-set
parts, difficulty references and other proc errors remain queued for evidence-based review.

## Prepared proc/Fixate batch after the 15:25 audit

The next pass prioritizes inert procs, spell-hook semantics and ignored target conditions, before the
larger achievement/item-set reconstruction backlog. Rank expansion matters: 84 no-ProcFlags warnings
represent 51 logged base IDs; 20 missing-phase warnings represent ten logged IDs. Do not bulk-fill either.

- `rev_20260912_08_melee_proc_hit_phase.sql`: eight exact records (22648, 46910, 46911, 51123,
  51127-51130) gain HIT phase 2 only when both the phase and SQL ProcFlags are still zero. These are
  Call of Eskhandar, Furious Attacks and Killing Machine. Their effective DBCs carry proc-trigger aura
  42 with valid helpers and melee-ability event bit 0x10. Native SpellMgr requires a matching phase for
  those events; cast/finish are not enabled. Preserve inherited event flags, hit filters, rates, chances,
  cooldowns and charges. This repairs the phase gate, not exact Ascension proc-rate/scaling parity.
  Eight of the current 20 missing-phase warning occurrences are addressed; Lightning Shield ranks and
  the old Flurry/Shredding Blows rank chain remain under review.
- `Spell.dbc3-scholomance-fixate`: spell 12021 effect zero is APPLY_AURA with aura type zero in the
  Ascension layer. Restore only its stock dummy aura type 4. The bound Scholomance script can then
  FixateTarget on application and ClearFixate on removal. Preserve Ascension's attack-speed aura,
  triggered spell, duration, target and strings. This addresses two of 155 hook mismatch occurrences,
  leaving an expected 153 after startup verification. Existing DBC continuations are unchanged.

The new binary is staged in server package, `_data` and client loose DBFilesClient. Three offline tests
pass: replay of the full proc export with repeatability/custom-phase preservation, DBC proc/trigger
dependencies, and exact one-field Fixate comparison including strings. SQL lint passes. No build,
live SQL application or combat test performed; deploy through the normal updater and restart both sides.
Test melee-ability hits proccing the affected auras and verify Fixate target locking/release in Scholomance.
The 109 targeting-condition warnings remain queued for per-spell review; none were blindly removed.

## Latest verification: September 12, 15:25 logs / 15:30 database export

Server revision 7abe03501bbb reached ready and shut down normally. The user reports testing looks good.
All five recent continuations loaded: encounter spells (6 rows), original-class starter abilities (18),
Witch Hunter Auto Shot permission (1), Witch Doctor Thrown permission (1), original-class permissions (9).
Missing creature-template creation errors: 293 -> 0. Race/class skill rejections: 0. SQL execution/range
errors: 0. Spell-script hook mismatches: 161 -> 155, as predicted by the six-row encounter correction.

The new export contains both totem templates, model links 4589/4587, spells 1103606/1105672 and the
1152041 Healing Stream script binding. Recorded hashes for migrations 06 and 07 match repository files;
their PENDING state reflects the pending-directory updater, not an unapplied migration. Thringaz now
has Demonology skill 354 saved. His dependent Shadow Bolt need not be persisted in character_spell;
the continuation restores the grant through skill loading. The export is not a live spellbook trace.

Remaining priorities: 155 script-hook mismatches; 84 proc entries without ProcFlags and 20 without
required SpellPhaseMask (reported as unable to trigger); 109 ignored target conditions; 156 missing
spell-difficulty references. The broad data backlog remains 10,242 achievement criteria requirements,
3,197 missing item-set parts and 116 obsolete item-set-name references. Another 8,573 item-set-name
messages explicitly use item_template fallback. There are still 40 invalid creature unit_class values,
ten modifier-operation-46 warnings for spell 55437, and four movement-velocity failures for creature
entries 18187-18190. These are unresolved, not evidence of regression from the recent fixes.

This audit changed no gameplay data or code. Counts are from the supplied run; user acceptance does not
substitute for encounter-by-encounter combat, scaling or complete original-class progression testing.

## Original-class bot starter-spell recovery

The user observed level-three Warlock Thringaz letting his pet fight while he remained idle, with
similar behavior from other classes. The supplied character export identifies GUID 229/class 9 and
contains only profession spells for him, no saved Shadow Bolt. This is snapshot evidence, not a live
spellbook or AI decision trace. Bot factory InitClassSpells grants 686/687 as dependent spells.
Ascension SkillLineAbility maps them to Demonology with class mask 512 and AcquireMethod 0; it also
restricts the school permission to class 10. The prior SQL restored Warlock school permission but
did not restore automatic starter-spell acquisition. Native _LoadSkills replays skill-reward spells;
LearnDefaultSkills covers previously deleted starting skills. SpellIdValue cannot select an unknown spell.

Prepared DBC-only repair, identical files in server package, `_data`, and client loose DBFilesClient:

- `SkillLineAbility.dbc2-original-class-starters`: 18 new rows 760424-760441. Restore the two level-one
  factory starter spells per Warrior, Paladin, Hunter, Rogue, Priest, Shaman, Mage, Warlock and Druid,
  using each class's existing starting skill, exact original-class mask, AcquireMethod 2 and no forward
  rank. This does not give custom classes free spells or change the spells themselves.
- `SkillRaceClassInfo.dbc4-original-class-starters`: nine new rows 972-980. Permit those starting skills
  for their original classes/all races with class-skill flags 1040 and no level gate. The original-class
  starter skills are already in playercreateinfo_skills; this also avoids relying on SQL-only permissions.

Both files append unique IDs checked against existing DBCs and exported SQL. Two offline tests verify
the factory grants, exported starting skills, binary layout, Warlock acquisition and exclusion of class
10/custom classes. No build or live deployment to the server. Reboot server with continuations and let
bots relog; restart client. Confirm Thringaz knows/casts 686 and other level-one offensive starters work.
Higher-rank trainer data, unrelated AI decisions and all other possible causes of idle combat remain
unverified; this fixes a demonstrated acquisition mismatch, not proof that every bot behavior is solved.

## Witch Doctor Serpent Ward and Thrown follow-up

The user's level-three Witch Doctor (class 13) observed two Serpent Wards from one cast. Spell 500960
has one SUMMON effect for creature 50105; the custom summon routine also specifies count one.
The custom script intercepted OnEffectLaunch while native EffectSummonType executes at HIT, so the
launch suppression did not prevent the later native summon. Changed that registration to OnEffectHit
for the shared Witch Doctor summon handler. Preserve its one-per-cast guard, slot replacement, AI,
intentional multi-summon counts and separate SCRIPT_EFFECT hook. This is an execution-phase bug that
cannot be corrected by changing DBC count data without breaking the custom summon path.

The same character lost Thrown spell 2764 because skill 176 excluded class 13. Both authored class
starter tables explicitly grant 2764. New `SkillRaceClassInfo.dbc3-witch-doctor-thrown` adds unused
row 971: skill 176, all races, class mask 4096, flags 128 (the native Thrown skill flags). Existing
rows and other-class permissions remain unchanged. Identical copies are in the server package,
`_data/dbc-continuations` and client `Data/patch-ZZ.MPQ/DBFilesClient` folder.

C++ lint and diff whitespace checks pass. Binary header/row, all ten race masks, isolation to class 13,
starter grants and absence of row 971 in the existing DBCs/export were checked. No server build or
runtime test performed. Rebuild/restart the server for the summon fix; deploy the new continuation on
both sides and restart/relog for the skill fix. Test one ward per cast, recasting replaces the previous
ward, normal firing/expiry, and no class-13 Thrown rejection on login.

## September 12, 14:29 log follow-up

Witch Hunter acceptance: the user reports the existing character working. Client `wxl-core.log`
confirms the SkillRaceClassInfo continuation merged (one appended, zero skipped), and the refreshed
item cache contains Old Rifle RangedModRange=100. Server logs confirm the rifle migration and skill
continuation loaded, with no remaining Auto Shot permission rejection or SQL execution errors.

Prepared next, not applied to the server:

- `Spell.dbc2-native-encounter-hooks`: six rows, copied from the Ascension layer with only reviewed fields
  changed. Spells 802/804 regain stock area-entry targeting, radii and range so the Twin Emperors'
  existing AOE casts can select eligible bugs. Ascension's damage, duration and explosion timer remain.
  Campfire 818 regains destination 32 for the native floor-height hook. Anubisath aura 9347 regains its
  stock periodic trigger 24573 every 11000 ms. Separation Anxiety 21094/23487 regain periodic dummy
  and 1000 ms from the canonical server helper definitions. This addresses six logged hook mismatches;
  155 of the current 161 remain outside this patch. No existing DBC is rewritten.
- `rev_20260912_07_ascension_totem_templates.sql`: reconstructed templates for Searing Totem 1102523
  and Healing Stream Totem 1103527, addressing 288 and five missing-template attempts respectively.
  Original archive NPC pages identify Totem type and portrait IDs 4589/4587, matching stock templates
  2523/3527 and the effective display/model DBCs. The donor supplies names and faction 35. Use the stock
  totem archetype; native summon code supplies five health, owner level and racial display selection.
  Spell descriptions identify attack 1103606 and periodic aura 1105672 -> dummy 1152041. Bind that dummy
  to the existing `spell_sha_healing_stream_totem` -> 52042 healing path. This uses the authored helper
  values, not invented damage or a placeholder NPC. The summon tooltip references the aura's six-point
  base value while the dummy has nine: preserve this source discrepancy pending combat/tooltip review.
  This is a functional reconstruction, not proof of exact official AI/scaling parity.

Checks: three DBC preservation/round-trip/dependency tests and two SQL replay/dependency tests pass;
SQL lint passes. SQL replay uses SQLite with MySQL session assignments evaluated separately, not live
MySQL. No build or live database application performed. The DBC continuation is also staged in `_data`
and the client's loose `Data/patch-ZZ.MPQ/DBFilesClient` folder for the next launch.

Acceptance after the server updater/restart and client restart: confirm this Spell continuation merges,
no creation failures for either totem, Searing acquires/attacks a hostile target, Healing Stream heals
group members every two seconds and cleans up on despawn; test the affected boss mechanics and campfire
placement. Startup silence alone does not establish those behaviors. Keep changed Ascension mechanics
(e.g. the Four Horsemen marks' authored damage) intact while reviewing the remaining bindings.

## Witch Hunter ranged starter investigation

The user's screenshot is Witch Hunter (class 15), not Witch Doctor. Darkslayer 804179 reports out of range
at every distance and the gun does not auto-fire. The effective range record 114 is 0â€“35 yards for both
Darkslayer and Auto Shot, and the server's custom-class ammo check already bypasses projectile stacks.

Two evidenced corrections are prepared. DBC-capable fixes use new continuations; SQL is retained only for the rifle field absent from Item.dbc:

- Captured starter item 484364 (Old Rifle) has RangedModRange=0 in the export, while ordinary rifle 2510
  has 100. The core sends this multiplier in item-query responses. Restore 100 only for the matching gun
  with the old zero value in `rev_20260912_06_witch_hunter_ranged_starter.sql`. This is the likely client-side range rejection; live confirmation is pending.
- Auto Shot 75 is an authored class-15 grant, but skill 11163 has only a Hunter permission in the effective
  skill DBC. The latest log explicitly deletes it for class 15. Add the matching permission for all races
  of Witch Hunter under unused row ID 530, retaining Hunter row 184. This is now shipped as
  `env/dist/bin/data/dbc-continuations/SkillRaceClassInfo.dbc2-witch-hunter-auto-shot`
  (also copied to `_data/dbc-continuations`), not SQL. Its tier 2 loads after the existing tier 1 layer.
  Existing DBCs are unchanged. The binary contains exactly one eight-field row and passes the
  migration/overlay fixture check. The permission statements were removed from the SQL migration.

Witch Hunter's level-one gt coefficients exist at index 1400 in the 3,200-row continuations:
gtOCTRegenHP=0.245902, gtRegenHPPerSpt=1.5, gtRegenMPPerSpt=0.034965. Core regen indexes the actual class ID.
Native automatic rage uses a separate formula and excludes ranged attacks; Witch Hunter's secondary rage
is explicitly accepted by spell energize. Darkslayer triggers 680235, whose effect 2 energizes rage on the
caster. No gt changes or blanket ranged-rage formula changes were made.

Offline migration tests cover the range guard, unrelated items, restored values, repeatability, existing
Hunter access, all ten Witch Hunter races and overlay ID collisions. SQL lint passes. Migration is unapplied.
After applying through the normal updater and restarting/relogging, verify Auto Shot stays learned, gun
range is usable and Darkslayer grants rage. A client with cached item-query data may require refreshing its
item cache before the new range modifier is visible. No ammo pouch or invented starter ammunition added.

## Missing item-set pieces: relationship audit

The direct archive-ID check was insufficient for identifying related gear. The current ItemSet.dbc stack
directly identifies 706 affected sets, including names, member IDs and bonus spells. Of the 3,197 unique
missing pieces, 2,361 still have effective Item.dbc metadata. Their absence from SQL/HTML does not mean
there is no evidence for their identity.

Comparing all members of each corresponding v20 set (not matching array positions, which changed) finds
96 unique missing items across 16 sets with identical non-ID Item.dbc fields to a stock member: class,
subclass, sound override, material, display, inventory type and sheath. These are strong identity leads.
For example, set 383 is Warlord's Battlegear; missing 6116542 matches member 16542, whose archive page names
it Warlord's Plate Headpiece. The direct missing-ID page is absent, but its related gear is identifiable.

See [missing-item-set-links.json](missing-item-set-links.json) for all affected sets, bonus thresholds,
missing IDs and stock-member matches. Stock-slot candidates are retained as weaker evidence and must not
be confused with metadata-matched members. Some archive names are merely Item # placeholders.

Next candidate batch: corroborate these 96 variant identities against available SQL/source gear, then
prepare any justified set-label repairs separately from full item-template restoration. Identical visuals
and slots do not prove identical stats, level requirements or acquisition rules. No items, stats or set
memberships were modified during this audit. The absence of direct pages does not establish deprecation.

## Prepared deprecated-reference cleanup

`WxlDeprecatedSpellReferences.h` defines the three exact captured SpellDifficulty rows (1908, 1909, 2805)
containing the eight archive-confirmed deprecated IDs. After all WXL overlays load and before core cache
construction, the loader clears only those ten slots whose spells are still absent. Different row layouts
and restored spells are preserved. The first spells in rows 1908/1909 are not deprecated by this evidence
and remain untouched. Each cleanup is reported in one startup info message.

Offline checks confirm the current binary rows match the policy and all ten target references are absent
and explicitly deprecated in the archive. All three groups already fail the core's required first-two-spells
validation, so the cleanup removes stale metadata rather than disabling functioning difficulty mappings.
Expected difficulty errors for the inspected data: 166 to 156. Source DBC files and SQL remain unchanged.
C++ lint passes; two native regression tests cover exact matching, restored spells and repeatability but
have not been compiled/run. Rebuild/startup remains pending.

No deprecated-item cleanup is authorized by the available evidence: the missing item-set IDs have no local
pages establishing their status. Existing item templates, inventories and set membership are retained.

## Latest archive cross-reference: September 12, 13:32 log set

Server revision: `9cf9bc0d8ec0`. The new log contains no achievement overflows, material mismatches or
display mismatches. There are 245 missing Searing Totem 1102523 creation attempts, 161 script-hook mismatches,
and one skill rejection: Undead Witch Hunter (race 5/class 15), spell 75 teaching skill 11163.
The earlier hunter Thrown deletions are absent. Missing achievement requirements and item-set groups persist.
Absence of an error in this run does not establish full gameplay acceptance.

**Correction to the earlier archive assessment:** spell 2100636 is present locally, explicitly titled
`DEPRECATED Devastating Leap`, and is also present in the generated donor spell SQL. Its HTML SHA-256 is
`79504d4c3754c8c9e3a936eff7ac6a9c20307cd2862bb90224d364bccd4007b1`, exactly matching the user's archive screenshot.
Its local page includes description, displayed effects, flags and history. The earlier review failed to
surface this useful evidence; absence from the running SpellStore is not absence from the archive.

The 166 difficulty errors cover 164 unique spell IDs. Of those, 157 have local HTML pages: eight titles
explicitly say DEPRECATED and 149 do not. Seven IDs have no local page. Do not classify all 164 as deprecated.
The 3,197 missing item-set IDs remain a separate result: zero matching local item pages. A remote archive
may include other captures; an example spell record does not establish coverage of those item IDs.

See [log-archive-cross-reference.json](log-archive-cross-reference.json) for exact IDs, names, page hashes,
missing pages and the inspected log fingerprint. The remote URL could not be opened by the browsing tool;
the screenshot's source fingerprint was verified directly against the local HTML bytes.

Next: use the archive names/history to review each missing difficulty reference for stale content versus
recoverable active content. A deprecated label is evidence for review, not authorization to delete an
entire difficulty group. The partial donor spell SQL must not be imported as full replacement spell records.

## CoA Repack Update3 source port

Source: `CoA-Repack-Update3/CoA-Repack-Update`, manifest `issue-fixes-20260912`, nominal base revision
`f069a4b943ccf72d1738d98c0123ec0ef49e1354`. All payload source hashes were verified against UPDATE.json.
This is a supplied CoA repack patch set, not a merge of the AzerothCore upstream branch. Each listed fix
was missing from this fork and is now **Prepared**, pending build and gameplay acceptance.

| Issue | Ported behavior | Acceptance after rebuilding |
| --- | --- | --- |
| #35 | Store active specialization in character settings and restore it before progression synchronization | Select spec, relog/restart, verify spec-dependent grants; test switching specs |
| #34 | Remove paid-node requirements from automatic progression while retaining spec roots | Check affected automatic nodes at their required levels and on the wrong spec |
| #33 | Set Arm of Thorim's stun mechanic on spell/effect; classify Brand of the Unworthy as knockout | Check DR, immunity, trinket removal and damage breaking Brand |
| #32 | Use Hunter's parry curve for Starcaller | Check learned Parry and rating scaling |
| #29 | Make Assault/Pacify/Protect exclusive per caster on the player and owned minions | Switch all three stances with two Necromancers nearby |
| #28 | Expand legacy item masks through custom-class fallbacks; preserve explicit custom masks | Equip intended legacy items; verify explicit exclusions remain |
| #27 | Expand legacy quest class masks through the same mapping | Accept intended class quests; verify unrelated class quests remain restricted |
| #25 | Derive racial grants from each race's authored skill-line and custom-class/resource variants | Check racial spellbook and resource behavior across races/classes |
| #24 | Give Barbarian Warrior base AP and Bloodmage Rogue base AP | Check low/high-level AP with stats and form modifiers |
| #23 | Continue legacy stat gains from each custom class's calibrated level-one anchor | Level 1 to 2, then check level 80 and zero-mana classes |
| #21 | Apply racial totem models only to actual totem creature types | Cultist tentacles keep template model/scale; ordinary totems retain racial models |
| #22 | Remove Inner Demon's forced metamorphosis body substitution | Character appearance persists with form visuals; Warlock metamorphosis remains intact |

The package also corrects Ascension spell-modifier packet aggregation and its trailing spell-family field,
including modifier resends. Ported with `IsAscensionCompatClient()` rather than the repack's localhost check.
Playerbot guards/helpers, event cleanup, client-control fixes, Shadow Nova correction, typed enums,
asynchronous character creation and our recent failure diagnostics remain intact. No binary was copied and
the repack installer was not run.

Two new native updater migrations accompany this port:

- `rev_1789223314829733700.sql`: stance group 1137 and per-caster exclusivity.
- `rev_20260912_00_custom_class_stat_progression.sql`: 21 custom classes, 79 levels each.

The current export's stat inputs and affected rows exactly match the package's expected base fingerprints.
Group 1137 is unused in the export. Offline SQL calculation replay (with MySQL syntax translated for SQLite)
matches the package's expected final fingerprint for all 1,659 stat rows, preserves anchors/legacy rows,
and is repeatable. This confirms calculation/data compatibility, not a live MySQL execution.

C++ and SQL lint passed. Three automatic talent tests passed; the optional client Lua check was skipped.
The stat replay test passed. Six supplied native test files were added for AP, items, quests, racials,
totems and shapeshift models; they have not been compiled or run. No build, deployment, database execution,
or visual acceptance was performed. The stat curve remains a compatibility approximation, not proprietary
Ascension progression data.

## Latest startup review: September 12, 12:37 log set

This review supersedes the earlier deployment-pending notes below for the five migrations explicitly
reported as applied by Server.log: achievement IDs, stock skill permissions, item displays, proc hit masks,
and all-race/class creation definitions. Their gameplay acceptance remains separate.

- Server.log records a normal shutdown, and Errors.log has no achievement overflow errors.
- The previous 24 display mismatches and unsupported HitMask warnings are absent. The previously reported
  Arms/Demonology permission deletions are absent. There are still 161 script-hook mismatches.
- **Prepared C10:** `rev_20260912_04_stacked_dbc_item_materials.sql` corrects five exported Material values
  to the effective Item.dbc values, with old-value guards. The core already corrects these in memory;
  this persists that correction. Independent SQL/DBC checks and repeatability/conflict tests pass.
- **Prepared C11:** `rev_20260912_05_restore_hunter_thrown_permission.sql` restores v20's hunter Thrown
  permission (skill 176, class mask 4, flags 128) under unused ID 529. Addresses 48 hunter skill-deletion
  messages. Offline overlay replay and repeatability tests pass; no build or database execution performed.
- **Blocked:** one Reaper Thrown rejection needs an intended class-skill contract; do not infer it from
  the restored hunter permission.
- **Blocked B06 expanded:** 168 missing-template failures for Searing Totem 1102523 (spell 1103599),
  plus three for Healing Stream Totem 1103527 (spell 1105394). Both donor rows contain only ID, name and
  faction 35. They cannot establish a complete summon template or AI behavior.
- Remaining large groups: 10,242 missing achievement criteria requirements; 8,573 item-set names supplied
  by runtime fallback; 3,197 missing item-set parts; 166 spell-difficulty references; 109 target-condition
  mismatches. These still require semantic/data reconstruction, not placeholder rows.

Item and skill regression checks now use the export/DBC evidence rather than requiring an old error to
remain in a replaceable log file. New migrations are unapplied and need the next startup check.

## Status and acceptance

- **Audited**: inspected offline; no change approved by that status alone.
- **Prepared**: source or migration exists and has offline checks; deployment/startup remain unverified.
- **Candidate**: potentially useful, but needs the listed evidence before a migration.
- **Blocked**: required semantics or data are missing. Placeholders do not establish compatibility.
- **Verified**: applied to the intended stack and the stated acceptance checks passed. Nothing below has
  been promoted to this status using the old logs.

For each completed batch, record its migration/source files, offline checks, deployment revision, and fresh
startup/gameplay result here. Keep prepared and verified separate. Build/startup testing belongs to the user.

## Source inventory and possible uses

The donor is `C:/Users/dead/Downloads/ascension-db`, a partial website-derived conversion, not a server dump.
All emitted columns in its 12 tables exist in the current export. That does not prove that values or omitted
fields are compatible. Counts below concern SQL rows; an absent SQL DBC row can already exist in binary DBCs.

| Source/table | Donor rows | Existing / absent SQL IDs | How it can help | Gate before applying |
| --- | ---: | ---: | --- | --- |
| `item_template` | 115,373 | 102,006 / 13,367 | Identify items and compare tooltip metadata | Verify identity, DBC display and complete required fields; never insert partial templates |
| `creature_template` | 41,817 | 30,536 / 11,281 | Names, level ranges and classification references | Verify model, faction, stats and scripts independently |
| `quest_template` | 10,776 | 9,449 / 1,327 | Quest text and objective candidates | Check objectives, items, NPCs, rewards and conditions together |
| `gameobject_template` | 1,673 | 1,193 / 480 | Identify candidate object IDs/types | Actual donor has only entry/type; models and type-specific data still required |
| `spell_dbc` | 214,154 | 3,180 / 210,974 | Names, costs, schools and level references | No effects or auras supplied; avoid partial SQL overlays that default missing fields |
| `achievement_dbc` | 9,666 | 0 / 9,666 | Titles, points and superseding IDs | Does not supply achievement criteria conditions |
| `areatable_dbc` | 2,852 | 0 / 2,852 | Names and continent references | Compare full effective DBC record; partial SQL rows are not replacements |
| Quest starters/enders, vendors, trainers, spell ranks | See inventory | Not identity-audited | Candidate relationships and rank chains | Verify both ends, existing conflicts, requirements and intended progression |
| `data/coa-world` | Full baseline | Not an incremental update | Bootstrap an empty world schema | Not appropriate for importing over this database |

Detailed column lists, source fingerprints and counts are in [donor-inventory.json](donor-inventory.json).
Fingerprints identify the inspected snapshots, not their authenticity. The reusable scanner is
[`audit_donor.py`](../apps/audit_donor.py); it performs no SQL execution.

## Work queue

| ID | Status | Work / benefit | Evidence and remaining acceptance |
| --- | --- | --- | --- |
| D01 | Audited | Inventory donor schemas and ID overlap | All 12 table column sets match export; checked all seven donor SQL files |
| D02 | Audited | First donor subset: fill empty existing template names | Zero candidates. No migration generated; preserve existing nonempty names |
| D03 | Blocked | Recover missing item-set parts | None of the 3,197 logged missing item IDs occur in donor item rows; need another item source |
| D04 | Audited | Review rank chains | 1,973 identical, 55 invalid structures, 5 missing spell references, 4 conflicting chains, 2 structurally new chains. The two new chains fail semantic review below; no rank migration prepared |
| D05 | Candidate | Review quest/vendor/trainer relationships | Follow D04; group each feature with referenced templates and conditions; reject dangling references |
| D06 | Candidate | Persist item-set name fallbacks | 8,573 logged fallbacks already use item_template in memory; low priority, no new content benefit |
| C01 | Prepared | Preserve large achievement/criteria IDs | Character migration plus AchievementMgr uint32 reads; verify persistence of IDs above 65,535 after restart |
| C02 | Prepared | Restore stock class access to Arms/Demonology skills | World migration adds noncolliding rows; offline checks cover 214 logged permission failures; verify affected players |
| C03 | Prepared | Correct 24 item displays | Guarded updates match effective Item.dbc and exported old values; verify equipment visuals |
| C04 | Prepared | Remove unsupported proc HitMask bits | 208 exported rows with 32767 become 12287; supported bit outcomes preserved; custom outcomes are not implemented |
| C05 | Prepared | Adapt native script hooks to changed effects | Charge, Lay on Hands, Drain Soul, Blood Presence, Ground Slam and Spore Cloud cover 23 of 184 logged hook mismatches; build and gameplay checks pending |
| C06 | Prepared | Accept the observed Rusty Shiv accumulator variant | Ranger compatibility guard accepts MiscValueB 20 as well as 10; verify spell 561315 validation and damage |
| C07 | Prepared | Clarify continuation loader logging | Unregistered client-only tables summarized instead of individual warnings; genuine known-table load failures remain visible |
| C08 | Prepared | Complete all-race/class creation definitions | Adds 38 absent original-class pairs, producing 310 pairs across ten races and 31 playable classes. Export replay preserves all 272 existing starts and verifies class/race stats. Playerbot original-class guards unchanged |
| C09 | Prepared | Diagnose character-save failures | CharacterHandler now logs account, GUID, race/class and transaction failure alongside database errors |
| B01 | Partial | 161 script-hook mismatches in latest log | Six addressed by the prepared encounter DBC continuation; 155 still require semantic review |
| B02 | Blocked | Missing achievement criteria requirements | 10,242 log messages; donor titles/points cannot reconstruct criteria_data. Empty placeholders can unlock achievements incorrectly |
| B03 | Blocked | Insidious Whisper collision | Stock boss spell 37676 is an Ascension mount; need a proven replacement, including targeting and duration |
| B04 | Blocked | Custom effects/auras and achievement types | Effect 193 behavior is unproven; supplied spells do not use aura 173. Unsupported achievement types need actual rules |
| B05 | Candidate | Other startup references | Separately investigate 166 spell-difficulty references, 109 target-condition mismatches, 84 missing loot templates and 40 creature class errors; donor metadata does not establish fixes |
| B06 | Prepared | Missing totem templates 1102523 and 1103527 | Original archive portraits resolve stock model identities; migration 07 reconstructs native totem templates and the Healing Stream script binding. Combat/scaling acceptance pending |

Counts are from the supplied old startup log and export, not a new server run. A quieter startup alone does
not verify combat, rewards, achievement conditions or world completeness.

## Prepared migration files

Apply through the normal database updater on the matching rebuilt server, preserving accounts and characters.
These files have not been executed by this task:

- `data/sql/updates/pending_db_characters/rev_20260912_00_extended_achievement_ids.sql`
- `data/sql/updates/pending_db_world/rev_20260912_00_restore_stock_class_skill_permissions.sql`
- `data/sql/updates/pending_db_world/rev_20260912_01_stacked_dbc_item_displays.sql`
- `data/sql/updates/pending_db_world/rev_20260912_02_supported_proc_hit_masks.sql`
- `data/sql/updates/pending_db_world/rev_20260912_03_all_race_class_creation.sql`

Existing source/SQL lint and offline skill/display checks passed. Native compilation, MySQL execution,
fresh startup and player-visible acceptance remain pending. The unrelated existing
`rev_1787754600000000000.sql` is outside this compatibility batch.

### Blood Elf/Reaper creation failure

The supplied live error attempts to save criterion 312873 into an unsigned SMALLINT (maximum 65535).
`Player::SaveToDB` includes achievement progress in the initial character transaction. A failed insert rolls
that transaction back, and CharacterHandler sends CHAR_CREATE_ERROR. This affects all classes that acquire
large criterion IDs, including existing characters saving progress; it is not a Reaper eligibility rule.
C01's character-schema migration and 32-bit core reads are required. Blood Elf/Reaper (race 10/class 30)
already exists in the export and is preserved by C08. No live database changes or builds were performed.

Creation-definition coverage is not full starter-gameplay acceptance. The effective outfit DBC lacks
Orc/Druid outfits for both genders and Human/Guardian male; custom-class scripted kits can handle their own
items. Action bars, class quests and racial interactions still need gameplay checks. Do not mark C08 as
complete gameplay compatibility merely because the creation rows exist.

## Refresh the donor audit

Run from the repository root with Python. It supports the inspected line-oriented SQL layout and fails on
unsupported INSERT/tuple layouts. It does not establish semantic compatibility or recommend inserts:

```powershell
python modules/mod-ascension-compat/apps/audit_donor.py --donor C:/Users/dead/Downloads/ascension-db/data/sql/updates/pending_db_world --current _CURRENT-DATABASE/acore_world --output modules/mod-ascension-compat/docs/donor-inventory.json
```

Review changed fingerprints/counts and reassess affected decisions before reusing an old candidate list.

To include rank-reference checks, append both arguments to the command above:

```powershell
--spell-dbc _data/dbc/Spell.dbc --spell-dbc _data/dbc-continuations/Spell.dbc1-ascension
```

### First rank-chain review

The two structurally new chains are Hand of Protection (1022, 5599, 10278) and Curse of Tongues
(1714, 11719). The effective files contain all five IDs, so an ID-only check would accept them.
However, the Ascension overlay replaces only 1022 and 1714, removes their rank text, and leaves the higher
rank records inherited from v20. Hand of Protection also gains a third effect. Both chains are absent from
the current SQL. Reintroducing the donor chains could reconnect changed unranked abilities to stock ranks.
**Blocked pending intended progression evidence; do not import these two chains merely because IDs exist.**

The audit's `candidate_new_chains` label is structural only. This ledger records the subsequent semantic
decision. Four parser/classification tests pass; the full local audit completed without schema mismatches.
