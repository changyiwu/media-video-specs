#!/usr/bin/env bash
# 環境檢查腳本：給 agent 第 1 階段呼叫
# 輸出每個元件的狀態，agent 依此決定要不要安裝
set -u

check() {
  local name="$1" cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "OK  $name"
  else
    echo "MISS $name"
  fi
}

echo "=== media-video-specs 環境檢查 ==="
check "python"     "python --version || python3 --version"
check "pip"        "pip --version || pip3 --version"
check "edge-tts"   "pip show edge-tts || pip3 show edge-tts"
check "node"       "node --version"
check "npm"        "npm --version"
check "ffmpeg"     "ffmpeg -version"
check "ffprobe"    "ffprobe -version"
# tools/subset_fonts.py 出片前字型瘦身（GOTCHAS D-12）
check "fonttools"  "python -c 'import fontTools' || python3 -c 'import fontTools'"

# 字體（多平台）
# Windows Git Bash 不一定有 $USER，退回 $USERNAME，兩者皆無時給空字串避免 set -u 中斷
WHO="${USER:-${USERNAME:-}}"
FONT_OK=0
for p in \
  "$HOME/AppData/Local/Microsoft/Windows/Fonts/GenSekiGothic2TW-H.otf" \
  "${LOCALAPPDATA:-$HOME/AppData/Local}/Microsoft/Windows/Fonts/GenSekiGothic2TW-H.otf" \
  "/c/Users/$WHO/AppData/Local/Microsoft/Windows/Fonts/GenSekiGothic2TW-H.otf" \
  "$HOME/Library/Fonts/GenSekiGothic2TW-H.otf" \
  "$HOME/.fonts/GenSekiGothic2TW-H.otf" \
  "$HOME/.local/share/fonts/GenSekiGothic2TW-H.otf"; do
  if [ -f "$p" ]; then FONT_OK=1; break; fi
done
if [ "$FONT_OK" = "1" ]; then echo "OK  fonts (GenSekiGothic2TW-H)"; else echo "MISS fonts (GenSekiGothic2TW)"; fi

# 範本內的字型副本：HyperFrames 只認專案資料夾內的字檔，算繪靠的是這幾份，不是系統字型（GOTCHAS D-2）
REPO="$(dirname "$(dirname "$(realpath "$0")")")"
MISSING_PROJ=""
for ex in "$REPO"/examples/*; do
  [ -f "$ex/assets/fonts/GenSekiGothic2TW-H.otf" ] || MISSING_PROJ="$MISSING_PROJ $(basename "$ex")"
done
if [ -z "$MISSING_PROJ" ]; then
  echo "OK  fonts in examples/*/assets/fonts"
else
  echo "MISS fonts in examples:$MISSING_PROJ（bash install/install_fonts.sh）"
fi

# Node.js 版本：HyperFrames 需要 22+
if node -e 'process.exit(+process.versions.node.split(".")[0] >= 22 ? 0 : 1)' >/dev/null 2>&1; then
  echo "OK  node >= 22"
else
  echo "MISS node >= 22（HyperFrames 需要）"
fi

# HyperFrames（算繪引擎，用 npx 執行）
# 用 --no-install 避免這裡觸發下載；沒有就印 MISS，交給 setup_hyperframes.sh 補
if npx --no-install hyperframes@0.8.181 --version >/dev/null 2>&1; then
  echo "OK  hyperframes"
else
  echo "MISS hyperframes（bash install/setup_hyperframes.sh）"
fi

# 算繪用的 Chrome（HyperFrames 自己管理的快取，不是系統的 Chrome）
if npx --no-install hyperframes@0.8.181 browser path >/dev/null 2>&1; then
  echo "OK  hyperframes chrome"
else
  echo "MISS hyperframes chrome（bash install/setup_hyperframes.sh）"
fi

# Kokoro TTS（選用：只有 generate_narration.py --tts kokoro 才需要）
PY="${HYPERFRAMES_PYTHON:-python}"
if "$PY" -c "import kokoro_onnx, soundfile" >/dev/null 2>&1; then
  echo "OK  kokoro-onnx (選用)"
else
  echo "MISS kokoro-onnx (選用，pip install kokoro-onnx soundfile；預設的 Edge-TTS 不需要)"
fi

# 選用：brotli 讓字型瘦身輸出 woff2；Pillow 給 tools/treat_images.py 照片套色
if python -c "import brotli" >/dev/null 2>&1 || python3 -c "import brotli" >/dev/null 2>&1; then
  echo "OK  brotli (選用)"
else
  echo "MISS brotli (選用，pip install brotli；沒有也能瘦身，只是維持 .otf)"
fi
if python -c "import pypinyin, opencc" >/dev/null 2>&1 || python3 -c "import pypinyin, opencc" >/dev/null 2>&1; then
  echo "OK  pypinyin+opencc (選用)"
else
  echo "MISS pypinyin+opencc (選用，pip install pypinyin opencc-python-reimplemented；只有多音字預檢要用)"
fi
if python -c "import PIL" >/dev/null 2>&1 || python3 -c "import PIL" >/dev/null 2>&1; then
  echo "OK  pillow"
else
  echo "MISS pillow（pip install pillow；審片 contact sheet 與照片套色要用）"
fi
