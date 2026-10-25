#!/usr/bin/env python3
"""跨平台的 media-video-specs 安裝 orchestrator。

用法：
  python install/setup.py check       # 環境檢查
  python install/setup.py fonts       # 下載源石黑體
  python install/setup.py hyperframes # 準備 HyperFrames（Node 22+、FFmpeg、算繪用 Chrome）
  python install/setup.py py-deps     # 安裝 Edge-TTS 與 tools/ 用到的 Python 套件（fonttools、brotli、pillow、pypinyin、opencc）
  python install/setup.py all         # 一次裝完
  python install/setup.py pack <skill-name> <01|02|03> [--target claude|codex|opencode|antigravity|all]
                                      # --target 省略時預設 all（四家 agent 全裝）

不依賴 bash，Windows / macOS / Linux 都能跑。
"""
from __future__ import annotations
import os, sys, shutil, subprocess, urllib.request, platform
from pathlib import Path

# 驗證過的 HyperFrames 版本。不指定版本時，npx 一遇到新版就拒絕執行（GOTCHAS D-11）
HF = "hyperframes@0.8.181"

# Windows 主控台預設 CP950，印 ✓ 或導向檔案時會丟 UnicodeEncodeError
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
PLATFORM = platform.system()  # Windows / Darwin / Linux

FONT_FILES = ["GenSekiGothic2TW-H.otf", "GenSekiGothic2TW-B.otf", "GenSekiGothic2TW-M.otf"]
FONT_UPSTREAM = "https://github.com/ButTaiwan/genseki-font/raw/master/otf/TW"


def font_target_dir() -> Path:
    if PLATFORM == "Windows":
        return Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    if PLATFORM == "Darwin":
        return Path.home() / "Library" / "Fonts"
    return Path.home() / ".local" / "share" / "fonts"


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def have_pkg(pkg: str) -> bool:
    return subprocess.call(
        [sys.executable, "-m", "pip", "show", pkg],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ) == 0


def examples() -> list[Path]:
    return sorted(p for p in (REPO / "examples").iterdir() if p.is_dir())


def node_major() -> int:
    if not have("node"):
        return 0
    out = subprocess.run(["node", "--version"], capture_output=True, text=True)
    return int(out.stdout.strip().lstrip("v").split(".")[0] or 0)


def npx(*args: str) -> list[str]:
    # Windows 的 npx 是 npx.cmd，要用完整路徑才叫得起來
    return [shutil.which("npx") or "npx", *args]


def hf_ok(*args: str) -> bool:
    # --no-install：檢查時不觸發下載
    if not have("npx"):
        return False
    return subprocess.call(npx("--no-install", HF, *args),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def cmd_check():
    rows = [
        ("python", have("python") or have("python3")),
        ("pip", have("pip") or have("pip3")),
        ("edge-tts", have_pkg("edge-tts")),
        ("node", have("node")),
        ("npm", have("npm")),
        ("ffmpeg", have("ffmpeg")),
        ("ffprobe", have("ffprobe")),
        # tools/subset_fonts.py 出片前字型瘦身（GOTCHAS D-12）
        ("fonttools", have_pkg("fonttools")),
        ("node >= 22", node_major() >= 22),
        ("fonts", (font_target_dir() / FONT_FILES[0]).exists()),
        # HyperFrames 只認專案資料夾內的字檔，算繪靠的是範本裡這幾份（GOTCHAS D-2）
        ("fonts in examples", all((ex / "assets" / "fonts" / FONT_FILES[0]).exists() for ex in examples())),
        ("hyperframes", hf_ok("--version")),
        ("hyperframes chrome", hf_ok("browser", "path")),
    ]
    print("=== media-video-specs 環境檢查 ===")
    for name, ok in rows:
        print(f"{'OK  ' if ok else 'MISS'} {name}")
    # 選用：brotli 讓字型瘦身輸出 woff2；pillow 給 tools/treat_images.py 照片套色
    for pkg, why in (("brotli", "沒有也能瘦身，只是維持 .otf"), ("pillow", "只有照片套色要用"),
                     ("pypinyin", "只有多音字預檢要用"), ("opencc-python-reimplemented", "只有多音字預檢要用")):
        print(f"{'OK  ' if have_pkg(pkg) else 'MISS'} {pkg}（選用，{why}）")
    missing = [n for n, ok in rows if not ok]
    if missing:
        print(f"\n缺少 {len(missing)} 個：{', '.join(missing)}")
        print("執行 `python install/setup.py all` 一次補齊（不含 python/node/ffmpeg 本身）")
    else:
        print("\n✅ 全部就緒")


def cmd_fonts():
    target = font_target_dir()
    target.mkdir(parents=True, exist_ok=True)
    # repo 的 assets/fonts 加上每個範本的 assets/fonts：HyperFrames 不接受 ../ 跳出
    # 專案根目錄的字型路徑，每個影片專案都要有自己的一份（GOTCHAS D-2）
    copies = [REPO / "assets" / "fonts"] + [ex / "assets" / "fonts" for ex in examples()]
    for d in copies:
        d.mkdir(parents=True, exist_ok=True)
    print(f"→ 安裝目標：{target}")
    for f in FONT_FILES:
        dest = target / f
        if dest.exists():
            print(f"  ✓ 已存在 {f}")
        else:
            print(f"  ↓ 下載 {f}")
            url = f"{FONT_UPSTREAM}/{f}"
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                dest.unlink(missing_ok=True)
                print(f"  X 下載失敗：{url}")
                print(f"    {e}")
                print("    上游 repo 可能改過目錄結構，請確認 FONT_UPSTREAM 路徑")
                sys.exit(1)
            # 字重檔約 14-17 MB；明顯過小代表拿到的是錯誤頁而不是字型
            if dest.stat().st_size < 1_000_000:
                size = dest.stat().st_size
                dest.unlink(missing_ok=True)
                print(f"  X {f} 只有 {size} bytes，不是字型檔，已刪除")
                sys.exit(1)
        # 同步專案副本
        for d in copies:
            if not (d / f).exists():
                shutil.copy(dest, d / f)
    print(f"✓ 完成。系統字體：{target}；專案副本：assets/fonts 與 examples/*/assets/fonts")
    print("  fork 範本到別處時，連同 assets/fonts/ 一起複製")
    if PLATFORM == "Linux":
        print("  Linux 用戶請執行 fc-cache -fv 重新整理")


def cmd_hyperframes():
    # HyperFrames 一律用 npx 執行，套件落在 npm 快取，不會在雲端硬碟上的專案裡產生 node_modules（GOTCHAS D-1）
    if node_major() < 22:
        print("X 需要 Node.js 22 以上（https://nodejs.org）"); sys.exit(1)
    if not have("ffmpeg"):
        print("X 找不到 ffmpeg（Windows: winget install Gyan.FFmpeg；macOS: brew install ffmpeg）"); sys.exit(1)
    subprocess.run(npx("--yes", HF, "--version"), check=True)
    subprocess.run(npx("--yes", HF, "browser", "ensure"), check=True)
    print("✓ HyperFrames 就緒。在範本資料夾內：npx --yes hyperframes@0.8.181 preview｜check｜render -o final.mp4")


def cmd_install_edge_tts():
    if have_pkg("edge-tts"):
        print("✓ edge-tts 已安裝")
        return
    subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts"], check=True)


# Edge-TTS 加上 tools/ 用到的套件：fonttools＋brotli（字型瘦身）、pillow（照片套色）、pypinyin＋opencc（多音字預檢）
PY_DEPS = ["edge-tts", "fonttools", "brotli", "pillow", "pypinyin", "opencc-python-reimplemented"]


def cmd_py_deps():
    missing = [p for p in PY_DEPS if not have_pkg(p)]
    if not missing:
        print("✓ " + "、".join(PY_DEPS) + " 都已安裝")
        return
    subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=True)


def cmd_all():
    print("1/3  安裝 Edge-TTS 與 tools/ 用到的套件")
    cmd_py_deps()
    print("\n2/3  下載源石黑體")
    cmd_fonts()
    print("\n3/3  準備 HyperFrames")
    cmd_hyperframes()
    print("\n✅ 全部就緒。可以進入階段 2（試做影片）了")


SKILL_PATHS = {
    "claude":      Path.home() / ".claude" / "skills",
    "codex":       Path.home() / ".agents" / "skills",
    "opencode":    Path.home() / ".config" / "opencode" / "skills",
    "antigravity": Path.home() / ".gemini" / "config" / "skills",
}

TYPE_META = {
    "01": ("活動紀錄影片",   "做一支活動紀錄/婚禮/研習/比賽影片"),
    "02": ("教學影片",       "做一支教學影片/學科解釋影片"),
    "03": ("社群科普影片",   "做一支社群科普/IG/YouTube Shorts 短片"),
}


def cmd_pack(args: list[str]):
    if len(args) < 2:
        print("用法：python install/setup.py pack <skill-name> <01|02|03> "
              "[--target claude|codex|opencode|antigravity|all]")
        print("      --target 省略時預設 all（四家 agent 全裝）")
        sys.exit(1)
    name, vtype = args[0], args[1]
    target = "all"
    for a in args[2:]:
        if a.startswith("--target="):
            target = a.split("=", 1)[1]
    if vtype not in TYPE_META:
        print(f"Type 必須是 01/02/03，收到 {vtype}"); sys.exit(1)
    if target != "all" and target not in SKILL_PATHS:
        print(f"Target 必須是 {list(SKILL_PATHS)} 或 all，收到 {target}"); sys.exit(1)

    targets = list(SKILL_PATHS) if target == "all" else [target]
    title, trigger = TYPE_META[vtype]

    for t in targets:
        skill_dir = SKILL_PATHS[t] / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        meta = skill_dir / "SKILL.md"
        meta.write_text(f"""---
name: {name}
description: 依 media-video-specs 第 {vtype} 類規範製作 {title}
target: {t}
---

# {title} 生成技能（{name}）

## 用途
依照 media-video-specs 第 {vtype} 類規範製作 {title}。

## 觸發情境
- 「{trigger}」
- 「按照規範做一支 {title}」
- 「跑 {name} 工作流」

## 工作流
1. 確認主題、片長、素材狀況
2. **先讀踩坑筆記**：`{REPO}/GOTCHAS.md`（A 流程 / B 字幕 / D HyperFrames / E 音訊）
3. 讀規範：`{REPO}/specs/{vtype}-*.md`
4. **產出 SCRIPT.md 與 DESIGN.md 給使用者確認後才動工**（GOTCHAS A-3，不可跳過）
5. fork 範本：複製 `{REPO}/examples/{vtype}-*/` 到工作目錄（連同 `assets/fonts/`；讀音替換表在 `{REPO}/tts-lexicon.md`，工作目錄不在 repo 裡時設 `TTS_LEXICON={REPO}/tts-lexicon.md`）
6. 跑該 spec 第 9 / 11 章 checklist
7. 生成旁白並稽核時間軸：`python generate_narration.py`（Edge-TTS；`--tts kokoro` 為備案）
8. 文字定稿後 `python {REPO}/tools/subset_fonts.py --project <工作目錄>` 瘦身字型，再 `npx --yes hyperframes@0.8.181 check`，必須通過（缺素材、動畫被切掉都會在這裡擋下）
9. `npx --yes hyperframes@0.8.181 render -o final.mp4`，再 `python {REPO}/tools/loudness.py final.mp4 --apply`（成片 −15 LUFS）
10. 給使用者預覽 → 確認後存檔；這時才聽出念錯字，用 `{REPO}/tools/fix_voice.py` 修，不要整頁重跑 TTS

## 規範路徑
`{REPO}/specs/{vtype}-*.md`

## 範本路徑
`{REPO}/examples/{vtype}-*/`

## 完整流程
`{REPO}/BOOTSTRAP.md`（5 階段）

## 注意
- HyperFrames 一律用 npx 執行，不要在雲端硬碟上的專案裡 npm install
- 時間軸寫在標籤的 `data-start`／`data-duration`，不要用 JS 事後設定
- Edge-TTS 並行會被斷線，序列 + retry 3 次
- 字幕單行 ≤ 25 字，不換行
- 開工先問清楚：學生目前學到第幾冊第幾章（非教學片則問觀眾看片時的階段）、新學還是複習（新學語速 -10%、留白 2～4 秒；複習 +35%、留白 1～2 秒）、能不能暫停（預設從頭播到尾，不做按暫停練習頁）
- 旁白預設 Edge-TTS 女聲 zh-TW-HsiaoChenNeural
- 共用工具（字型瘦身、響度、修念錯字、授權照片）說明在 `{REPO}/tools/README.md`
""", encoding="utf-8")
        print(f"✓ {t} → {skill_dir}")

    print("")
    print(f"  技能名稱 : {name}（第 {vtype} 類・{title}）")
    print(f"  觸發詞   : 「{trigger}」")


COMMANDS = {
    "check": cmd_check,
    "fonts": cmd_fonts,
    "hyperframes": cmd_hyperframes,
    "edge-tts": cmd_install_edge_tts,
    "py-deps": cmd_py_deps,
    "all": cmd_all,
}


def main(argv: list[str]):
    if len(argv) < 2:
        print(__doc__); sys.exit(0)
    sub = argv[1]
    if sub == "pack":
        cmd_pack(argv[2:])
    elif sub in COMMANDS:
        COMMANDS[sub]()
    else:
        print(f"未知子指令：{sub}\n"); print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
