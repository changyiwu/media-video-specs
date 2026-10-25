# 生成 12 段逐頁旁白，並稽核 index.html 的時間軸
# 執行：
#   python generate_narration.py               生成旁白（Edge-TTS）+ 稽核
#   python generate_narration.py --audit       只稽核（改了 data-duration 之後用，不重跑 TTS）
#   python generate_narration.py --tts kokoro  改用 HyperFrames 內建 TTS（Kokoro，中國腔，見 specs/02 7.1）
#   python generate_narration.py --page 3 --take B [--text "換拼法的整句"] [--rate=-5%]
#                                              只重念第 3 頁當修唸錯字的候選，交給 tools/fix_voice.py（GOTCHAS H-5）
# 稽核通過後：npx --yes hyperframes@0.8.181 check → npx --yes hyperframes@0.8.181 render -o final.mp4
import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

# Windows 主控台預設 CP950，直接 print 中文會變亂碼。
# 下面「旁白 vs 版面」對照表正是要靠它判斷哪頁該調 data-duration，印成亂碼等於白印。
# SystemExit 的訊息走 stderr，兩條都要改。
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
OUT = HERE / "assets" / "narration"

# Edge-TTS（預設，台灣腔）
VOICE = "zh-TW-HsiaoChenNeural"  # 預設女聲；男聲用 zh-TW-YunJheNeural
RATE = "-8%"  # 社群片比教學片略快（specs/03）
PITCH = "-2Hz"

# 念完旁白後的留白（秒），稽核用；規範建議 2~4s
TAIL = (2, 4)

# HyperFrames 內建 Kokoro-82M（備案：免網路、免金鑰，但只有中國口音的 zf_xiaobei）
KOKORO_VOICE = "zf_xiaobei"
KOKORO_SPEED = 0.92  # 對應 Edge-TTS 的 RATE -8%

SCRIPT = [
    (1,  "為什麼 AI 用一用，會突然忘了你剛剛說過什麼？"),
    (2,  "AI 沒有真正的記憶。它有的，是一張短期便利貼。這張便利貼，叫做「上下文」。"),
    (3,  "你說的每句話、AI 回的每句話，都會被一起貼在這張便利貼上。AI 才有辦法接話。"),
    (4,  "便利貼的單位叫做 token，大約一個中文字就是一個 token。GPT-4 約十二萬八千 token，Claude 約二十萬。聽起來很多——"),
    (5,  "但對話越長，越早的內容會被擠出視窗。AI 就「忘了」前面講過什麼。"),
    (6,  "所以，不是 AI 變笨。是它的便利貼被塞爆了。"),
    (7,  "怎麼辦？這裡有三個破解的招式。"),
    (8,  "第一招：摘要。把舊對話濃縮成重點，省下空間。Claude Code 裡的 compact 指令，就是這個。"),
    (9,  "第二招：外部記憶。把資訊存到檔案或資料庫，要用時再撈回來。這叫做 RAG。"),
    (10, "第三招：分工。讓子代理處理細節，主代理只接收結果摘要。避免每個 agent 都拿到全部 context。"),
    (11, "三個馬上能用的小建議：開新對話、適時 compact、長文件交給 agent 從檔案讀。"),
    (12, "AI 的智力，受限於它能記得多少。學會管理上下文，就是學會放大它的腦容量。"),
]


# ---- 讀音替換表（tts-lexicon.md，GOTCHAS H-4） ----
# Edge-TTS 不能用 SSML 指定讀音，多音字、英文詞念錯只能改字。表在 media-video-specs 根目錄的 tts-lexicon.md
# （格式與規則寫在表的開頭：| 原文 | 改寫 | 說明 | 的 Markdown 表格）。只改送進 TTS 的文字，字幕不受影響。
# 這份表有四份、內容相同（另外三份在 media-short-film、media-voice-clone、agent-speak/speak/）。
# 找表順序，遠的在前、近的覆蓋遠的：同層另外三份（有就合併）→ 環境變數 TTS_LEXICON 指的表
# → 從本資料夾往上每一層的 tts-lexicon.md（專案在 repo 的 output/ 或 examples/ 裡時，repo 根目錄那份就在其中）。
# 專案 fork 到 repo 以外的地方時，設 TTS_LEXICON 指向 media-video-specs/tts-lexicon.md。

LEX = "tts-lexicon.md"
SIBLINGS = [("media-short-film", LEX), ("media-voice-clone", LEX), ("agent-speak", f"speak/{LEX}")]


def lexicon_files():
    siblings = [next((d / repo / rel for d in (HERE, *HERE.parents) if (d / repo / rel).is_file()), None)
                for repo, rel in SIBLINGS]
    env = os.environ.get("TTS_LEXICON")
    out = []
    for f in [*siblings, Path(env) if env else None, *reversed([d / LEX for d in (HERE, *HERE.parents)])]:
        if f and f.is_file() and f.resolve() not in {x.resolve() for x in out}:
            out.append(f)
    return out


def lex_cells(line):
    s = line.strip()[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]
    return [c[1:-1] if len(c) >= 2 and c[0] == c[-1] == "`" else c for c in cells]


def load_lexicon():
    # 只讀表頭是「原文｜改寫」的表格；同一個原文以近的那份為準
    table = {}
    for f in lexicon_files():
        inside = False
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if not line.lstrip().startswith("|"):
                inside = False
                continue
            c = lex_cells(line)
            if c[:2] == ["原文", "改寫"]:
                inside = True
                continue
            if not inside or all(re.fullmatch(r":?-+:?", x) for x in c if x):
                continue
            if len(c) < 2 or not c[0] or not c[1]:
                raise SystemExit(f"{f} 格式不對（| 原文 | 改寫 | 說明 |，原文、改寫都不能空）：{line}")
            table[c[0]] = c[1]
    return table


def speakable(text, table):
    # 長的原文先比對，一次掃完：換過的結果不會再被其他條目換
    if not table:
        return text
    pat = re.compile("|".join(re.escape(k) for k in sorted(table, key=len, reverse=True)))
    return pat.sub(lambda m: table[m.group(0)], text)


# ---- TTS ----

async def synth_edge(text, out, rate=RATE, pitch=PITCH):
    import edge_tts
    c = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch)
    await c.save(str(out))


def synth_kokoro(text, out):
    npx = shutil.which("npx")
    if not npx:
        raise SystemExit("找不到 npx，先跑 install/setup_hyperframes.sh（需要 Node.js 22+）")
    with tempfile.TemporaryDirectory() as tmp:
        # 旁白文字走 .txt 檔，不直接當參數傳：Windows 的 npx 是 .cmd，
        # 中文標點與 & | ^ 之類字元經過 cmd.exe 轉義會壞掉
        txt, wav = Path(tmp) / "line.txt", Path(tmp) / "line.wav"
        txt.write_text(text, encoding="utf-8")
        subprocess.run([npx, "--yes", "hyperframes", "tts", str(txt), "--voice", KOKORO_VOICE,
                        "--speed", str(KOKORO_SPEED), "--output", str(wav)], check=True)
        # 轉成 mp3：index.html 的 <audio src> 一律指向 page-NN.mp3，換引擎不必改版面
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                        "-c:a", "libmp3lame", "-q:a", "2", str(out)], check=True)


async def synth(engine, text, out, rate=RATE, pitch=PITCH):
    for attempt in range(3):
        try:
            if engine == "kokoro":
                synth_kokoro(text, out)
            else:
                await synth_edge(text, out, rate, pitch)
            return
        except Exception as e:
            print(f"retry {out.name} ({attempt + 1}): {e}")
            await asyncio.sleep(2)
    raise SystemExit(f"{out.name} 連續三次生成失敗")


async def generate(engine):
    OUT.mkdir(parents=True, exist_ok=True)
    lex = load_lexicon()
    print(f"讀音替換表：{len(lex)} 條（{'、'.join(str(f) for f in lexicon_files())}）" if lex else
          "讀音替換表：找不到 tts-lexicon.md（repo 根目錄應有一份；專案不在 media-video-specs 裡時設 TTS_LEXICON 指向它），不做替換")
    for i, t in SCRIPT:
        spoken = speakable(t, lex)
        if spoken != t:
            print(f"  page-{i:02d} 改讀：{spoken}")
        await synth(engine, spoken, OUT / f"page-{i:02d}.mp3")
        print(f"OK page-{i:02d}.mp3")
    print("All done.")


# ---- 修唸錯字的候選（tools/fix_voice.py，GOTCHAS H-5） ----
# 整頁重念一次，存成 assets/narration/fix/cand/page-NN_<take>.mp3；旁邊的 .json 記下實際送進 TTS 的文字與參數，
# fix_voice.py 試聽、套用、比對逐詞時間都靠它。定案的改字要寫進讀音替換表（H-4），--text 只是拿來試念。

async def make_take(engine, page, tag, text, rate, pitch):
    lines = dict(SCRIPT)
    if page not in lines:
        raise SystemExit(f"SCRIPT 沒有第 {page} 頁")
    if engine == "kokoro" and (rate, pitch) != (RATE, PITCH):
        print("Kokoro 沒有 rate／pitch 可調，這兩個參數會被忽略；候選之間的差異只能靠 --text")
    spoken = speakable(text or lines[page], load_lexicon())
    out = OUT / "fix" / "cand" / f"page-{page:02d}_{tag}.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    await synth(engine, spoken, out, rate, pitch)
    meta = {"page": page, "take": tag, "engine": engine,
            "voice": KOKORO_VOICE if engine == "kokoro" else VOICE,
            "rate": rate, "pitch": pitch, "text": spoken}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {out.relative_to(HERE).as_posix()}：{spoken}")


# ---- 稽核：index.html 的時間軸 ----
# 時間軸的唯一真相來源是 index.html 標籤上的 data-start／data-duration（HyperFrames 靜態讀取，
# 見 GOTCHAS D-3）。這裡檢查它和旁白對不對得上，不合規就 exit 1，不要進 render。

class Timeline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root_dur = None
        self.pages = []   # (page, id, start, dur)
        self.audios = {}  # id -> (src, start, dur)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-composition-id" in a and self.root_dur is None:
            self.root_dur = float(a["data-duration"]) if "data-duration" in a else None
        if "data-page" in a:
            self.pages.append((int(a["data-page"]), a.get("id"),
                               float(a.get("data-start", "nan")), float(a.get("data-duration", "nan"))))
        if tag == "audio" and a.get("id"):
            self.audios[a["id"]] = (a.get("src"), float(a.get("data-start", "nan")),
                                    float(a.get("data-duration", "nan")))


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def audit():
    tl = Timeline()
    tl.feed((HERE / "index.html").read_text(encoding="utf-8"))
    pages = sorted(tl.pages)
    errors, warns = [], []

    if len(pages) != len(SCRIPT):
        raise SystemExit(f"index.html 有 {len(pages)} 頁（data-page），SCRIPT 有 {len(SCRIPT)} 段，兩者要一致")

    # 1. 起點連續：每頁 start = 前一頁 start + duration
    expect = 0.0
    for n, pid, start, dur in pages:
        if start != expect:
            errors.append(f"page {n:02d}（#{pid}）data-start={start:g}，應為 {expect:g}（前一頁 start + duration）")
        expect = start + dur
    total = sum(d for *_, d in pages)

    # 2. 根節點總長 = 各頁加總
    if tl.root_dur != total:
        errors.append(f"根節點 data-duration={tl.root_dur}，應為各頁加總 {total:g}")

    # 3. 每頁的旁白 <audio> 要和該頁同時段
    for n, _, start, dur in pages:
        aid = f"nar-{n:02d}"
        if aid not in tl.audios:
            errors.append(f"page {n:02d}：找不到 <audio id=\"{aid}\">（沒有 id 的 audio 會被混音器略過）")
            continue
        src, a_start, a_dur = tl.audios[aid]
        if src != f"assets/narration/page-{n:02d}.mp3":
            errors.append(f"page {n:02d}：#{aid} 的 src 是 {src}，應為 assets/narration/page-{n:02d}.mp3")
        if (a_start, a_dur) != (start, dur):
            errors.append(f"page {n:02d}：#{aid} 時段 {a_start:g}+{a_dur:g}s 和頁面 {start:g}+{dur:g}s 不一致")

    # 4. 旁白 vs 版面：dur >= 旁白 + TAIL（動畫 + 1.5s 那條下限由頁面自己的守衛量，見 GOTCHAS C-7）
    print(f"\n旁白 vs 版面（data-duration 下限：旁白 + {TAIL[0]:g}~{TAIL[1]:g}s——見 GOTCHAS C-7）：")
    for n, _, start, dur in pages:
        mp3 = OUT / f"page-{n:02d}.mp3"
        if not mp3.exists():
            errors.append(f"page {n:02d}：缺 {mp3.name}，先跑一次不帶 --audit 的 generate_narration.py")
            continue
        a = probe(mp3)
        tail = dur - a
        mark = ""
        if a > dur:
            errors.append(f"page {n:02d}：旁白 {a:.2f}s 比版面 {dur:g}s 長，尾巴會被切掉")
            mark = "  <== 旁白超出版面"
        elif tail < TAIL[0]:
            warns.append(f"page {n:02d}：tail 只有 {tail:.2f}s（建議 {TAIL[0]:g}~{TAIL[1]:g}s）")
            mark = "  <== tail 偏短"
        elif tail > TAIL[1]:
            warns.append(f"page {n:02d}：tail 有 {tail:.2f}s（建議 {TAIL[0]:g}~{TAIL[1]:g}s）")
            mark = "  <== tail 偏長"
        print(f"  page {n:02d}  起點 {start:6g}s  旁白 {a:6.2f}s  版面 {dur:4g}s  餘裕 {tail:5.2f}s{mark}")

    for w in warns:
        print(f"  警告：{w}")
    if errors:
        print()
        for e in errors:
            print(f"  錯誤：{e}")
        raise SystemExit("\n時間軸不合規，先改 index.html 的 data-start／data-duration 再重跑 --audit")
    print(f"\nOK 時間軸稽核通過，總長 {total:g}s。下一步（在 output/<主題>/ 裡）：文字定稿後 python ../../tools/subset_fonts.py --project . "
          "→ npx --yes hyperframes@0.8.181 check → npx --yes hyperframes@0.8.181 render -o final.mp4 "
          "→ python ../../tools/loudness.py final.mp4 --apply（GOTCHAS D-12／E-6）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="生成逐頁旁白並稽核 index.html 時間軸")
    ap.add_argument("--audit", action="store_true", help="只稽核，不重跑 TTS")
    ap.add_argument("--tts", choices=["edge", "kokoro"], default="edge",
                    help="edge＝Edge-TTS 台灣腔（預設）；kokoro＝HyperFrames 內建，免網路但為中國口音")
    # argparse 的 help 會做 % 格式化，語速裡的 % 要寫成 %%
    ap.add_argument("--page", type=int, help="只重念這一頁，當作修唸錯字的候選（和 --take 一起用）")
    ap.add_argument("--take", help="候選代號（A、B、C…），存成 assets/narration/fix/cand/page-NN_<take>.mp3")
    ap.add_argument("--text", help="這個候選要念的整句（換拼法試念用）；省略就用 SCRIPT 原句")
    ap.add_argument("--rate", default=RATE, help=f"候選的語速，預設 {RATE.replace('%', '%%')}；負值要寫成 --rate=-5%%")
    ap.add_argument("--pitch", default=PITCH, help=f"候選的音高，預設 {PITCH}")
    args = ap.parse_args()
    if args.page or args.take:
        if not (args.page and args.take):
            raise SystemExit("--page 和 --take 要一起給")
        asyncio.run(make_take(args.tts, args.page, args.take, args.text, args.rate, args.pitch))
        raise SystemExit(0)
    if not args.audit:
        asyncio.run(generate(args.tts))
    audit()
