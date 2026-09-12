#include "../../../../../modules/mod-wxl-extended-dbc/src/WxlDeprecatedSpellReferences.h"
#include "gtest/gtest.h"

TEST(DeprecatedSpellReferences, ClearsOnlyConfirmedAbsentSlots)
{
    uint32 total = 0;
    for (auto row : ModWxlDbc::DeprecatedDifficultyRows)
    {
        total += ModWxlDbc::ClearDeprecatedDifficultyReferences(row, [](int32) { return false; });
        if (row.ID == 1908)
            EXPECT_EQ(row.SpellID[0], 2100635);
        if (row.ID == 1909)
            EXPECT_EQ(row.SpellID[0], 2100640);
        EXPECT_EQ(ModWxlDbc::ClearDeprecatedDifficultyReferences(row, [](int32) { return false; }), 0u);
    }
    EXPECT_EQ(total, 10u);
}

TEST(DeprecatedSpellReferences, PreservesRestoredSpellsAndDifferentMappings)
{
    auto row = ModWxlDbc::DeprecatedDifficultyRows[0];
    EXPECT_EQ(ModWxlDbc::ClearDeprecatedDifficultyReferences(row,
        [](int32 spell) { return spell == 2100637; }), 1u);
    EXPECT_EQ(row.SpellID[2], 2100637);
    EXPECT_EQ(row.SpellID[3], 2100637);
    row = ModWxlDbc::DeprecatedDifficultyRows[0];
    row.SpellID[1] = 123;
    EXPECT_EQ(ModWxlDbc::ClearDeprecatedDifficultyReferences(row, [](int32) { return false; }), 0u);
    EXPECT_EQ(row.SpellID[2], 2100637);
    row.ID = 999;
    EXPECT_EQ(ModWxlDbc::ClearDeprecatedDifficultyReferences(row, [](int32) { return false; }), 0u);
}
