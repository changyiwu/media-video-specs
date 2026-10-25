# 量測成片響度，並正規化到 −15 LUFS（與 media-short-film 統一的目標；YouTube 的播放基準是 −14）、真峰值 ≤ −1 dBTP
# 執行（在 repo 根目錄）：
#   python tools/loudness.py output/<主題>/final.mp4            只量測
#   python tools/loudness.py output/<主題>/final.mp4 --apply    正規化後覆蓋原檔（-o 另存）
#
# 規範在 GOTCHAS E-6：每支片 render 完都要跑 --apply，再交片。HyperFrames 的 `normalize-audio`
# 只調單一音軌的 data-volume（旁白對 BGM 的相對音量），管不到整支片混音後的響度，所以要在成片上做。
#
# 做法（移植自 media-short-film 的 make_film.py cut）：音軌先套固定增益，再用 4 倍超取樣的限幅器壓峰值
# （近似真峰值限幅），**實際編成交片用的 AAC 之後才量**響度與真峰值——AAC 編碼本身會把真峰值推高，
# 只量編碼前的音檔會漏掉。響度差超過 ±0.5 LU 就調增益、真峰值超標就壓低限幅門檻，最多 8 輪。
# 最後只把新的音軌換進原片，視訊串流直接複製、不重新編碼。已經在目標內就不動。
import argparse
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

TARGET_I, TP_MAX, TOLERANCE = -15.0, -1.0, 0.5
SR, ROUNDS = 48000, 8


def ffmpeg(args):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失敗：\n{r.stderr[-2000:]}")
    return r.stderr


def measure(path):
    """整合響度（LUFS）與真峰值（dBTP），量的是檔案裡實際的音軌"""
    err = ffmpeg(["-i", str(path), "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"])
    summary = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", summary)
    tp = re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", summary)
    if not i:
        raise SystemExit(f"量不到響度（{path} 有音軌嗎？）")
    return float(i.group(1)), (float(tp.group(1)) if tp and tp.group(1) != "-inf" else -99.0)


def ok(i, tp):
    return abs(i - TARGET_I) <= TOLERANCE and tp <= TP_MAX


def show(label, i, tp):
    print(f"{label}：整合響度 {i:6.1f} LUFS　真峰值 {tp:5.1f} dBTP")


def normalize(src, dest):
    i0, _ = measure(src)
    gain, lim = TARGET_I - i0, 10 ** ((TP_MAX - 0.3) / 20)   # 限幅門檻先設在目標真峰值下方 0.3 dB
    with tempfile.TemporaryDirectory() as tmp:
        raw, enc = Path(tmp) / "raw.wav", Path(tmp) / "audio.m4a"
        ffmpeg(["-i", str(src), "-map", "0:a:0", "-c:a", "pcm_f32le", "-ar", str(SR), str(raw)])
        for n in range(1, ROUNDS + 1):
            # alimiter 一定要 level=false：預設會把輸出自動拉到 0 dBFS
            ffmpeg(["-i", str(raw), "-af",
                    f"volume={gain:.2f}dB,aresample={SR * 4},"
                    f"alimiter=limit={lim:.3f}:level=false:attack=2:release=80,aresample={SR}",
                    "-c:a", "aac", "-b:a", "192k", str(enc)])
            i, tp = measure(enc)
            print(f"  第 {n} 輪：增益 {gain:+.2f} dB、限幅 {20 * math.log10(lim):.1f} dBFS → {i:.1f} LUFS、真峰值 {tp:.1f} dBTP")
            if ok(i, tp):
                break
            if tp > TP_MAX:
                lim = max(0.25, lim * 10 ** ((TP_MAX - 0.3 - tp) / 20))
            if abs(i - TARGET_I) > TOLERANCE:
                gain += TARGET_I - i
        else:
            print(f"! {ROUNDS} 輪還沒同時達標：通常是某處爆音或動態太大，聽一下再決定要不要交片")
        part = dest.with_name(dest.stem + ".loudness-tmp" + dest.suffix)
        ffmpeg(["-i", str(src), "-i", str(enc), "-map", "0:v?", "-map", "1:a:0", "-c", "copy",
                "-movflags", "+faststart", str(part)])
        os.replace(part, dest)


def main():
    ap = argparse.ArgumentParser(description="成片響度量測與正規化（−15 LUFS／真峰值 ≤ −1 dBTP）")
    ap.add_argument("video", help="成片（通常是 output/<主題>/final.mp4）")
    ap.add_argument("--apply", action="store_true", help="正規化（預設覆蓋原檔）")
    ap.add_argument("-o", "--output", help="正規化結果另存到這裡，不覆蓋原檔")
    a = ap.parse_args()
    src = Path(a.video).resolve()
    if not src.exists():
        raise SystemExit(f"找不到 {src}")

    i, tp = measure(src)
    show("目前", i, tp)
    good = ok(i, tp)
    print(f"目標：{TARGET_I:g} LUFS ±{TOLERANCE:g}、真峰值 ≤ {TP_MAX:g} dBTP → {'符合' if good else '不符合'}")
    if not a.apply:
        if not good:
            print(f"要正規化：python tools/loudness.py \"{a.video}\" --apply")
        return
    if good:
        print("已在目標範圍內，不改檔")
        return
    dest = Path(a.output).resolve() if a.output else src
    normalize(src, dest)
    i, tp = measure(dest)
    show("處理後", i, tp)
    print(f"→ {dest}")


if __name__ == "__main__":
    main()
