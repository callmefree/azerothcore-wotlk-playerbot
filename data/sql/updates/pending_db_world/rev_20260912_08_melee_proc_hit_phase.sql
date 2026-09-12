-- Ascension's effective DBC flags include melee-ability hits (0x10) for these proc auras.
-- The stock SQL rows have phase 0: SpellMgr rejects those ability events without a hit phase.
-- 22648: Call of Eskhandar; 46910/46911: Furious Attacks; 51123/51127-51130: Killing Machine.
-- Preserve DBC-inherited flags, hit filters, rates, cooldowns and charges. Do not broaden to cast/finish.
UPDATE `spell_proc` SET `SpellPhaseMask` = 2
WHERE `SpellId` IN (22648, 46910, 46911, 51123, 51127, 51128, 51129, 51130)
    AND `SpellPhaseMask` = 0 AND `ProcFlags` = 0;
