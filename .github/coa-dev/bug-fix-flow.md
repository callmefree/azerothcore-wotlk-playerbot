# CoA 仓库：本地修复 bug → 向上游发 issue / PR 流程

本说明适用于两个 fork：

- **core**：`callmefree/azerothcore-wotlk-coa`（上游 `jealous-sound/azerothcore-wotlk-coa`，分支 `main`）
- **bot** ：`callmefree/azerothcore-wotlk-playerbot`（上游 `jealous-sound/azerothcore-wotlk-playerbot`，分支 `Playerbot`）

> 注：因 GitHub 单账号单网络只允许一个 fork，`callmefree` 下 bot 仓库的命名/形态可能随部署方案变化，
> 但"在 fork 修 bug → 向上游发 issue/PR"的流程不变。下文以变量 `<FORK>`、`<UPSTREAM>`、`<BRANCH>` 表示。

## 一、策略：自己优先修复，再上报上游

1. 上游更新通过 `sync-upstream` 工作流自动拉取并合并进 fork（每天 UTC 03:30，或手动 `workflow_dispatch`）。
2. 当你在 fork 里**自己修掉了一个 bug**，应优先把修复保留在 fork 上（保证现网能跑），同时把修复**上报给上游**，让官方合并、减少长期维护负担。
3. 上报方式二选一：
   - **issue**：只描述 bug + 复现 + 你的修复思路/链接（适合上游暂不接受外部 PR，或修复尚未定型）。
   - **PR**  ：直接把修复分支推到 fork 后，向 `jealous-sound` 对应仓库发 Pull Request（适合上游活跃、接受贡献）。

## 二、操作步骤

```bash
# 1) 进入你本地 clone 的 fork 目录
cd path/to/<FORK>

# 2) 切到对应分支并拉取最新（sync 之后）
git fetch origin
git checkout <BRANCH>
git pull origin <BRANCH>

# 3) 新建修复分支
git checkout -b fix/<short-name>

# 4) 修改代码 / 提交
git add -A
git commit -m "fix: <描述>"

# 5) 推送到你的 fork
git push -u origin fix/<short-name>

# 6) 上报上游（见下方脚本）
```

## 三、一键上报脚本 `scripts/report-to-upstream.sh`

```bash
# 发 issue（只描述，不含代码）
./scripts/report-to-upstream.sh issue <UPSTREAM> "标题" [正文文件.md]

# 发 PR（把上面的 fix 分支推到上游评审）
./scripts/report-to-upstream.sh pr <UPSTREAM> <UPSTREAM_BRANCH> "标题"
```

示例（core）：
```bash
./scripts/report-to-upstream.sh issue jealous-sound/azerothcore-wotlk-coa \
  "玩家银行析构崩溃导致可触发 DoS (upstream #4301)"
```

示例（bot）：
```bash
./scripts/report-to-upstream.sh pr jealous-sound/azerothcore-wotlk-playerbot Playerbot \
  "Fix: playerbot 在 XX 场景下崩溃"
```

## 四、自动化兜底（已内置）

- **编译失败**：`windows-build` 工作流失败时会自动在 fork 开 `ci-failure` issue，附运行链接。
- **同步冲突**：`sync-upstream` 与上游合并冲突时，自动 `git merge --abort` 并在 fork 开 `sync-conflict` issue。
  此时需你手动解决冲突后重新运行 sync 工作流。

## 五、注意事项

- 上游 `jealous-sound/*` 部分仓库可能是 **archive（只读）**，此时只能发 issue，不能发 PR（PR 会被拒）。
- 发 PR 前确认你的 fork 分支基于上游最新（先跑一次 sync），避免大量冲突。
- 若修复涉及敏感/未公开逻辑，优先发 issue 描述现象，不要公开完整补丁。
