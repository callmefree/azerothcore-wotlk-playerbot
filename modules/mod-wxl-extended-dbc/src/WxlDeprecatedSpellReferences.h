#ifndef WXL_DEPRECATED_SPELL_REFERENCES_H
#define WXL_DEPRECATED_SPELL_REFERENCES_H

#include "DBCStructure.h"
#include <array>

namespace ModWxlDbc
{
// These eight IDs have explicitly DEPRECATED titles in the preserved Exiles pages.
// Match the entire captured difficulty row; never apply this policy to arbitrary missing spells.
inline constexpr std::array<SpellDifficultyEntry, 3> DeprecatedDifficultyRows =
{{
    {1908, {2100635, 2100636, 2100637, 2100637}},
    {1909, {2100640, 2100641, 2100642, 2100642}},
    {2805, {2135213, 2135214, 2135215, 2135216}}
}};

template <typename SpellExists>
uint32 ClearDeprecatedDifficultyReferences(SpellDifficultyEntry& row, SpellExists spellExists)
{
    for (auto const& expected : DeprecatedDifficultyRows)
    {
        if (row.ID != expected.ID)
            continue;
        for (uint8 slot = 0; slot < MAX_DIFFICULTY; ++slot)
            if (row.SpellID[slot] != expected.SpellID[slot])
                return 0;

        uint32 cleared = 0;
        // The first entries of 1908/1909 are not among the confirmed deprecated IDs.
        uint8 const firstSlot = row.ID == 2805 ? 0 : 1;
        for (uint8 slot = firstSlot; slot < MAX_DIFFICULTY; ++slot)
            if (!spellExists(row.SpellID[slot]))
            {
                row.SpellID[slot] = 0;
                ++cleared;
            }
        return cleared;
    }
    return 0;
}
}

#endif
