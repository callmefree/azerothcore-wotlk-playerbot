/*
 * This file is part of the AzerothCore Project. See AUTHORS file for Copyright information
 * This program is free software; you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software Foundation;
 * either version 2 of the License, or (at your option) any later version.
 */

#include "DBCStore.h"
#include "DBCStructure.h"
#include "DBCfmt.h"
#include <gtest/gtest.h>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <memory>

namespace
{
    class WorldMapAreaDBCtest : public testing::Test
    {
    protected:
        void SetUp() override
        {
            auto const suffix = std::chrono::steady_clock::now().time_since_epoch().count();
            _path = std::filesystem::temp_directory_path() / ("ac-worldmaparea-" + std::to_string(suffix) + ".dbc");
            std::ofstream file(_path, std::ios::binary);
            ASSERT_TRUE(file.is_open());
            auto write = [&file](uint32 value)
            {
                std::array<char, 4> bytes = {
                    char(value), char(value >> 8), char(value >> 16), char(value >> 24)
                };
                file.write(bytes.data(), bytes.size());
            };
            file.write("WDBC", 4);
            write(3);
            write(11);
            write(44);
            write(1);
            // An ordinary zone and two different map-only rows sharing the -1 sentinel.
            for (auto const& row : std::array<std::array<uint32, 11>, 3>{{
                {{10, 0, 12, 0, 0, 0, 0, 0, 0xFFFFFFFF, 0, 0}},
                {{1000, 1760, 0xFFFFFFFF, 0, 0, 0, 0, 0, 0xFFFFFFFF, 0, 0}},
                {{1001, 1761, 0xFFFFFFFF, 0, 0, 0, 0, 0, 0xFFFFFFFF, 0, 0}}
            }})
                for (uint32 value : row)
                    write(value);
            file.put('\0');
            ASSERT_TRUE(file.good());
        }

        void TearDown() override
        {
            std::error_code error;
            std::filesystem::remove(_path, error);
        }

        std::filesystem::path _path;
    };
}

TEST_F(WorldMapAreaDBCtest, PreservesDistinctMapOnlyRowsByRowID)
{
    DBCStorage<WorldMapAreaEntry> store(WorldMapAreaEntryfmt);
    ASSERT_TRUE(store.Load(_path.string().c_str()));
    ASSERT_EQ(store.GetNumRows(), 1002u);
    ASSERT_NE(store.LookupEntry(10), nullptr);
    EXPECT_EQ(store.LookupEntry(10)->area_id, 12);
    EXPECT_EQ(store.LookupEntry(12), nullptr);
    ASSERT_NE(store.LookupEntry(1000), nullptr);
    ASSERT_NE(store.LookupEntry(1001), nullptr);
    EXPECT_EQ(store.LookupEntry(1000)->area_id, -1);
    EXPECT_EQ(store.LookupEntry(1001)->area_id, -1);
    EXPECT_EQ(store.LookupEntry(1000)->map_id, 1760u);
    EXPECT_EQ(store.LookupEntry(1001)->map_id, 1761u);
}

TEST_F(WorldMapAreaDBCtest, ReplacementDoesNotDeleteSharedBaseAllocation)
{
    auto replacement = std::make_unique<WorldMapAreaEntry>();
    DBCStorage<WorldMapAreaEntry> store(WorldMapAreaEntryfmt);
    ASSERT_TRUE(store.Load(_path.string().c_str()));
    *replacement = *store.AssertEntry(1000);
    replacement->map_id = 2000;
    store.EnsureCapacity(2002);
    store.ReplaceEntry(1000, replacement.get());
    EXPECT_EQ(store.LookupEntry(1000)->map_id, 2000u);
    EXPECT_EQ(store.AssertEntry(1001)->map_id, 1761u);
    EXPECT_EQ(store.GetNumRows(), 2002u);
}
