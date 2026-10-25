# 把照片裁切、縮放並套成影片的配色，讓網路照片融進版面
# 執行（在 repo 根目錄）：
#   python tools/treat_images.py --project output/<主題> [--bg "#1A1A1A" --fg "#FAF7EE"]
#
# 讀 <專案>/images.json，每張圖一個條目，輸出 assets/images/treated/<name>.jpg：
# {
#   "_colors": {"bg": "#1A1A1A", "fg": "#FAF7EE"},
#   "lunar":   {"src": "assets/images/lunar.jpg", "crop": [x0, y0, x1, y1], "size": [1600, 1000], "mode": "duotone"},
#   "office":  {"src": "assets/images/office.jpg", "size": [1920, 1080], "mode": "keep", "darken": 0.85}
# }
# mode：
#   duotone — 轉灰階後，暗部對到 bg、亮部對到 fg：照片融進配色，強調色留給片中的重點（證據照適用）
#   keep    — 保留原色（氣氛照、照配色生成的圖），可加 darken 壓暗
# bg／fg 用 DESIGN.md 的色票：順序是 --bg/--fg 參數 > images.json 的 _colors。
# 可選欄位：crop（原圖座標）、size（裁成這個尺寸，置中填滿）、contrast（duotone 前的對比，預設 1.15）、darken。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 treat_images.py（MIT License，
# Copyright (c) 2026 mathruffian-dot）：顏色改由 images.json／參數提供（本 repo 沒有 theme.json）、訊息改繁中。
# 需要：pip install pillow
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) != 6:
        raise SystemExit(f"顏色要寫成 #RRGGBB，收到 #{h}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser(description="照片裁切、縮放並套成影片配色")
    ap.add_argument("--project", required=True, help="影片專案資料夾（output/<主題>）")
    ap.add_argument("--bg", help="duotone 暗部顏色（#RRGGBB）")
    ap.add_argument("--fg", help="duotone 亮部顏色（#RRGGBB）")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    spec_path = project / "images.json"
    if not spec_path.exists():
        raise SystemExit(f"找不到 {spec_path}（格式見本檔開頭）")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    colors = spec.get("_colors", {})
    bg, fg = a.bg or colors.get("bg"), a.fg or colors.get("fg")
    out_dir = project / "assets" / "images" / "treated"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, s in spec.items():
        if name.startswith("_") or not isinstance(s, dict) or "src" not in s:
            continue
        im = Image.open(project / s["src"]).convert("RGB")
        if s.get("crop"):
            im = im.crop(tuple(s["crop"]))
        if s.get("size"):
            im = ImageOps.fit(im, tuple(s["size"]), Image.LANCZOS)
        mode = s.get("mode", "duotone")
        if mode == "duotone":
            if not (bg and fg):
                raise SystemExit(f"{name} 是 duotone，要先給顏色：images.json 的 _colors 或 --bg/--fg")
            g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
            g = ImageEnhance.Contrast(g).enhance(s.get("contrast", 1.15))
            im = ImageOps.colorize(g, black=hex_rgb(bg), white=hex_rgb(fg))
        elif mode != "keep":
            raise SystemExit(f"{name} 的 mode 只能是 duotone 或 keep，收到 {mode}")
        if s.get("darken"):
            im = ImageEnhance.Brightness(im).enhance(s["darken"])
        dest = out_dir / f"{name}.jpg"
        im.save(dest, quality=88)
        print(f"{name}：{im.size[0]}x{im.size[1]}（{mode}）→ {dest.relative_to(project).as_posix()}")


if __name__ == "__main__":
    main()
