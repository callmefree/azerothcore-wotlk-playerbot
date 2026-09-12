-- Extended DBC achievement and criteria IDs exceed the unsigned SMALLINT limit (65535).
-- Preserve existing progress while allowing the same 32-bit IDs used by the core and DBCs.
ALTER TABLE `character_achievement`
    MODIFY COLUMN `achievement` INT UNSIGNED NOT NULL;

ALTER TABLE `character_achievement_progress`
    MODIFY COLUMN `criteria` INT UNSIGNED NOT NULL;
