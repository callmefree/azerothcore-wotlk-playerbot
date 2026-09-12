-- The exported all-hit mask includes two bits that this core never emits.
-- PROC_HIT_MASK_ALL is 0x2FFF (12287); retain every supported hit outcome.
-- This does not invent implementations for the unsupported Ascension outcomes.
UPDATE `spell_proc` SET `HitMask` = 12287 WHERE `HitMask` = 32767;
