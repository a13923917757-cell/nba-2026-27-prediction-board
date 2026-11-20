#!/usr/bin/env bash
# 每日自动更新：抓最新排名 + 重建逐日走势 + 推送到 GitHub
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PROJ="$(pwd)"
REPO="${NBA_REPO_DIR:-$HOME/nba-repo}"
TOKEN_FILE="$HOME/.config/nba_gh_token"
REMOTE="https://x-access-token:$(cat "$TOKEN_FILE" 2>/dev/null)@github.com/a13923917757-cell/nba-2026-27-prediction-board.git"

echo "[1/4] 抓取最新排名"
python3 scripts/update_data.py || echo "update_data 失败，继续"

echo "[2/4] 重建逐日走势"
python3 scripts/build_history.py || echo "build_history 失败，继续"

echo "[3/4] 同步到本地仓库"
if [ ! -d "$REPO/.git" ]; then
  git clone -q "$REMOTE" "$REPO" || { echo "clone 失败"; exit 1; }
else
  git -C "$REPO" remote set-url origin "$REMOTE"
  git -C "$REPO" pull -q --rebase origin main || git -C "$REPO" pull -q origin main || true
fi
cp "$PROJ/data.json" "$PROJ/history.json" "$REPO/"
cp "$PROJ/NBA预测积分榜.html" "$REPO/index.html"
cp -r "$PROJ/assets/"* "$REPO/assets/" 2>/dev/null || true
cp "$PROJ/scripts/"*.py "$REPO/scripts/" 2>/dev/null || true

echo "[4/4] 提交并推送"
cd "$REPO" || exit 1
git config user.name "Doubao Bot"
git config user.email "doubao@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then
  echo "无变化，跳过推送"
else
  git commit -q -m "chore: 每日数据更新 $(date '+%Y-%m-%d %H:%M')"
  git push -q origin main && echo "已推送：$(git log --oneline -1)"
fi
