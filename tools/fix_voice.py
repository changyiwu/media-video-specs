# 片做完才發現某頁旁白有字念錯：整頁重念幾個候選、用耳朵挑一個，再把它等比伸縮回原本的長度換進去，
# 頁長與動畫時間都不必重排（GOTCHAS H-5）
# 執行（在 repo 根目錄；output/<主題> 是從 02／03 範本 fork 出來、有 generate_narration.py 的專案）：
#   1. 產生候選（在專案資料夾裡）：
#        python generate_narration.py --page 3 --take A --rate=-5%
#        python generate_narration.py --page 3 --take B --text "換了拼法的整句"
#   2. 試聽：把念錯那個詞所在的子句（從 0 起算，依標點切）從每個候選剪出來，串成一個檔，用耳朵選
#        python tools/fix_voice.py --project output/<主題> audition --page 3 --clauses 1 2
#   3. 套用：選定的候選整句等比伸縮回原本的語音長度、音量對齊原句，覆蓋 page-03.mp3（原檔先備份）
#        python tools/fix_voice.py --project output/<主題> apply --page 3 --take B
#   還原：python tools/fix_voice.py --project output/<主題> restore --page 3
#
# 為什麼整句伸縮、不切子句：重念的停頓位置和原句不同，照停頓切子句再拼，切點會落在字中間，結果漏字或重複。
# 為什麼要人耳選：ASR 抓得到念成別的詞，抓不到聲調錯。
#
# 本 repo 的動畫照 WordBoundary 逐詞秒數對齊（H-2）。apply 會用 Edge-TTS 重抓原句與候選的逐詞時間，
# 換算成伸縮後的秒數逐詞比對，差超過 0.2 秒的詞列出來：那幾個時間點的 tween 要照 H-3 的 T(n, t) 修。
# 離線或用 Kokoro 時加 --no-words 略過。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 fix_voice.py 與 voice_meta.py（MIT License，
# Copyright (c) 2026 mathruffian-dot）：改成本 repo 的逐頁 mp3 與 generate_narration.py 的 SCRIPT、
# 試聽改用 filter_complex 串接（concat demuxer 讀不了中文路徑，GOTCHAS E-5）、拿掉逐子句字幕重算
# （本 repo 每頁一條靜態字幕）、加上逐詞時間比對。
# 需要：ffmpeg、ffprobe；比對逐詞時間需要 edge-tts 與網路
import argparse
import asyncio
import difflib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

NOISE, MIN_GAP = "-38dB", 0.10       # 靜音判定：低於 -38 dB 且持續 0.1 秒以上
SPLIT = r"[，。？！；、：,.?!;:]"     # 子句切點
DRIFT = 0.2                          # 逐詞時間差超過這個秒數就列出來


# ---- 音訊量測 ----

def run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def ff(*args):
    r = run(["ffmpeg", "-v", "error", "-y", *args])
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失敗：\n{r.stderr[-1500:]}")


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", str(path)]).stdout.strip())


def speech_spans(path):
    """有聲音的區段 [(起, 訖), …] 與總長，用 ffmpeg silencedetect 找停頓。"""
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
               "-af", f"silencedetect=noise={NOISE}:d={MIN_GAP}", "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    total = duration(path)
    if len(ends) < len(starts):
        ends.append(total)
    spans, cur = [], 0.0
    for s, e in zip(starts, ends):
        if s > cur + 0.02:
            spans.append((cur, s))
        cur = e
    if cur < total - 0.02:
        spans.append((cur, total))
    if not spans:
        raise SystemExit(f"{path} 裡找不到語音")
    return spans, total


def lufs(path):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"]).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


# ---- 子句 ----

def clauses(text):
    parts, buf = [], ""
    for ch in text:
        if re.match(SPLIT, ch):
            if buf.strip():
                parts.append(buf.strip() + (ch if ch in "？?" else ""))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def time_clauses(parts, spans):
    """子句數和語音區段數相同就一對一；否則依字數比例攤在語音時間上，邊界再吸附到最近的停頓。"""
    if len(parts) == len(spans):
        return [(p, s, e) for p, (s, e) in zip(parts, spans)]
    total_speech = sum(e - s for s, e in spans)
    weights = [len(re.sub(r"\s", "", p)) for p in parts]
    wsum = sum(weights)

    def at(frac):
        target = frac * total_speech
        for s, e in spans:
            if target <= e - s:
                return s + target
            target -= e - s
        return spans[-1][1]

    gaps = [(spans[i][1], spans[i + 1][0]) for i in range(len(spans) - 1)]
    out, acc, start = [], 0, spans[0][0]
    for k, (p, w) in enumerate(zip(parts, weights)):
        acc += w
        end = at(acc / wsum)
        near = min(gaps, key=lambda g: abs((g[0] + g[1]) / 2 - end), default=None)
        if near and abs((near[0] + near[1]) / 2 - end) < 0.35 and k < len(parts) - 1:
            end, nxt = near[0], near[1]
        else:
            nxt = end
        out.append((p, start, end))
        start = nxt
    return out


# ---- 專案 ----

class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        gn = self.root / "generate_narration.py"
        if not gn.exists():
            raise SystemExit(f"{self.root} 沒有 generate_narration.py（要從 02／03 範本 fork 的專案）")
        spec = importlib.util.spec_from_file_location("generate_narration", gn)
        self.gn = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gn)
        self.script = dict(self.gn.SCRIPT)
        self.narr = self.root / "assets" / "narration"
        self.fix = self.narr / "fix"
        self.work = self.fix / "work"

    def page(self, n):
        if n not in self.script:
            raise SystemExit(f"SCRIPT 沒有第 {n} 頁")
        return self.narr / f"page-{n:02d}.mp3"

    def backup(self, n):
        return self.fix / f"page-{n:02d}.before-fix.mp3"

    def original(self, n):
        """原句：套用過就是備份檔，否則是目前的 page-NN.mp3。"""
        b = self.backup(n)
        return b if b.exists() else self.page(n)

    def takes(self, n):
        return sorted((self.fix / "cand").glob(f"page-{n:02d}_*.mp3"))

    def take_meta(self, mp3):
        j = mp3.with_suffix(".json")
        return json.loads(j.read_text(encoding="utf-8")) if j.exists() else None

    def spoken(self, n):
        """原句實際送進 TTS 的文字（套過讀音替換表）。"""
        return self.gn.speakable(self.script[n], self.gn.load_lexicon())


# ---- 試聽 ----

def label(text, voice, out):
    """候選代號的語音標籤（Edge-TTS），失敗就用嗶聲。"""
    try:
        import edge_tts
        mp3 = out.with_suffix(".mp3")
        asyncio.run(edge_tts.Communicate(text, voice, rate="+10%").save(str(mp3)))
        ff("-i", str(mp3), "-ar", "24000", "-ac", "1", str(out))
    except Exception:
        ff("-f", "lavfi", "-i", "sine=f=880:d=0.25", "-ar", "24000", "-ac", "1", str(out))
    return out


def audition(p, n, clause_ids):
    takes = p.takes(n)
    if not takes:
        raise SystemExit(f"沒有候選：先在專案資料夾跑 python generate_narration.py --page {n} --take A（B、C…）")
    parts = clauses(p.script[n])
    bad = [c for c in clause_ids if not 0 <= c < len(parts)]
    if bad:
        listing = "\n".join(f"  {k}：{t}" for k, t in enumerate(parts))
        raise SystemExit(f"子句編號 {bad} 超出範圍，第 {n} 頁的子句：\n{listing}")
    p.work.mkdir(parents=True, exist_ok=True)
    # 標籤用和旁白不同的聲音，聽得出哪句是標籤
    lab_voice = "zh-TW-HsiaoChenNeural" if "YunJhe" in p.gn.VOICE else "zh-TW-YunJheNeural"
    sources = [("原本", p.original(n))] + [(t.stem.split("_", 1)[1], t) for t in takes]
    seq = []
    gap = p.work / "gap.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.6", str(gap))
    print(f"第 {n} 頁，子句 {clause_ids}：「{''.join(parts[min(clause_ids):max(clause_ids) + 1])}」")
    for tag, src in sources:
        cl = time_clauses(parts, speech_spans(src)[0])
        a = max(0.0, cl[min(clause_ids)][1] - 0.05)
        b = cl[max(clause_ids)][2] + 0.1
        seg = p.work / f"seg_{tag}.wav"
        ff("-i", str(src), "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "24000", "-ac", "1", str(seg))
        seq += [label(tag, lab_voice, p.work / f"label_{tag}.wav"), seg, gap]
        print(f"  {tag}：{a:.2f}–{b:.2f}s（{src.name}）")
    # 用 filter_complex 串，不用 concat demuxer 的 list.txt：後者讀不了中文路徑（GOTCHAS E-5）
    args = []
    for f in seq:
        args += ["-i", str(f)]
    chain = "".join(f"[{k}:a]" for k in range(len(seq))) + f"concat=n={len(seq)}:v=0:a=1[a]"
    out = p.fix / f"audition_page-{n:02d}.mp3"
    ff(*args, "-filter_complex", chain, "-map", "[a]", "-c:a", "libmp3lame", "-q:a", "2", str(out))
    print(f"→ {out}")
    print(f"聽完選一個：python tools/fix_voice.py --project \"{p.root}\" apply --page {n} --take <代號>")


# ---- 套用 ----

async def word_times(text, voice, rate, pitch):
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    return [(ch["text"], ch["offset"] / 1e7) async for ch in c.stream() if ch["type"] == "WordBoundary"]


def check_words(p, n, meta, tempo, a0, s1):
    """原句與候選的逐詞時間比對：候選詞秒數換算成伸縮後的位置，和原句同一個詞相比。"""
    orig = asyncio.run(word_times(p.spoken(n), p.gn.VOICE, p.gn.RATE, p.gn.PITCH))
    cand = asyncio.run(word_times(meta["text"], meta["voice"], meta["rate"], meta["pitch"]))
    if not orig or not cand:
        print("! 拿不到逐詞時間（串流中斷？H-2），這步略過，請用 snapshot 目視確認")
        return
    sm = difflib.SequenceMatcher(a=[w for w, _ in orig], b=[w for w, _ in cand], autojunk=False)
    drift = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            w, t0 = orig[blk.a + k]
            t1 = (cand[blk.b + k][1] - s1) / tempo + a0
            drift.append((abs(t1 - t0), w, t0, t1))
    if not drift:
        print("! 原句和候選對不到任何相同的詞，略過比對")
        return
    worst = max(drift)
    print(f"逐詞比對：{len(drift)}/{len(orig)} 個詞對得上，最大偏差 {worst[0]:.2f}s（「{worst[1]}」）")
    far = [d for d in drift if d[0] > DRIFT]
    for d, w, t0, t1 in far:
        print(f"  「{w}」 原 {t0:.2f}s → 新 {t1:.2f}s（差 {t1 - t0:+.2f}s）")
    if far:
        print(f"  ↑ 偏差超過 {DRIFT}s：這頁對到這些詞的 tween 照 GOTCHAS H-3 的 T(n, t) 修")
    else:
        print(f"  都在 {DRIFT}s 內，動畫不用動")


def apply(p, n, tag, words):
    dest = p.page(n)
    cand = p.fix / "cand" / f"page-{n:02d}_{tag}.mp3"
    if not cand.exists():
        raise SystemExit(f"找不到候選 {cand}")
    backup = p.backup(n)
    if not backup.exists():
        shutil.copy2(dest, backup)  # 只在第一次套用時備份，之後都以這份原句為準
    p.work.mkdir(parents=True, exist_ok=True)

    spans0, total0 = speech_spans(backup)
    a0, b0 = spans0[0][0], spans0[-1][1]
    spans1, _ = speech_spans(cand)
    s1, e1 = spans1[0][0], spans1[-1][1]
    tempo = (e1 - s1) / (b0 - a0)
    if not 0.85 <= tempo <= 1.15:
        print(f"! 候選語音 {e1 - s1:.2f}s、原句 {b0 - a0:.2f}s，要伸縮 {tempo:.3f} 倍，差太多聽得出來，建議換一個候選")
    elif not 0.95 <= tempo <= 1.05:
        print(f"注意：伸縮 {tempo:.3f} 倍，超過 ±5% 可能聽得出來，套用後實際聽一次")

    # 候選只留語音段，等比伸縮成原句的語音長度，前面補上原句開頭的靜音，總長對齊原檔。
    # atempo／adelay 之後的時間戳不是從 0 起算，最後的 atrim 前要用取樣數重建（asetpts=N/SR/TB），
    # 不然會少裁約 0.2 秒、整頁旁白變短
    stretched = p.work / f"page-{n:02d}_{tag}.stretched.wav"
    ff("-i", str(cand), "-af",
       f"atrim=start={s1:.3f}:end={e1:.3f},asetpts=PTS-STARTPTS,atempo={tempo:.5f},"
       f"adelay={a0 * 1000:.0f}:all=1,asetpts=N/SR/TB,apad,atrim=0:{total0:.3f}",
       "-ar", "24000", "-ac", "1", str(stretched))
    gain = lufs(backup) - lufs(stretched)
    ff("-i", str(stretched), "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
       "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "2", str(dest))
    print(f"第 {n} 頁換成候選 {tag}：語音 {e1 - s1:.2f}s → {b0 - a0:.2f}s（伸縮 {tempo:.3f} 倍），"
          f"音量 {gain:+.1f} dB，總長 {total0:.2f}s → {duration(dest):.2f}s；原檔備份在 {backup.name}")

    meta = p.take_meta(cand)
    if not words:
        print("已略過逐詞比對（--no-words）")
    elif not meta:
        print(f"! 候選沒有 {cand.with_suffix('.json').name}（不是用 generate_narration.py --take 產生的），略過逐詞比對")
    elif meta.get("engine") != "edge":
        print("Kokoro 候選沒有 WordBoundary，略過逐詞比對；用 snapshot 目視確認")
    else:
        check_words(p, n, meta, tempo, a0, s1)
    print("下一步：python generate_narration.py --audit → npx --yes hyperframes@0.8.181 check → "
          "snapshot 目視（D-10）→ render → python tools/loudness.py <成片> --apply（E-6）")


def restore(p, n):
    backup = p.backup(n)
    if not backup.exists():
        raise SystemExit(f"第 {n} 頁沒有套用過，沒有備份可還原")
    shutil.copy2(backup, p.page(n))
    backup.unlink()
    print(f"第 {n} 頁已還原成原句")


def main():
    ap = argparse.ArgumentParser(description="修正某頁旁白念錯的字，不動頁長與動畫")
    ap.add_argument("--project", required=True, help="影片專案資料夾（output/<主題>）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("audition", help="把各候選的關鍵子句串成一個試聽檔")
    a1.add_argument("--page", type=int, required=True)
    a1.add_argument("--clauses", type=int, nargs="+", required=True, help="念錯的詞所在的子句編號（從 0 起算）")
    a2 = sub.add_parser("apply", help="套用選定的候選")
    a2.add_argument("--page", type=int, required=True)
    a2.add_argument("--take", required=True, help="候選代號（A、B…）")
    a2.add_argument("--no-words", action="store_true", help="略過逐詞時間比對（離線時用）")
    a3 = sub.add_parser("restore", help="還原成原句")
    a3.add_argument("--page", type=int, required=True)
    a = ap.parse_args()
    p = Project(a.project)
    if a.cmd == "audition":
        audition(p, a.page, a.clauses)
    elif a.cmd == "apply":
        apply(p, a.page, a.take, not a.no_words)
    else:
        restore(p, a.page)


if __name__ == "__main__":
    main()
