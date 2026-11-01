# tools/ — 三類影片共用的工具

在 **repo 根目錄**執行，用 `--project output/<主題>` 指向影片專案（或直接給成片路徑）。
都是一般的 Python 指令，四家 agent 一樣用；不要複製進每個範本，避免各份分叉。

| 工具 | 做什麼 | 什麼時候用 | 需要 | 說明 |
|------|--------|-----------|------|------|
| `subset_fonts.py` | 把源石黑體切成片中用到的字（每個字重約 15 MB → 約 100 KB），`@font-face` 改指向瘦身版 | 文字定稿後、`check` 之前；改過字就重跑 | `fonttools`（選用 `brotli`） | GOTCHAS D-12 |
| `loudness.py` | 量測成片響度；`--apply` 正規化到 −15 LUFS、真峰值 ≤ −1 dBTP | 每支片 `render` 完、交片前 | ffmpeg | GOTCHAS E-6 |
| `review_times.py` | 算審片的時間點：每個旁白子句結束前 0.15 秒、每頁頁尾前 1.6 秒；`--table` 看對照、`--pages` 給 `snapshot --at` | 通常由 `sheet.py` 自動呼叫 | ffmpeg | GOTCHAS D-10 |
| `sheet.py` | 從草稿抽格拼 contact sheet（4×2、每格手機寬度），附每格對應旁白的對照表 | `check` 通過後、定稿前，流程見 [review-loop.md](review-loop.md) | ffmpeg、`pillow` | GOTCHAS D-10 |
| `polyphone_check.py` | 掃旁白稿（套過讀音替換表後），標出可能被 TTS 念錯的多音字，同一個詞只列一次並附頁碼 | 寫完旁白稿、產生旁白前 | `pypinyin`、`opencc-python-reimplemented` | GOTCHAS H-4 |
| `fix_voice.py` | 某頁念錯字時：候選試聽 → 整句等比伸縮換回原長度 → 列出需要修的 tween | 片做完才聽出念錯（事前預防用讀音替換表） | ffmpeg；逐詞比對需 edge-tts | GOTCHAS H-5 |
| `find_images.py` | 從 Wikimedia Commons 找授權照片（只收 PD／CC0／CC BY／CC BY-SA），下載並寫 `CREDITS.md` | 社群科普需要「證據照」時 | 網路 | specs/03 6.5 |
| `treat_images.py` | 照片裁切、縮放，套成片子的兩色（duotone）或保留原色 | 照片要融進配色時 | `pillow` | specs/03 6.3 |
| `h3_runner.py` | 走 HTTP 呼叫 ComfyUI 生成一段 MiniMax H3 片段；`--check`、`--lint`、`--dry-run` 不生成 | 社群科普需要拍不到的動態畫面時（選配） | ComfyUI、H3 模型；本身只用標準函式庫 | specs/03 6.6、GOTCHAS D-15 |
| `hw_check.py` | 看 CPU、記憶體、GPU、硬碟與 edge-tts 版本，印出本流程的建議設定（推估值） | 新電腦第一次出片 | 無 | BOOTSTRAP 階段 1 |

## 出片順序

```bash
python tools/subset_fonts.py --project output/<主題>                 # 文字定稿後
npx --yes hyperframes@0.8.181 check                                   # 在影片專案資料夾內
npx --yes hyperframes@0.8.181 render --quality draft -o renders/draft.mp4
python tools/sheet.py --project output/<主題>                         # 逐張看，修到沒問題（review-loop.md）
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

`subset_fonts.py`、`fix_voice.py`、`find_images.py`、`treat_images.py`、`review_times.py`、`sheet.py`、`h3_runner.py`、`hw_check.py` 改編自
[mathruffian-dot/claude-motion-explainer-video](https://github.com/mathruffian-dot/claude-motion-explainer-video)
（MIT License，Copyright (c) 2026 mathruffian-dot），改寫成本 repo 的逐頁旁白與範本結構；各檔開頭註明了改了什麼。
`sheet.py` 與 `review-loop.md` 的循環和檢查表原出處是 [whaleyxbt/claude-motion](https://github.com/whaleyxbt/claude-motion)（MIT License，Copyright (c) 2026 whaleyxbt）。
`loudness.py` 是本 repo 新寫的。授權全文見 [LICENSE](../LICENSE) 的 THIRD-PARTY CODE 段。
