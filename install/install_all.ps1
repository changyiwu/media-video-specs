# Windows PowerShell 版本：一鍵安裝所有 optional 元件
# 用法：powershell -ExecutionPolicy Bypass -File install/install_all.ps1
$ErrorActionPreference = 'Stop'

Write-Host "1/3  安裝 Edge-TTS 與 tools/ 用到的套件（字型瘦身、照片套色）"
pip install --quiet edge-tts fonttools brotli pillow pypinyin opencc-python-reimplemented

Write-Host "2/3  下載源石黑體"
$FontsDir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
New-Item -ItemType Directory -Force -Path $FontsDir | Out-Null
$Upstream = "https://github.com/ButTaiwan/genseki-font/raw/master/otf/TW"
foreach ($f in @("GenSekiGothic2TW-H.otf","GenSekiGothic2TW-B.otf","GenSekiGothic2TW-M.otf")) {
  $dest = "$FontsDir\$f"
  if (Test-Path $dest) {
    Write-Host "  ✓ 已存在 $f"
  } else {
    Write-Host "  ↓ 下載 $f"
    Invoke-WebRequest -Uri "$Upstream/$f" -OutFile $dest
  }
}

# 同步 repo 副本，再複製進每個範本的 assets\fonts：
# HyperFrames 不接受 ../ 跳出專案根目錄的字型路徑，每個影片專案都要有自己的一份（GOTCHAS D-2）
$Repo = Split-Path (Split-Path $PSCommandPath -Parent) -Parent
$Projects = @($Repo) + @(Get-ChildItem (Join-Path $Repo "examples") -Directory | ForEach-Object FullName)
foreach ($p in $Projects) {
  $dir = Join-Path $p "assets\fonts"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  foreach ($f in @("GenSekiGothic2TW-H.otf","GenSekiGothic2TW-B.otf","GenSekiGothic2TW-M.otf")) {
    if (-not (Test-Path "$dir\$f")) { Copy-Item "$FontsDir\$f" "$dir\$f" }
  }
}

Write-Host "3/3  準備 HyperFrames（含算繪用 Chrome）"
# HyperFrames 一律用 npx 執行，套件落在 npm 快取，不會在雲端硬碟上的專案裡產生 node_modules（GOTCHAS D-1）
$NodeMajor = [int]((node --version).TrimStart('v').Split('.')[0])
if ($NodeMajor -lt 22) { throw "Node.js 版本是 $(node --version)，HyperFrames 需要 22 以上" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "找不到 ffmpeg：winget install Gyan.FFmpeg（Windows on ARM 先試 winget install BtbN.FFmpeg.GPL.9.0 --architecture arm64，被 Smart App Control 擋再改裝 Gyan.FFmpeg）" }
npx --yes hyperframes@0.8.181 --version
npx --yes hyperframes@0.8.181 browser ensure

Write-Host ""
Write-Host "✅ 全部就緒。可以進入階段 2（試做影片）了"
