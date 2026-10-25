# 產生旁白前，把旁白稿裡容易被 TTS 念錯的多音字標出來（GOTCHAS H-4）
# 執行（在 repo 根目錄；output/<主題> 是有 generate_narration.py 的專案）：
#   python tools/polyphone_check.py --project output/<主題>
#   python tools/polyphone_check.py --project output/<主題> --all    常錯清單以外的多音字也一起檢查（比較吵）
#
# 掃的是「送進 TTS 的文字」：先套讀音替換表，已經改寫掉的詞（奇數 → 基數）不會再列。
# 先轉簡體再查 pypinyin（它的詞典收的是簡體詞；直接查繁體時「長方形」猜 zhǎng、「銀行」猜 xíng），然後標出兩種地方：
#   1. 讀音不是這個字最常見的讀法（例：奇數的奇念 jī）——TTS 最容易在這裡念成常見讀法
#   2. 常錯清單裡的字、但詞典沒收這個詞（例：「十一少一」的少）——讀音只能靠猜，要人聽
# 同一個詞只列一次（附頁碼）。列出的讀音是 pypinyin 的判斷，**不保證對**（實測「數一數」還是猜錯），
# 是「該去聽哪裡」的清單：產生旁白後優先聽這幾處，念錯就加讀音替換表、重跑那頁（片已做完就用 tools/fix_voice.py）。
#
# 想要自動判斷聲調：media-short-film 的 tools/pron_check.py 會逐字比對音高曲線，但要 torchaudio、
# parselmouth 等較重的依賴，本 repo 不內建。
# 需要：pip install pypinyin opencc-python-reimplemented（沒有 opencc 時只看常錯清單、不判斷讀音）
import argparse
import importlib.util
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# 教學、科普旁白常被念錯的多音字（spec 02 點名的奇少數還差重，加上實際常見的）
WATCH = set("奇少數還差重長調行便降種相應將當曾解樂好量率角處朝薄省卷背傳參給只正興覺似塞假藏")
# 「一」「不」的讀音隨後一個字變調（一個 yí、不會 bú），不是多音字念錯，不檢查
SANDHI = set("一不")


def load_project(root):
    gn = Path(root).resolve() / "generate_narration.py"
    if not gn.exists():
        raise SystemExit(f"{gn.parent} 沒有 generate_narration.py（要從 02／03 範本 fork 的專案）")
    spec = importlib.util.spec_from_file_location("generate_narration", gn)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def t2s_or_none():
    try:
        import opencc
    except ImportError:
        return None
    for cfg in ("t2s", "t2s.json"):
        try:
            return opencc.OpenCC(cfg).convert
        except Exception:
            pass
    return None


def is_cjk(ch):
    return "一" <= ch <= "鿿"


def phrase_at(simp, i, phrases):
    """包含第 i 個字、詞典有收的最長詞（2–4 字）"""
    for n in (4, 3, 2):
        for a in range(i - n + 1, i + 1):
            if a >= 0 and a + n <= len(simp) and simp[a:a + n] in phrases:
                return a, a + n
    return None


def main():
    ap = argparse.ArgumentParser(description="旁白稿的多音字預檢")
    ap.add_argument("--project", required=True, help="影片專案資料夾（output/<主題>）")
    ap.add_argument("--all", action="store_true", help="常錯清單以外的多音字也檢查「詞典沒收」這一項")
    a = ap.parse_args()
    try:
        from pypinyin import Style, pinyin
        from pypinyin.constants import PHRASES_DICT
    except ImportError:
        raise SystemExit("需要 pypinyin：pip install pypinyin opencc-python-reimplemented")
    t2s = t2s_or_none()
    if t2s is None:
        print("沒有 opencc：只列常錯清單裡的字，不判斷讀音（pip install opencc-python-reimplemented）\n")
    gn = load_project(a.project)
    lex = gn.load_lexicon()
    found = {}                                           # 詞 → {說明, 頁碼}
    for page, text in gn.SCRIPT:
        spoken = gn.speakable(text, lex)
        simp = t2s(spoken) if t2s else spoken
        guess = [x[0] for x in pinyin(simp, style=Style.TONE3, errors=lambda s: ["-"] * len(s))] if t2s else None
        for i, ch in enumerate(spoken):
            if not is_cjk(ch) or ch in SANDHI:
                continue
            readings = list(dict.fromkeys(pinyin(simp[i], style=Style.TONE3, heteronym=True)[0]))
            if len(readings) < 2:
                continue
            span = phrase_at(simp, i, PHRASES_DICT) if t2s else None
            if t2s and span:
                word, why = spoken[span[0]:span[1]], None
                # 輕聲（這個 ge、記得 de）不是念錯，跳過
                if guess[i] != readings[0] and guess[i][-1:].isdigit():
                    why = f"念 {guess[i]}，不是最常見的 {readings[0]}"
            else:
                # 用前面一個字組成的詞分組（沒有就用後面一個字），「個數」「個數除」「個數是」算同一個
                prev = spoken[i - 1] if i > 0 and is_cjk(spoken[i - 1]) else ""
                nxt = spoken[i + 1] if i + 1 < len(spoken) and is_cjk(spoken[i + 1]) else ""
                word = prev + ch if prev else ch + nxt
                why = None
                if ch in WATCH or (a.all and t2s):
                    why = f"詞典沒收，可能念 {'／'.join(readings[:4])}" + (f"（猜 {guess[i]}）" if guess else "")
            if why:
                key = (word, ch)
                found.setdefault(key, [why, []])
                if page not in found[key][1]:
                    found[key][1].append(page)
    if not found:
        print("沒有需要特別聽的多音字")
        return
    for (word, ch), (why, pages) in sorted(found.items(), key=lambda kv: kv[1][1][0]):
        print(f"  「{word}」的「{ch}」：{why}　第 {'、'.join(str(p) for p in pages)} 頁")
    allp = sorted({p for _, ps in found.values() for p in ps})
    print(f"\n共 {len(found)} 個詞：產生旁白後優先聽第 {'、'.join(str(p) for p in allp)} 頁的這幾處；"
          "念錯就加讀音替換表（tts-lexicon.md，四份一起改）再重跑那頁")


if __name__ == "__main__":
    main()
