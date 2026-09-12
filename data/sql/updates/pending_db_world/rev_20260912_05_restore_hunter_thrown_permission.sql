-- The Ascension overlay replaces the v20 row granting hunters the Thrown skill (176).
-- Preserve the v20 permission using an ID unused by both supplied DBC layers.
DELETE FROM `skillraceclassinfo_dbc` WHERE `ID` = 529;
INSERT INTO `skillraceclassinfo_dbc`
    (`ID`, `SkillID`, `RaceMask`, `ClassMask`, `Flags`, `MinLevel`, `SkillTierID`, `SkillCostIndex`) VALUES
(529, 176, -1, 4, 128, 0, 0, 0);
