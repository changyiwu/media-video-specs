#!/usr/bin/env bash
# 把影片製作流程打包成目標 agent 的 skill
# 用法：bash install/pack_skill.sh <skill-name> <video-type 01|02|03> [--target claude|codex|opencode|antigravity|all]
# --target 省略時預設 all（四家 agent 全裝），本 repo 對四家 agent 對等支援。
set -e

NAME="${1:-video-maker}"
TYPE="${2:-02}"
TARGET="all"
for arg in "$@"; do
  case "$arg" in
    --target=*) TARGET="${arg#--target=}" ;;
  esac
done

case "$TYPE" in
  01) TITLE="活動紀錄影片"; TRIGGER="做一支活動紀錄/婚禮/研習/比賽影片" ;;
  02) TITLE="教學影片";     TRIGGER="做一支教學影片/學科解釋影片" ;;
  03) TITLE="社群科普影片"; TRIGGER="做一支社群科普/IG/YouTube Shorts 短片" ;;
  *)  echo "Type 必須是 01 / 02 / 03"; exit 1 ;;
esac

REPO_ROOT="$(dirname "$(dirname "$(realpath "$0")")")"

ALL_TARGETS="claude codex opencode antigravity"
case "$TARGET" in
  all) TARGETS="$ALL_TARGETS" ;;
  claude|codex|opencode|antigravity) TARGETS="$TARGET" ;;
  *) echo "Target 必須是 claude / codex / opencode / antigravity / all"; exit 1 ;;
esac

# 各 agent 的 skill 安裝根目錄（單一真相來源見 BOOTSTRAP.md 階段 0）
skill_root() {
  case "$1" in
    claude)      echo "$HOME/.claude/skills" ;;
    codex)       echo "$HOME/.agents/skills" ;;
    opencode)    echo "$HOME/.config/opencode/skills" ;;
    antigravity) echo "$HOME/.gemini/config/skills" ;;
  esac
}

for t in $TARGETS; do
  SKILL_DIR="$(skill_root "$t")/$NAME"
  META_FILE="$SKILL_DIR/SKILL.md"
  mkdir -p "$SKILL_DIR"

  cat > "$META_FILE" <<EOF
---
name: $NAME
description: 依 media-video-specs 第 $TYPE 類規範製作 $TITLE
target: $t
---

# $TITLE 生成技能（$NAME）

## 用途
依照 media-video-specs 第 $TYPE 類規範製作 $TITLE。

## 觸發情境
使用者說：
- 「$TRIGGER」
- 「按照規範做一支 $TITLE」
- 「跑 $NAME 工作流」

## 工作流
1. 確認主題、片長、素材狀況
2. **先讀踩坑筆記**：\`$REPO_ROOT/GOTCHAS.md\`（A 流程 / B 字幕 / D HyperFrames / E 音訊）
3. 讀規範：\`$REPO_ROOT/specs/$TYPE-*.md\`
4. **產出 SCRIPT.md 與 DESIGN.md 給使用者確認後才動工**（GOTCHAS A-3，不可跳過）
5. fork 範本：複製 \`$REPO_ROOT/examples/$TYPE-*/\` 到工作目錄（連同 \`assets/fonts/\`；讀音替換表在 \`$REPO_ROOT/tts-lexicon.md\`，工作目錄不在 repo 裡時設 \`TTS_LEXICON=$REPO_ROOT/tts-lexicon.md\`）
6. 跑該 spec 第 9 / 11 章 checklist
7. 生成旁白並稽核時間軸：\`python generate_narration.py\`（Edge-TTS；\`--tts kokoro\` 為備案）
8. 文字定稿後 \`python $REPO_ROOT/tools/subset_fonts.py --project <工作目錄>\` 瘦身字型，再 \`npx --yes hyperframes@0.8.181 check\`，必須通過（缺素材、動畫被切掉都會在這裡擋下）
9. \`npx --yes hyperframes@0.8.181 render -o final.mp4\`，再 \`python $REPO_ROOT/tools/loudness.py final.mp4 --apply\`（成片 −15 LUFS）
10. 給使用者預覽 → 確認後存檔；這時才聽出念錯字，用 \`$REPO_ROOT/tools/fix_voice.py\` 修，不要整頁重跑 TTS

## 規範路徑
\`$REPO_ROOT/specs/$TYPE-*.md\`

## 範本路徑
\`$REPO_ROOT/examples/$TYPE-*/\`

## 完整流程
\`$REPO_ROOT/BOOTSTRAP.md\`（5 階段）

## 主要工具
- Edge-TTS（預設女聲 zh-TW-HsiaoChenNeural）；備案 HyperFrames 內建 Kokoro TTS
- HyperFrames（GSAP 時間軸 + 逐格算繪成 mp4，需要 Node.js 22+ 與 FFmpeg）
- KaTeX（數學）
- 源石黑體（執行 \`bash $REPO_ROOT/install/install_fonts.sh\` 安裝）
- 共用工具（字型瘦身、響度、修念錯字、授權照片）：\`$REPO_ROOT/tools/\`，說明在 \`$REPO_ROOT/tools/README.md\`

## 注意事項
- HyperFrames 一律用 npx 執行，不要在雲端硬碟上的專案裡 npm install
- 時間軸寫在標籤的 \`data-start\`／\`data-duration\`，不要用 JS 事後設定
- Edge-TTS 並行會被斷線，序列 + retry 3 次
- 字幕單行 ≤ 25 字，不換行
- 開工先問清楚：學生目前學到第幾冊第幾章（非教學片則問觀眾看片時的階段）、新學還是複習（新學語速 -10%、留白 2～4 秒；複習 +35%、留白 1～2 秒）、能不能暫停（預設從頭播到尾，不做按暫停練習頁）
- 字體放在專案自己的 \`assets/fonts/\`，不能用 \`../\` 引用專案外的檔案
EOF

  echo "✓ $t → $SKILL_DIR"

  case "$t" in
    opencode)
      echo "    ℹ️  OpenCode 額外需要：在你的 opencode.json 或 .opencode/config.json 內"
      echo "        確認 \"skills\" 路徑包含 ~/.config/opencode/skills/"
      ;;
    antigravity)
      echo "    ℹ️  Antigravity 2.x 是獨立桌面 Agent 應用（不是 IDE）"
      echo "        請在 App 內確認 ~/.gemini/config/skills/ 的 skill 已被載入"
      echo "        若無自動偵測，請手動將 $META_FILE 內容貼入 Antigravity 的 Custom Agent 設定"
      ;;
  esac
done

echo ""
echo "  技能名稱 : $NAME（第 $TYPE 類・$TITLE）"
echo "  觸發詞   : 「$TRIGGER」"
