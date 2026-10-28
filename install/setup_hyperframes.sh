#!/usr/bin/env bash
# 準備 HyperFrames 算繪環境（取代舊的 setup_playwright.sh）
# 用法：bash install/setup_hyperframes.sh
#
# HyperFrames 一律用 npx 執行，套件落在 npm 快取（~/.npm/_npx），不會在專案裡產生 node_modules，
# 所以雲端硬碟上的專案資料夾不受影響（GOTCHAS D-1）。這支只做三件事：
# 檢查 Node.js 22+ 與 FFmpeg、預先抓好 CLI、預先下載算繪用的 Chrome。
set -e

need() { command -v "$1" >/dev/null 2>&1 || { echo "✗ 找不到 $1：$2" >&2; exit 1; }; }

need node   "請先安裝 Node.js 22 以上（https://nodejs.org）"
need npx    "npx 隨 Node.js 附帶，請重新安裝 Node.js"
need ffmpeg "HyperFrames 本機算繪需要 FFmpeg（Windows: winget install Gyan.FFmpeg（Windows on ARM 先試 winget install BtbN.FFmpeg.GPL.9.0 --architecture arm64，被 Smart App Control 擋再改裝 Gyan.FFmpeg）；macOS: brew install ffmpeg）"

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "✗ Node.js 版本是 $(node --version)，HyperFrames 需要 22 以上" >&2
  exit 1
fi
echo "✓ Node.js $(node --version)、FFmpeg 已就緒"

echo "→ 取得 HyperFrames CLI"
npx --yes hyperframes@0.8.181 --version

echo "→ 下載算繪用的 Chrome（已存在會直接略過）"
npx --yes hyperframes@0.8.181 browser ensure

echo "→ 環境自我檢查"
npx --yes hyperframes@0.8.181 doctor || echo "  ⚠ doctor 有警告，見上方輸出（GPU 相關警告不影響出片）"

echo ""
echo "✓ HyperFrames 就緒。在範本資料夾內："
echo "    npx --yes hyperframes@0.8.181 preview          # 瀏覽器預覽（存檔自動重新整理）"
echo "    npx --yes hyperframes@0.8.181 check            # 出片前的關卡，必須通過"
echo "    npx --yes hyperframes@0.8.181 render -o final.mp4"
