/*
 * mod-wxl-dbc — apply continuation files after LoadDBCStores().
 */

#include "WxlDbcLoader.h"

#include "WxlDbcRegistry.h"
#include "WxlDbcScan.h"
#include "WxlDeprecatedSpellReferences.h"

#include "Config.h"
#include "DBCStores.h"
#include "Log.h"
#include "World.h"

#include <filesystem>

namespace ModWxlDbc
{
    void ApplyContinuations()
    {
        if (!sConfigMgr->GetOption<bool>("WxlDbc.Enable", true))
        {
            LOG_INFO("module.wxl-dbc", "Disabled via WxlDbc.Enable.");
            return;
        }

        InitDbcRegistry();

        std::string const continuationSubPath =
            sConfigMgr->GetOption<std::string>("WxlDbc.ContinuationPath", "dbc-continuations");

        std::filesystem::path const root =
            std::filesystem::path(sWorld->GetDataPath()) / continuationSubPath;

        if (!std::filesystem::exists(root))
        {
            LOG_INFO("module.wxl-dbc", "No continuation folder at {} (nothing to apply).", root.string());
            return;
        }

        std::vector<ContinuationEntry> const entries = DiscoverContinuations(root);
        if (entries.empty())
        {
            LOG_INFO("module.wxl-dbc", "No continuation files found under {}.", root.string());
            return;
        }

        LOG_INFO("module.wxl-dbc", "Applying {} continuation file(s) from {}...", entries.size(), root.string());

        uint32 filesApplied = 0;
        uint32 rowsInjected = 0;
        uint32 unregisteredFiles = 0;

        for (ContinuationEntry const& entry : entries)
        {
            if (!HasContinuationStore(entry.baseDbcFile.c_str()))
            {
                ++unregisteredFiles;
                LOG_DEBUG("module.wxl-dbc", "Skipping {}: no registered server store.", entry.path.string());
                continue;
            }

            uint32 const injected = InjectContinuationByTable(entry.baseDbcFile.c_str(), entry.path.string().c_str());
            if (injected == 0)
            {
                LOG_WARN("module.wxl-dbc", "No rows injected from {} (empty file or load error).", entry.path.string());
                continue;
            }

            ++filesApplied;
            rowsInjected += injected;
            LOG_INFO("module.wxl-dbc", "  {} -> {} row(s) into {}", entry.path.filename().string(), injected, entry.baseDbcFile);
        }

        // All overlays are now loaded, but core difficulty caches have not been built yet.
        // DBC storage allocates mutable rows; its public lookup exposes a const view.
        uint32 deprecatedReferences = 0;
        for (auto const& expected : DeprecatedDifficultyRows)
            if (auto const* row = sSpellDifficultyStore.LookupEntry(expected.ID))
                deprecatedReferences += ClearDeprecatedDifficultyReferences(
                    *const_cast<SpellDifficultyEntry*>(row),
                    [](int32 spellId) { return sSpellStore.LookupEntry(spellId) != nullptr; });
        if (deprecatedReferences)
            LOG_INFO("module.wxl-dbc", "Cleared {} absent, archive-confirmed deprecated spell difficulty references.",
                deprecatedReferences);

        if (unregisteredFiles)
            LOG_INFO("module.wxl-dbc", "Skipped {} continuation file(s) without a registered server store.",
                unregisteredFiles);

        LOG_INFO("module.wxl-dbc", "Done. {} file(s), {} row(s) injected. Base data/dbc/ files were not modified.",
            filesApplied, rowsInjected);
    }
}
