#!/usr/bin/env bash
# 在 callmefree 的 fork 中修复特定 bug 后，向上游 jealous-sound 发 issue / PR。
#
# 前置：
#   - 本地已 `gh auth login`（callmefree 账号，具备 repo 权限）
#   - 当前位于 fork 仓库目录内，且修复分支已 git push 到 callmefree
#
# 用法：
#   发 issue:  report-to-upstream.sh issue <UPSTREAM_REPO> "<标题>" [正文文件.md]
#   发 PR:     report-to-upstream.sh pr   <UPSTREAM_REPO> <UPSTREAM_BASE_BRANCH> "<标题>"
#
# 示例（core）：
#   report-to-upstream.sh issue jealous-sound/azerothcore-wotlk-coa "玩家银行析构崩溃 (DoS)"
# 示例（bot）：
#   report-to-upstream.sh pr jealous-sound/azerothcore-wotlk-playerbot Playerbot "Fix: xxx"
set -euo pipefail

MODE="${1:-}"
UPSTREAM="${2:-}"
TITLE="${3:-}"
BODY_FILE="${4:-}"

if [[ -z "$MODE" || -z "$UPSTREAM" || -z "$TITLE" ]]; then
  echo "用法:" >&2
  echo "  $0 issue <UPSTREAM_REPO> \"<标题>\" [正文文件.md]" >&2
  echo "  $0 pr   <UPSTREAM_REPO> <UPSTREAM_BASE_BRANCH> \"<标题>\"" >&2
  exit 1
fi

# 当前 fork 仓库（owner/name）与分支
FORK="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
HEAD_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [[ "$MODE" == "issue" ]]; then
  BODY=""
  if [[ -n "$BODY_FILE" && -f "$BODY_FILE" ]]; then
    BODY="$(cat "$BODY_FILE")"
  fi
  if [[ -z "$BODY" ]]; then
    BODY="来自 fork \`$FORK\` 分支 \`$HEAD_BRANCH\` 的修复/报告。\n\n（请用正文文件或在此补充复现步骤、日志、修复说明）"
  fi
  echo ">> 向 $UPSTREAM 创建 issue: $TITLE"
  gh issue create --repo "$UPSTREAM" --title "$TITLE" --body "$BODY"
  echo "完成。"

elif [[ "$MODE" == "pr" ]]; then
  BASE_BRANCH="${4:-}"
  if [[ -z "$BASE_BRANCH" ]]; then
    echo "错误：PR 模式需要指定上游 base 分支，例如 Playerbot / main" >&2
    exit 1
  fi
  # PR 的 head 必须带 fork owner 前缀
  HEAD_REF="callmefree:$HEAD_BRANCH"
  echo ">> 向 $UPSTREAM 创建 PR: $TITLE (head=$HEAD_REF base=$BASE_BRANCH)"
  gh pr create --repo "$UPSTREAM" --head "$HEAD_REF" --base "$BASE_BRANCH" --title "$TITLE" --fill \
    || gh pr create --repo "$UPSTREAM" --head "$HEAD_REF" --base "$BASE_BRANCH" --title "$TITLE"
  echo "完成。"

else
  echo "错误：MODE 必须是 issue 或 pr" >&2
  exit 1
fi
