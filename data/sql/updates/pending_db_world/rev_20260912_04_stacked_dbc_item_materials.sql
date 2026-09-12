-- Match the effective stacked Item.dbc material; preserve independently changed values.
UPDATE `item_template` SET `Material` = 6 WHERE `entry` = 629930 AND `Material` = 1;
UPDATE `item_template` SET `Material` = 6 WHERE `entry` = 629950 AND `Material` = 2;
UPDATE `item_template` SET `Material` = 7 WHERE `entry` = 2000009 AND `Material` = 8;
UPDATE `item_template` SET `Material` = 7 WHERE `entry` = 2000066 AND `Material` = 8;
UPDATE `item_template` SET `Material` = 7 WHERE `entry` = 2000067 AND `Material` = 8;
