-- Witch Hunter's captured starter rifle has a zero client ranged-distance multiplier.
-- Normal rifles use 100 percent. Keep independently corrected/customized values.
UPDATE `item_template` SET `RangedModRange` = 100
WHERE `entry` = 484364 AND `class` = 2 AND `subclass` = 3
    AND `InventoryType` = 26 AND `RangedModRange` = 0;
