# tools/ — 三類影片共用的工具

在 **repo 根目錄**執行，用 `--project output/<主題>` 指向影片專案（或直接給成片路徑）。
都是一般的 Python 指令，四家 agent 一樣用；不要複製進每個範本，避免各份分叉。

| 工具 | 做什麼 | 什麼時候用 | 需要 | 說明 |
|------|--------|-----------|------|------|
| `subset_fonts.py` | 把源石黑體切成片中用到的字（每個字重約 15 MB → 約 100 KB），`@font-face` 改指向瘦身版 | 文字定稿後、`check` 之前；改過字就重跑 | `fonttools`（選用 `brotli`） | GOTCHAS D-12 |
| `loudness.py` | 量測成片響度；`--apply` 正規化到 −15 LUFS、真峰值 ≤ −1 dBTP | 每支片 `render` 完、交片前 | ffmpeg | GOTCHAS E-6 |
| `polyphone_check.py` | 掃旁白稿（套過讀音替換表後），標出可能被 TTS 念錯的多音字，同一個詞只列一次並附頁碼 | 寫完旁白稿、產生旁白前 | `pypinyin`、`opencc-python-reimplemented` | GOTCHAS H-4 |
| `fix_voice.py` | 某頁念錯字時：候選試聽 → 整句等比伸縮換回原長度 → 列出需要修的 tween | 片做完才聽出念錯（事前預防用讀音替換表） | ffmpeg；逐詞比對需 edge-tts | GOTCHAS H-5 |
| `find_images.py` | 從 Wikimedia Commons 找授權照片（只收 PD／CC0／CC BY／CC BY-SA），下載並寫 `CREDITS.md` | 社群科普需要「證據照」時 | 網路 | specs/03 6.5 |
| `treat_images.py` | 照片裁切、縮放，套成片子的兩色（duotone）或保留原色 | 照片要融進配色時 | `pillow` | specs/03 6.3 |

## 出片順序

```bash
python tools/subset_fonts.py --project output/<主題>                 # 文字定稿後
npx --yes hyperframes@0.8.181 check                                   # 在影片專案資料夾內
npx --yes hyperframes@0.8.181 render -o final.mp4
python tools/loudness.py output/<主題>/final.mp4 --apply
```

`subset_fonts.py` 會改寫 `index.html`，只能在 `output/<主題>/` 跑，在 `examples/` 會被拒絕（範本在版控裡，字檔不在）。

## 修念錯字

```bash
cd output/<主題>
python generate_narration.py --page 3 --take A --rate=-5%
python generate_narration.py --page 3 --take B --text "換了拼法的整句"
cd ../..
python tools/fix_voice.py --project output/<主題> audition --page 3 --clauses 1 2   # 串成試聽檔，用耳朵選
python tools/fix_voice.py --project output/<主題> apply --page 3 --take B
python tools/fix_voice.py --project output/<主題> restore --page 3                  # 反悔時還原
```

## 來源

`subset_fonts.py`、`fix_voice.py`、`find_images.py`、`treat_images.py` 改編自
[mathruffian-dot/claude-motion-explainer-video](https://github.com/mathruffian-dot/claude-motion-explainer-video)
（MIT License，Copyright (c) 2026 mathruffian-dot），改寫成本 repo 的逐頁旁白與範本結構；各檔開頭註明了改了什麼。
`loudness.py` 是本 repo 新寫的。授權全文見 [LICENSE](../LICENSE) 的 THIRD-PARTY CODE 段。
