# 從 Wikimedia Commons 找可以放進影片的授權照片（含 NASA 等公有領域照片），下載並記錄來源
# 執行（在 repo 根目錄）：
#   python tools/find_images.py search "Apollo 11 lunar module" [--limit 8]
#   python tools/find_images.py get "File:Apollo 11 Lunar Module.jpg" --name lunar --project output/<主題> [--width 1920]
#
# 只保留允許放進影片再發布的授權：公有領域、CC0、CC BY、CC BY-SA（NC、ND、合理使用一律擋掉）。
# `get` 存到 <專案>/assets/images/<name>.<副檔名>，並在 assets/images/CREDITS.md 寫一行作者、授權、來源；
# 畫面上的來源標示照它印出的那行寫（specs/03 第 6.3 節）。下載後要親眼看一次：路人、其他品牌的 logo、
# 浮水印要裁掉或換一張。
#
# 定位：Unsplash（specs/03 Tier 1）適合氣氛照；這支適合「證據照」——歷史照片、實驗裝置、真的存在的東西。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 find_images.py（MIT License，
# Copyright (c) 2026 mathruffian-dot）：存放路徑改成本 repo 範本用的 assets/images/、訊息改繁中。
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia API 要求 User-Agent 帶聯絡方式
UA = "media-video-specs/1.0 (https://github.com/changyiwu/media-video-specs)"
OK = re.compile(r"^(public domain|pd\b|cc0|cc by(-sa)? \d|cc-by(-sa)?-\d)", re.I)


def api(params):
    params = {"format": "json", **params}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def info(page):
    ii = page["imageinfo"][0]
    m = ii.get("extmetadata", {})
    strip = lambda s: re.sub(r"<[^>]+>", "", s or "").strip()
    return {
        "title": page["title"],
        "width": ii.get("width"), "height": ii.get("height"),
        "license": strip(m.get("LicenseShortName", {}).get("value")),
        "license_url": strip(m.get("LicenseUrl", {}).get("value")),
        "artist": strip(m.get("Artist", {}).get("value"))[:80],
        "page": ii.get("descriptionurl"),
        "thumb": ii.get("thumburl"),
    }


def search(q, limit):
    d = api({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": q,
             "gsrlimit": limit * 3, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
             "iiextmetadatafilter": "LicenseShortName|Artist"})
    rows = [info(p) for p in (d.get("query", {}).get("pages", {}) or {}).values()]
    rows = [r for r in rows if OK.match(r["license"] or "")][:limit]
    for r in rows:
        print(f'{r["title"][:72]:72} {r["width"]}x{r["height"]} | {r["license"]} | {r["artist"]}')
    if not rows:
        print("找不到可用授權的結果：換關鍵字（英文通常比較多），或改用 Unsplash／生圖")


def get(title, name, project, width):
    d = api({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
             "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist", "iiurlwidth": width})
    page = list(d["query"]["pages"].values())[0]
    if "imageinfo" not in page:
        raise SystemExit(f'Wikimedia Commons 沒有這個檔案：{title}（從 search 的結果複製完整的 "File:..." 標題）')
    r = info(page)
    if not OK.match(r["license"] or ""):
        raise SystemExit(f'不下載 {title}：授權「{r["license"]}」不是公有領域／CC0／CC BY／CC BY-SA')
    ext = Path(urllib.parse.urlparse(r["thumb"]).path).suffix.lower() or ".jpg"
    dest_dir = Path(project).resolve() / "assets" / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name}{ext}"
    req = urllib.request.Request(r["thumb"], headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())
    credits = dest_dir / "CREDITS.md"
    lic = f'{r["license"]} ({r["license_url"]})' if r.get("license_url") else r["license"]
    line = (f'- {dest.name} — "{r["title"][5:]}" by {r["artist"] or "unknown"}, {lic}, via Wikimedia Commons: '
            f'{r["page"]} — 已裁切、縮放（套色見 treat_images 的設定）\n')
    old = credits.read_text(encoding="utf-8") if credits.exists() else "# 圖片來源\n\n"
    # 重新下載同名檔案時取代舊的那一行
    old = "".join(l for l in old.splitlines(keepends=True) if not l.startswith(f"- {dest.name} — "))
    credits.write_text(old + line, encoding="utf-8")
    print(f"已存 {dest}")
    print(f'畫面標示：Photo: {r["artist"] or "unknown"} · {r["license"]} · Wikimedia Commons')
    if "SA" in r["license"].upper():
        print("注意：CC BY-SA 的照片裁切、套色後仍是 CC BY-SA，CREDITS.md 與畫面標示都要寫清楚")


def main():
    ap = argparse.ArgumentParser(description="從 Wikimedia Commons 找授權照片")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="搜尋，只列出可用授權")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=8)
    g = sub.add_parser("get", help="下載一張並寫進 CREDITS.md")
    g.add_argument("title", help='search 結果裡的完整標題，例如 "File:xxx.jpg"')
    g.add_argument("--name", required=True, help="存檔用的短名（不含副檔名）")
    g.add_argument("--project", required=True, help="影片專案資料夾（output/<主題>）")
    g.add_argument("--width", type=int, default=1920)
    a = ap.parse_args()
    if a.cmd == "search":
        search(a.query, a.limit)
    else:
        get(a.title, a.name, a.project, a.width)


if __name__ == "__main__":
    main()
