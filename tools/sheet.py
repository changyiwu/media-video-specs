# 審片用的 contact sheet：一個時間點一格、每張 4×2，格子標時間。流程見 tools/review-loop.md、GOTCHAS D-10
# 格子預設 360 px 寬，也就是手機動態上的實際寬度：格子裡讀得清楚，手機上就讀得清楚。
# 執行（在 repo 根目錄）：
#   python tools/sheet.py --project output/<主題>                          # 草稿 renders/draft.mp4 × review_times.py 的時間點
#   python tools/sheet.py --project output/<主題> --from 3 --to 5 --every 0.2 --name scrub     # 掃一段轉場
#   python tools/sheet.py --project output/<主題> --at 3.7,3.75,3.8 --name exact               # 看特定時刻
#   python tools/sheet.py --video output/<主題>/assets/videos/gen/v1/clip.mp4 --from 0 --to 5 --every 0.7 --out <資料夾>
#   python tools/sheet.py --images a.png b.png --labels 0.3,1.5 --out <資料夾>                # 拼現成截圖
# 輸出：--project 時預設放 <專案>/.hyperframes/review/（不進 git），一併寫 <name>-table.txt 對照每格是哪一句旁白。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 skills/review-loop/scripts/sheet.py（MIT License，
# Copyright (c) 2026 mathruffian-dot；該資料夾改編自 whaleyxbt/claude-motion，MIT License，Copyright (c) 2026 whaleyxbt）：
# 拿掉本 repo 沒有的 timeline.js、加上 --project 接 review_times.py、輸出對照表。
# 需要：ffmpeg、ffprobe、pillow
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

COLS, ROWS = 4, 2
GAP = 8
LABEL_H = 26


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(video)],
                         check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def grab(video, t, dest, end):
    # 時間點可能落在最後一格之後，那就看最後一格
    t = max(0.0, min(t, end - 0.05))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                    "-frames:v", "1", str(dest)], check=True)
    if not Path(dest).exists():
        raise SystemExit(f"ffmpeg 在 {t:.3f}s 沒有輸出畫面")
    return dest


def label_font():
    for name in ("msjh.ttc", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, 16)
        except OSError:
            continue
    return ImageFont.load_default()


def build_sheets(tiles, out_dir, width, stem):
    out_dir.mkdir(parents=True, exist_ok=True)
    font = label_font()
    per = COLS * ROWS
    written = []
    for n in range(0, len(tiles), per):
        batch = tiles[n:n + per]
        with Image.open(batch[0][1]) as first:
            h = round(first.height * width / first.width)
        cell_h = h + LABEL_H
        sheet = Image.new("RGB", (COLS * width + (COLS + 1) * GAP,
                                  ROWS * cell_h + (ROWS + 1) * GAP), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for i, (label, img_path) in enumerate(batch):
            x = GAP + (i % COLS) * (width + GAP)
            y = GAP + (i // COLS) * (cell_h + GAP)
            img = Image.open(img_path).convert("RGB").resize((width, h), Image.LANCZOS)
            draw.text((x + 4, y + 4), label, fill=(240, 240, 240), font=font)
            sheet.paste(img, (x, y + LABEL_H))
        dest = out_dir / f"{stem}-{n // per + 1}.png"
        sheet.save(dest)
        written.append(dest)
    return written


def moments_of(a, project):
    """[(格子標籤, 秒數, 對照表文字)]"""
    if a.at:
        return [(f"{float(t):.2f}s", float(t), "") for t in a.at.split(",")]
    if a.t0 is not None and a.t1 is not None:
        steps = int(round((a.t1 - a.t0) / a.every)) + 1
        return [(f"{a.t0 + i * a.every:.2f}s", a.t0 + i * a.every, "") for i in range(steps)]
    if project:
        from review_times import rows
        return [(f"p{n:02d} {t:.2f}s", t, text if text is not None else "（落定）") for t, n, text in rows(project)]
    raise SystemExit("--video 要搭配 --at 或 --from／--to；用 --project 才會自動算時間點")


def main():
    p = argparse.ArgumentParser(description="審片用的 contact sheet：一個時間點一格，每張 4×2")
    p.add_argument("--project", help="影片專案；影片預設 renders/draft.mp4，時間點預設 review_times.py")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--video", help="要抽格的影片")
    src.add_argument("--images", nargs="+", help="現成的截圖，依序")
    p.add_argument("--at", help="逗號分隔的秒數")
    p.add_argument("--from", dest="t0", type=float)
    p.add_argument("--to", dest="t1", type=float)
    p.add_argument("--every", type=float, default=0.2)
    p.add_argument("--labels", help="--images 的逗號分隔標籤")
    p.add_argument("--width", type=int, default=360, help="格子寬度 px（預設 360，手機寬度）")
    p.add_argument("--out", help="輸出資料夾（預設 <專案>/.hyperframes/review）")
    p.add_argument("--name", default="draft", help="輸出檔名開頭（預設 draft）")
    a = p.parse_args()

    project = Path(a.project).resolve() if a.project else None
    if not a.out and not project:
        raise SystemExit("沒有 --project 時要給 --out")
    out = Path(a.out) if a.out else project / ".hyperframes" / "review"

    if a.images:
        labels = a.labels.split(",") if a.labels else [Path(i).stem for i in a.images]
        if len(labels) != len(a.images):
            raise SystemExit("--labels 的數量要和 --images 相同")
        for path in build_sheets(list(zip(labels, a.images)), out, a.width, a.name):
            print(path)
        return

    video = Path(a.video) if a.video else (project / "renders" / "draft.mp4" if project else None)
    if not video or not video.exists():
        raise SystemExit(f"找不到影片 {video}：先 npx --yes hyperframes@0.8.181 render --quality draft -o renders/draft.mp4")
    moments = moments_of(a, project)
    end = duration(video)
    with tempfile.TemporaryDirectory(prefix="sheet-") as tmp:
        tiles = [(lbl, grab(video, t, Path(tmp) / f"f{i:03d}.png", end)) for i, (lbl, t, _) in enumerate(moments)]
        sheets = build_sheets(tiles, out, a.width, a.name)
    per = COLS * ROWS
    table = out / f"{a.name}-table.txt"
    table.write_text("".join(f"{a.name}-{i // per + 1} 第 {i % per + 1} 格\t{lbl}\t{text}\n"
                             for i, (lbl, _, text) in enumerate(moments)), encoding="utf-8")
    for path in [*sheets, table]:
        print(path)


if __name__ == "__main__":
    main()
