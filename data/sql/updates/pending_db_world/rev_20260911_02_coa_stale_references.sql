-- CoA baseline cleanup: spell and skill references absent from both reviewed DBC sets and SQL overlays.
-- Keep valid consecutive rank prefixes; omit two resulting single-rank chains without deleting their spells.
-- Exact before-rows and required baseline hashes are in var/dbc-sql-audit/candidate/stale-references.json.
-- Does not modify character spells, skills, inventory, achievements, or any DBC record.
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 1022 AND `spell_id` = 1022 AND `rank` = 1;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 1022 AND `spell_id` = 5599 AND `rank` = 2;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 1022 AND `spell_id` = 10278 AND `rank` = 3;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 1714 AND `spell_id` = 1714 AND `rank` = 1;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 1714 AND `spell_id` = 11719 AND `rank` = 2;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 14179 AND `spell_id` = 58424 AND `rank` = 4;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 14179 AND `spell_id` = 58425 AND `rank` = 5;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 14186 AND `spell_id` = 14194 AND `rank` = 4;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 14186 AND `spell_id` = 14195 AND `rank` = 5;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 19255 AND `spell_id` = 19258 AND `rank` = 4;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 19255 AND `spell_id` = 19259 AND `rank` = 5;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 30710 AND `spell_id` = 30710 AND `rank` = 1;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 30710 AND `spell_id` = 30711 AND `rank` = 2;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 30710 AND `spell_id` = 30712 AND `rank` = 3;
DELETE FROM `spell_ranks`
WHERE `first_spell_id` = 31638 AND `spell_id` = 31640 AND `rank` = 3;
DELETE FROM `spell_proc`
WHERE `SpellId` = 71761;
DELETE FROM `spell_script_names`
WHERE `spell_id` = 71761 AND `ScriptName` = 'spell_mage_deep_freeze_immunity_state';
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 3 AND `SpellId` = 5599;
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 3 AND `SpellId` = 10278;
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 4 AND `SpellId` = 5599;
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 4 AND `SpellId` = 10278;
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 5 AND `SpellId` = 5599;
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 5 AND `SpellId` = 10278;
DELETE FROM `trainer_spell`
WHERE `TrainerId` = 31 AND `SpellId` = 11719;
DELETE FROM `npc_trainer`
WHERE `ID` = 200004 AND `SpellID` = 5599;
DELETE FROM `npc_trainer`
WHERE `ID` = 200004 AND `SpellID` = 10278;
DELETE FROM `npc_trainer`
WHERE `ID` = 200010 AND `SpellID` = 11719;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 1 AND `skill` = 256 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 1 AND `skill` = 257 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 2 AND `skill` = 267 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 2 AND `skill` = 594 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 4 AND `skill` = 163 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 8 AND `skill` = 253 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 16 AND `skill` = 613 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 64 AND `skill` = 374 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 64 AND `skill` = 375 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 128 AND `skill` = 237 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 256 AND `skill` = 355 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 256 AND `skill` = 593 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 1024 AND `skill` = 573 AND `rank` = 0;
DELETE FROM `playercreateinfo_skills`
WHERE `raceMask` = 0 AND `classMask` = 1024 AND `skill` = 574 AND `rank` = 0;
