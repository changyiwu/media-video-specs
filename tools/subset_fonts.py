# 把專案的字型瘦身成「片中實際用到的字」，並把 @font-face 改指向瘦身版
# 執行（在 repo 根目錄）：
#   python tools/subset_fonts.py --project output/<主題>             瘦身並改指向
#   python tools/subset_fonts.py --project output/<主題> --restore   改回完整字型
#
# 源石黑體三個字重各約 15 MB，一支片通常只用到幾百個字，瘦身後每個字重只剩一兩百 KB。
# 掃描 index.html（與 compositions/ 底下的 html）的全文——標記與 JS 字串都算，JS 設定的文字也涵蓋——
# 保留這些字加上 ASCII 與常用中文標點，在原字型旁寫出 <字型>.subset.woff2（沒裝 brotli 時維持 .otf），
# 再把每個 @font-face 的 url() 改指向瘦身版。
#
# 要放在最後：所有文字（旁白字幕、圖說、照片來源）都改完、`check` 之前才跑；之後改過任何字就重跑
# （它每次都從完整字型重切，不會越切越少）。只能在 output/<主題>/ 跑：在 examples/ 跑會把版控中的
# 範本改成指向不在 git 裡的字檔（GOTCHAS D-12）。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 subset_fonts.py（MIT License，
# Copyright (c) 2026 mathruffian-dot）：預設字型改成源石黑體三個字重、加上 examples/ 守衛、訊息改繁中。
# 需要：pip install fonttools（選用：pip install brotli，輸出 woff2）
import argparse
import re
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
FONTS = ["GenSekiGothic2TW-H.otf", "GenSekiGothic2TW-B.otf", "GenSekiGothic2TW-M.otf"]
# 只在執行期才產生、原始碼裡找不到的字，靠這張表兜底
EXTRA = ("".join(chr(c) for c in range(0x20, 0x7F))
         + "，。、？！：；「」『』（）《》〈〉—…⋯·・～％＋－×÷＝≈≠≤≥→←↑↓①②③④⑤⑥⑦⑧⑨⑩²³°μ✓✗★")


FORMATS = {"woff2": "woff2", "otf": "opentype", "ttf": "truetype"}


def set_format(text):
    """url() 換了副檔名，緊接在後的 format() 也要跟著換（woff2 標成 opentype 是錯的宣告）。"""
    return re.sub(r"(url\(['\"]?assets/fonts/[\w.-]+\.(woff2|otf|ttf)['\"]?\)\s*format\(['\"])[\w-]+(['\"]\))",
                  lambda m: m.group(1) + FORMATS[m.group(2)] + m.group(3), text)


def compositions(project):
    files = sorted((project / "compositions").glob("**/*.html")) + [project / "index.html"]
    return [f for f in files if f.exists()]


def main():
    ap = argparse.ArgumentParser(description="把字型瘦身成片中用到的字")
    ap.add_argument("--project", required=True, help="影片專案資料夾（output/<主題>）")
    ap.add_argument("--fonts", nargs="+", default=FONTS, help="assets/fonts/ 底下要瘦身的字檔")
    ap.add_argument("--restore", action="store_true", help="把 url() 改回完整字型")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    if REPO / "examples" in (project, *project.parents):
        raise SystemExit("不要在 examples/ 底下跑：範本在版控裡，字檔不在。先 fork 到 output/<主題>/（GOTCHAS D-12）")
    fonts_dir = project / "assets" / "fonts"
    files = compositions(project)
    if not files:
        raise SystemExit(f"{project} 底下找不到 index.html")

    if a.restore:
        def full_name(stem):
            for ext in (".otf", ".ttf"):
                if (fonts_dir / f"{stem}{ext}").exists():
                    return f"{stem}{ext}"
            return f"{stem}.otf"
        for f in files:
            t = f.read_text(encoding="utf-8")
            t2 = re.sub(r"assets/fonts/([\w.-]+?)\.subset\.(?:woff2|ttf|otf)",
                        lambda m: f"assets/fonts/{full_name(m.group(1))}", t)
            t2 = set_format(t2)
            if t2 != t:
                f.write_text(t2, encoding="utf-8")
                print("改回完整字型：", f.relative_to(project).as_posix())
        return

    from fontTools import subset
    try:
        import brotli  # noqa: F401
        flavor = "woff2"
    except ImportError:
        flavor = None  # 沒有 brotli 就維持原本的格式（CFF 的 .otf 仍是 .otf）

    chars = set(EXTRA)
    for f in files:
        chars.update(f.read_text(encoding="utf-8"))
    chars = {c for c in chars if c.isprintable()}
    print(f"{len(files)} 個 composition 共用到 {len(chars)} 個不同的字")

    renames = {}
    for name in a.fonts:
        src = fonts_dir / name
        if not src.exists():
            print("略過（找不到）：", name)
            continue
        out = fonts_dir / f"{src.stem}.subset.{'woff2' if flavor else src.suffix.lstrip('.')}"
        opts = subset.Options()
        opts.flavor = flavor
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        font = subset.load_font(str(src), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)))
        sub.subset(font)
        subset.save_font(font, str(out), opts)
        print(f"{name}：{src.stat().st_size / 1e6:.1f} MB → {out.name} {out.stat().st_size / 1e3:.0f} KB")
        renames[name] = out.name

    for f in files:
        t = f.read_text(encoding="utf-8")
        t2 = t
        for full, small in renames.items():
            stem = Path(full).stem
            t2 = re.sub(rf"assets/fonts/{re.escape(stem)}(?:\.subset\.(?:woff2|ttf|otf)|\.(?:ttf|otf))",
                        f"assets/fonts/{small}", t2)
        t2 = set_format(t2)
        if t2 != t:
            f.write_text(t2, encoding="utf-8")
            print("已改指向瘦身版：", f.relative_to(project).as_posix())


if __name__ == "__main__":
    main()
