# 看這台電腦的 CPU、記憶體、NVIDIA GPU、硬碟與出片相關版本，印出本 repo 流程的建議設定。
# 建議值都是經驗法則推估，不是跑分；有實測的地方會寫出來。
# 執行（在 repo 根目錄）：python tools/hw_check.py --project output/<主題>
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 hw_check.py（MIT License，
# Copyright (c) 2026 mathruffian-dot）：偵測部分沿用；建議改成本 repo 的流程（算繪 worker、審片草稿、
# Edge-TTS／Kokoro、字型瘦身、H3 片段），拿掉本 repo 沒有的 Breeze TTS 與 sub-agent 分批建議。
import argparse
import ctypes
import importlib.metadata
import os
import platform
import shutil
import subprocess
from pathlib import Path
import sys

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

EDGE_TTS_MIN = (7, 3, 1)   # 舊版會被微軟擋（GOTCHAS H-8）
H3_VRAM = 26               # 上游 RTX 5090 實測生成時用掉的 GB（GOTCHAS D-15）


def ram_gb():
    system = platform.system()
    try:
        if system == "Windows":
            class MEMSTAT(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MEMSTAT()
            m.dwLength = ctypes.sizeof(MEMSTAT)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 2**30, m.ullAvailPhys / 2**30
        if system == "Linux":
            info = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0]) * 1024
            return info["MemTotal"] / 2**30, info.get("MemAvailable", 0) / 2**30
        if system == "Darwin":
            total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout)
            return total / 2**30, None
    except Exception:
        pass
    return None, None


def gpus():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    out = subprocess.run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    found = []
    for line in out.stdout.strip().splitlines():
        name, _, mem = line.rpartition(",")
        try:
            found.append((name.strip(), int(mem.strip()) / 1024))
        except ValueError:
            pass
    return found


def version_of(package):
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def workers_advice(total, cores):
    if total is None:
        return "2", "記憶體不明，先保守"
    if total <= 8:
        return "1", "8 GB 以下 HyperFrames 也會自動進低記憶體模式"
    if cores < 4:
        return "2", "CPU 核心少"
    if total < 16:
        return "2", "每個 worker 是一個 Chrome，當掉就再調低"
    return "auto", "預設值"


def tts_advice():
    ver = version_of("edge-tts")
    if not ver:
        return "Edge-TTS 還沒裝：pip install edge-tts（合成在微軟伺服器，本機不吃資源，要網路）"
    nums = tuple(int(x) for x in ver.split(".")[:3] if x.isdigit())
    if nums < EDGE_TTS_MIN:
        return f"Edge-TTS {ver} 太舊會被擋：pip install -U edge-tts（GOTCHAS H-8）"
    return f"Edge-TTS {ver}，可用（本機不吃資源，要網路）；離線備案是 --tts kokoro（GOTCHAS H-1）"


def h3_advice(vram):
    if vram >= H3_VRAM:
        return "顯示記憶體足夠；用 --draft 先看動作，定稿再跑完整步數（GOTCHAS D-15）"
    if vram >= 12:
        return (f"上游實測生成時用掉約 {H3_VRAM} GB，這張卡是否跑得動未實測；"
                "先 h3_runner.py --check，跑 draft 爆記憶體就用退路（只給 prompt.txt 與第一格、改用靜態圖，或不放影片）")
    return "不建議本機生成；ComfyUI 可在別台電腦（--comfy），不然用退路（改用靜態圖或不放影片）"


def main():
    ap = argparse.ArgumentParser(description="看這台電腦的硬體，印出本 repo 流程的建議設定")
    ap.add_argument("--project", default=".", help="影片專案，用來看所在磁碟的剩餘空間")
    a = ap.parse_args()

    cores = os.cpu_count() or 1
    total, avail = ram_gb()
    gpu = gpus()
    free = shutil.disk_usage(Path(a.project).resolve().anchor or "/").free / 2**30
    home_free = shutil.disk_usage(Path.home().anchor or "/").free / 2**30
    vram = max((v for _, v in gpu), default=0)

    print("== 這台電腦")
    print(f"  系統      {platform.system()} {platform.release()}（{platform.machine()}）")
    print(f"  CPU       {cores} 個邏輯核心")
    print("  記憶體    " + (f"共 {total:.1f} GB" + (f"，可用 {avail:.1f} GB" if avail else "") if total else "不明"))
    print("  GPU       " + ("；".join(f"{n}（{v:.0f} GB VRAM）" for n, v in gpu) if gpu else "沒有 NVIDIA GPU（找不到 nvidia-smi）"))
    print(f"  硬碟      專案所在磁碟剩 {free:.0f} GB；使用者資料夾所在磁碟剩 {home_free:.0f} GB")

    print("\n== 建議（推估值）")
    n, why = workers_advice(total, cores)
    print(f"  算繪        npx --yes hyperframes@0.8.181 render --workers {n}（{why}）")
    print("  審片        草稿一律 --quality draft，定稿才用預設品質（tools/review-loop.md）")
    print(f"  旁白        {tts_advice()}")
    print("  字型        " + ("fonttools 已裝，文字定稿後跑 tools/subset_fonts.py（GOTCHAS D-12）" if version_of("fonttools")
                              else "pip install fonttools brotli，每個 worker 要載入的字型才不會是 15 MB 三份（GOTCHAS D-12）"))
    print("  contact sheet  " + ("Pillow 已裝" if version_of("pillow") else "pip install pillow（tools/sheet.py 要用）"))
    print(f"  AI 影片片段  {h3_advice(vram)}")
    if min(free, home_free) < 10:
        print(f"  硬碟        剩不到 10 GB：算繪暫存、草稿、npx 快取與 Chrome（在使用者資料夾）都要空間")

    print("\n  實測參考：4:49 的片，Windows on ARM 筆電 render 約 3 分鐘、12 核心 RTX 5060 Ti 桌機 draft 約 2 分鐘（本 repo）；")
    print("  24 核心／95 GB／RTX 5090，105 秒的片 draft 約 75–80 秒、high 約 85–90 秒，auto 選 3 個 worker（上游）。")


if __name__ == "__main__":
    main()
