# 算出審片要截圖的時間點：每頁的旁白子句結束前 0.15 秒（念到這句時，畫面該有的東西應該已經落定），
# 加上每頁的落定時刻（頁尾前 1.6 秒，動畫都跑完了）。流程見 tools/review-loop.md、GOTCHAS D-10
# 執行（在 repo 根目錄）：
#   python tools/review_times.py --project output/<主題>           # 逗號分隔的秒數
#   python tools/review_times.py --project output/<主題> --table   # 逐列：秒數、頁、子句
#   python tools/review_times.py --project output/<主題> --pages   # 只給每頁落定時刻，給 snapshot --at 用
#
# 時間的來源：每頁起點讀 index.html 標籤上的 data-start／data-duration（D-3 的唯一真相來源）；
# 子句結束時間用 generate_narration.py 的 SCRIPT 依標點切子句、ffmpeg silencedetect 找 page-NN.mp3 的停頓來對
# （和 fix_voice.py 同一套），不需要網路，子句數和停頓數對不上時依字數比例估，差一點無妨：截的是「這句快念完」。
# 沒有 generate_narration.py 或旁白 mp3 的專案（01 範本）只給每頁落定時刻。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 review_times.py（MIT License，
# Copyright (c) 2026 mathruffian-dot）：上游讀 audio_meta.json 的子句時間，本 repo 沒有這個檔，
# 改用逐頁 mp3 與 SCRIPT 現算；加上每頁落定時刻、太近的時間點合併、--pages。
# 需要：ffmpeg、ffprobe
import argparse
import importlib.util
from html.parser import HTMLParser
from pathlib import Path

from fix_voice import clauses, speech_spans, time_clauses

SETTLE = 1.6   # 頁尾前幾秒算落定：分階動畫守衛保證動畫在頁尾前 1.5 秒跑完（C-7）


class Timeline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pages = []   # (page, start, dur)
        self.audios = {}  # src -> start

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-page" in a:
            self.pages.append((int(a["data-page"]), float(a["data-start"]), float(a["data-duration"])))
        if tag == "audio" and a.get("src") and a.get("data-start"):
            self.audios[a["src"]] = float(a["data-start"])


def load_script(root):
    gn = root / "generate_narration.py"
    if not gn.exists():
        return {}
    spec = importlib.util.spec_from_file_location("generate_narration", gn)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.SCRIPT)


def rows(project, before=0.15, gap=0.8):
    """[(秒數, 頁, 子句文字或 None)]；None 是該頁落定時刻。時間上太近的子句略過，落定時刻一定留著。"""
    root = Path(project).resolve()
    html = root / "index.html"
    if not html.exists():
        raise SystemExit(f"{root} 沒有 index.html")
    tl = Timeline()
    tl.feed(html.read_text(encoding="utf-8"))
    if not tl.pages:
        raise SystemExit(f"{html} 找不到 data-page 的頁面")
    script = load_script(root)
    pages = sorted(tl.pages, key=lambda p: p[1])
    out = []
    for i, (n, start, dur) in enumerate(pages):
        # 交叉淡化的頁會和下一頁重疊（C-1），落定時刻要算在下一頁開始之前
        end = min(start + dur, pages[i + 1][1]) if i + 1 < len(pages) else start + dur
        settle = round(max(start, end - SETTLE), 2)
        src = f"assets/narration/page-{n:02d}.mp3"
        mp3 = root / src
        if n in script and mp3.exists():
            t0 = tl.audios.get(src, start)
            spans, _ = speech_spans(mp3)
            for text, _, e in time_clauses(clauses(script[n]), spans):
                t = round(max(t0, t0 + e - before), 2)
                if t < settle - gap:
                    out.append((t, n, text))
        out.append((settle, n, None))
    kept = []
    for row in out:
        if kept and row[0] - kept[-1][0] < gap:
            if row[2] is not None:
                continue
            if kept[-1][2] is not None:
                kept.pop()
        kept.append(row)
    return kept


def main():
    ap = argparse.ArgumentParser(description="算出審片要截圖的時間點（旁白子句結束前、每頁落定時刻）")
    ap.add_argument("--project", default=".")
    ap.add_argument("--before", type=float, default=0.15, help="子句結束前幾秒（預設 0.15）")
    ap.add_argument("--gap", type=float, default=0.8, help="兩張截圖至少隔幾秒（預設 0.8）")
    ap.add_argument("--table", action="store_true", help="逐列印出秒數、頁、子句")
    ap.add_argument("--pages", action="store_true", help="只給每頁落定時刻；第一個時間點重複一次（D-10：第一張可能空白）")
    a = ap.parse_args()
    data = rows(a.project, a.before, a.gap)
    if a.pages:
        ts = [t for t, _, text in data if text is None]
        print(",".join(str(t) for t in [ts[0], *ts]))
    elif a.table:
        for t, n, text in data:
            print(f"{t:8.2f}  p{n:02d}  {text if text is not None else '（落定）'}")
    else:
        print(",".join(str(t) for t, _, _ in data))


if __name__ == "__main__":
    main()
