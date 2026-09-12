-- Ascension's SkillRaceClassInfo rows restrict Arms and Demonology to class 10.
-- Preserve those rows and add the stock v20 permissions for Warrior and Warlock.
-- IDs 527 and 528 are unused in both supplied DBC sets and the current SQL export;
-- separate IDs prevent dbc1-ascension from overwriting these SQL permissions.
DELETE FROM `skillraceclassinfo_dbc` WHERE `ID` IN (527, 528);
INSERT INTO `skillraceclassinfo_dbc`
(`ID`, `SkillID`, `RaceMask`, `ClassMask`, `Flags`, `MinLevel`, `SkillTierID`, `SkillCostIndex`) VALUES
(527, 26, -1, 1, 1040, 0, 0, 0),
(528, 354, -1, 256, 1040, 0, 0, 0);
