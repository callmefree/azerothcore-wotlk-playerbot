-- Restore the two missing Ascension totems using the stock totem archetypes 2523/3527.
-- Archive npc pages identify type Totem and portraits 4589/4587; the donor gives faction 35.
-- Ascension summon descriptions identify attack 1103606 and periodic healing aura 1105672.
-- Native Totem::InitStats supplies owner level, racial model and spell-defined summon health.
-- These are reconstructed compatibility templates, not a complete official server-data dump.
-- Only create absent templates; the existence guards prevent REPLACE from deleting an existing row.
SET @ASC_MISSING_SEARING := NOT EXISTS (SELECT 1 FROM `creature_template` WHERE `entry` = 1102523);
SET @ASC_MISSING_HEALING := NOT EXISTS (SELECT 1 FROM `creature_template` WHERE `entry` = 1103527);
REPLACE INTO `creature_template`
(`entry`, `name`, `minlevel`, `maxlevel`, `faction`, `speed_walk`, `speed_run`, `detection_range`,
 `BaseAttackTime`, `RangeAttackTime`, `unit_class`, `unit_flags2`, `type`, `HealthModifier`, `VerifiedBuild`)
SELECT 1102523, 'Searing Totem', 15, 15, 35, 1, 1, 18, 2000, 2000, 1, 2048, 11, 1, 0
WHERE @ASC_MISSING_SEARING = 1;

REPLACE INTO `creature_template`
(`entry`, `name`, `minlevel`, `maxlevel`, `faction`, `speed_walk`, `speed_run`, `detection_range`,
 `BaseAttackTime`, `RangeAttackTime`, `unit_class`, `unit_flags2`, `type`, `HealthModifier`, `VerifiedBuild`)
SELECT 1103527, 'Healing Stream Totem', 1, 80, 35, 1, 1, 18, 2000, 2000, 1, 2048, 11, 0.05, 0
WHERE @ASC_MISSING_HEALING = 1;

DELETE FROM `creature_template_model` WHERE `CreatureID` IN (1102523, 1103527);
INSERT INTO `creature_template_model`
(`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`)
VALUES
(1102523, 0, 4589, 1, 1, 0),
(1103527, 0, 4587, 1, 1, 0);

DELETE FROM `creature_template_spell` WHERE `CreatureID` IN (1102523, 1103527);
INSERT INTO `creature_template_spell` (`CreatureID`, `Index`, `Spell`, `VerifiedBuild`)
VALUES
(1102523, 0, 1103606, 0),
(1103527, 0, 1105672, 0);

-- The periodic aura triggers a dummy effect; without this binding it never produces a heal.
-- Reuse the same validated dummy -> 52042 heal path as stock Healing Stream (52041).
DELETE FROM `spell_script_names` WHERE `spell_id` = 1152041 AND `ScriptName` = 'spell_sha_healing_stream_totem';
INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES (1152041, 'spell_sha_healing_stream_totem');
