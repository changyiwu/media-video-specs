# media-video-specs（專案藍圖）

> 本檔為跨 Agent 通用的專案藍圖（AGENTS.md 開放標準）。任何 Agent 的每個 session 都應先讀本檔＋`handoff.md`。
> Claude Code 有 `CLAUDE.md` 時只讀它，故由 `CLAUDE.md` 的 `@AGENTS.md` import 本檔（`CLAUDE.md` 只有這一行）；Claude 專屬規範寫在本檔〈Claude Code 專屬〉一節。

## 專案簡介

三類影片（活動紀錄／教學／社群科普）的製作硬規範 + 可 fork 的 HTML 範本 + 跨平台安裝腳本，供 **Claude Code、Codex、OpenCode、Antigravity** 四家 AI agent 共用。目標是把「我想做一支影片」這句話，自動分流到三類規範之一，依規範跑完整工作流，最後可打包成該 agent 可重複呼叫的技能。

本 repo **不含任何 binary 素材**（mp4、mp3、png、字體），全部由 bootstrap 動態取得。

原始版本由 **三師爸** 製作（詳見 [README.md](README.md) 的〈原作者與致謝〉），本 repo 是 changyiwu 的衍生版本，主要差異是把單一 agent 假設改成四家 agent 對等支援。

## 關鍵時程

<!-- 目前無外部時程壓力 -->

## 目標與路線圖

- [x] 階段一：去識別化 — 移除原作者私人資訊與其專屬 CI，改為自有版本
- [x] 階段二：四家 agent 對等 — 命名、文件敘事、打包腳本不再以 Claude 為預設
- [x] 階段三：文件格式標準化 — `AGENTS.md`／`CLAUDE.md`／`handoff.md` 改用 project-init 範本格式
- [x] 渲染管線改為 HyperFrames — 三支範本改成 GSAP 時間軸 composition，取代 Playwright 錄影 + ffmpeg mux
- [ ] 階段四：實跑驗證 — 用真實主題各跑一支 01／02／03，確認 specs 與範本沒有斷裂（02 已完成；01／03 待素材）
- [ ] 階段五：打包成常設技能 — 驗證通過後 `pack_skill.sh` 裝進四家 agent

## 資料夾結構

```
media-video-specs/
├── README.md                    ← 人類入口
├── AGENTS.md                    ← 本檔，專案藍圖（Codex / OpenCode / Antigravity 讀）
├── CLAUDE.md                    ← 橋接檔（Claude Code 讀，import AGENTS.md）
├── handoff.md                   ← 交接檔（不進 git，靠雲端硬碟同步）
├── BOOTSTRAP.md                 ← 5 階段影片製作流程（agent 動工時讀）
├── GOTCHAS.md                   ← 踩坑筆記（開工前必讀）
├── LICENSE
├── opencode.json                ← OpenCode 的 instructions 引導
├── tts-lexicon.md               ← 讀音替換表（四個 repo 各一份、內容相同，見下方規則）
├── specs/                       ← 三類影片規範（核心）
│   ├── 01-活動紀錄影片.md
│   ├── 01-活動紀錄影片.html     ← 規範視覺化版
│   ├── 02-教學影片.md
│   └── 03-社群科普影片.md
├── examples/                    ← 三個 HyperFrames 範本可 fork
│   ├── 01-marathon-light/
│   ├── 02-factors-multiples/
│   └── 03-ai-context/
├── tools/                       ← 三類共用的出片工具（用 --project output/<主題> 呼叫，見 tools/README.md）
│   ├── subset_fonts.py          ← 字型瘦身（GOTCHAS D-12）
│   ├── loudness.py              ← 成片響度 −15 LUFS（GOTCHAS E-6）
│   ├── polyphone_check.py       ← 旁白稿多音字預檢（GOTCHAS H-4）
│   ├── fix_voice.py             ← 事後修念錯字（GOTCHAS H-5）
│   ├── find_images.py           ← Wikimedia Commons 授權照片
│   └── treat_images.py          ← 照片裁切、套色
├── templates/
│   └── 發布資訊範本.md          ← 上架與社群文案範本（五個媒體專案共用，正本在 media-youtube-publish）
├── output/                      ← 用本 repo 做的影片專案（每支一個子資料夾，已列入 .gitignore）
└── install/                     ← 自動安裝工具
    ├── check_env.sh
    ├── install_fonts.sh         ← 源石黑體（從 ButTaiwan 下載）
    ├── setup_hyperframes.sh     ← 算繪引擎（npx --yes hyperframes@0.8.181）
    ├── pack_skill.sh            ← 打包成四家 agent 的 skill
    ├── install_all.sh
    ├── install_all.ps1          ← Windows 無 bash 時用
    └── setup.py                 ← 跨平台 Python orchestrator
```

## 專案專屬規則：影片製作流程

使用者說「我要做影片」「啟動 media-video-specs」「按照三類影片規範做⋯」，或你發現 cwd 是本 repo 時：

1. **先讀 [BOOTSTRAP.md](BOOTSTRAP.md)**，按 5 階段執行（階段 0 識別 agent → 1 環境檢查 → 2 介紹三類 → 3 試作 → 4 調整 → 5 打包技能）
2. **動工前必讀 [GOTCHAS.md](GOTCHAS.md)**，尤其 A 流程、B 字幕、D HyperFrames 算繪、E 音訊四節
3. **每階段都要等使用者確認再進下一步**，不要連跑五階段
4. 影片專案一律放在本 repo 的 `output/<主題>/`（fork 範本到這裡），`output/` 已列入 `.gitignore`，不要放到 repo 外或加回版控

不可妥協的三條鐵律（來自 GOTCHAS A 節）：

- 任何 code／TTS／渲染之前，**第一步必須產出 `SCRIPT.md`（旁白＋字卡＋分鏡）與 `DESIGN.md`（字體／配色／字級／版面／動畫節奏）並在對話中展示給使用者審查**，等明確說「go」才動工
- 字幕**壓成單行、每段 ≤ 25 字**，以不換行為最大原則
- HyperFrames **一律用 `npx --yes hyperframes@0.8.181 …` 執行**，不在雲端硬碟上的專案裡 `npm install`；出片前 `npx --yes hyperframes@0.8.181 check` 必須通過

其他常設規則：

- 成片驗收通過後，照 `templates/發布資訊範本.md` 寫 `output/<主題>/發布資訊.md`（YouTube／FB／IG／Threads 文案、AI 揭露、`CREDITS.md` 署名）；範本五個媒體專案各一份、內容逐位元組相同，正本在 media-youtube-publish 的 `skills/youtube-video-workflow/references/`，改正本再整份覆蓋，不在本專案就地改
- 成片一律用 `tools/loudness.py --apply` 正規化到 **−15 LUFS**、真峰值 ≤ −1 dBTP 再交片（GOTCHAS E-6）
- 三類共用的工具放 `tools/`，用 `--project output/<主題>` 呼叫；**不要複製進每個範本**（02、03 的 `generate_narration.py` 已經是兩份副本，改它時兩份一起改、只讓常數與旁白稿不同）
- 讀音替換表 `tts-lexicon.md` **四個 repo 各一份、內容逐位元組相同**（本 repo、media-short-film、media-voice-clone、agent-speak/speak/；四個都公開，各自要單獨可用）：**改表時四份一起改**，用 `python ../media-short-film/tools/tts_lexicon.py --check`／`--sync` 檢查與合併；同層時程式會合併讀取，本 repo 的優先
- HyperFrames 版本**鎖定不追最新**，升級照 GOTCHAS D-11 的程序（三支範本 `check`／`render` 過再一起換版本號）

## 專案專屬規則：四家 Agent 對等

本專案支援 Claude Code、Codex、OpenCode、Antigravity，**沒有預設偏好的 agent**。修改時遵守：

- 新增文件敘述、腳本輸出、skill 打包邏輯時，四家一律平等對待，不要寫成「以 Claude 為主、其他為輔」
- `pack_skill.sh` 與 `setup.py pack` 的 `--target` 必須同時支援 `claude｜codex｜opencode｜antigravity`，新增功能時四個分支都要補
- 各家的 skill 安裝路徑對照表以 [BOOTSTRAP.md](BOOTSTRAP.md) 階段 0 為單一真相來源，其他檔案要引用不要複製
- 只有 Claude Code 需要的規範集中寫在本檔末尾的〈Claude Code 專屬〉一節（`CLAUDE.md` 只放一行 import），其他章節維持四家對等、不要混進 Claude 專屬內容

## 專案專屬規則：授權與署名

- 原作者 **三師爸** 的著作權聲明**必須保留**在 `LICENSE` 與 `README.md`，任何改寫都不得移除
- 反之，原作者的**私人資訊**（個人帳號路徑、私有 repo 網址、其專屬 CI 設定）一律移除，不要在新增內容時又寫回去
- 第三方素材授權（源石黑體 SIL OFL、Unsplash License、Wikimedia Commons 各檔授權）在 `LICENSE` 的 THIRD-PARTY ASSETS 段，新增素材要同步補上
- 引用的第三方程式碼（`tools/` 改編自 mathruffian-dot/claude-motion-explainer-video，MIT）原著作權聲明附在 `LICENSE` 的 THIRD-PARTY CODE 段；改寫這些檔案時保留檔頭的來源註記

## 同步層級（本專案初始化至第 3 層級）

| 層級 | 平台 | 位置 | 讀取時機 |
|------|------|------|---------|
| L1 | 本地（GDrive） | `AGENTS.md`＋`handoff.md`（不進 git，只走雲端硬碟）＋`CLAUDE.md`（橋接） | 每個 session |
| L2 | GitHub | <https://github.com/changyiwu/media-video-specs>（**公開**） | 指定時 |
| L3 | Obsidian | `media-video-specs/專案工作流程.md` | 有需要時 |

## 三個檔案的職責（依「時效性」分家，不是依「詳細程度」）

| 檔案 | 時效 | 寫入方式 | 放什麼 |
|------|------|---------|--------|
| `handoff.md` | **只對下一個 session 有效**，過期即丟 | 每次收工**整份重寫** | 做到哪、下一步、**這次**的暫時 workaround |
| `AGENTS.md`（本檔） | **長期有效**，每個 session 都適用 | 只有規則本身變了才改 | 目標、路線圖、常設規則、結構 |
| Obsidian（L3）／`git log` | **歷史**：發生過什麼、為什麼 | 只增不刪 | 決策紀錄、踩坑完整版、逐次進度 |

驗收標準：**`handoff.md` 整份刪掉，不應損失任何長期資訊**——會的話代表該升級進本檔卻沒升級。

**本檔不要出現的東西**（會無限膨脹，且開工每次都要重讀）：
- ❌ `## 最近進度`／逐次工作紀錄 → 有 L3 寫 Obsidian「🗓️ 最近更動紀錄」；沒有就靠 `git log`（所以 commit 訊息要寫「做什麼＋為什麼」）
- ❌ 決策記錄、取捨理由、踩坑經過的完整版 → Obsidian「決策紀錄」「🕳️ 踩坑筆記」
- ✅ 只留「結論式的規則」：踩過的坑收斂成一條**祈使句**寫進〈工作約定〉或〈專案專屬規則〉，理由那一大段留在 Obsidian

> 本專案的踩坑筆記是**例外**：`GOTCHAS.md` 是要跟著 repo 一起發布給其他人看的**產品內容**，不是本專案的內部歷史，所以留在 repo 內、不搬去 Obsidian。

## 工作約定
- 任何 Agent、任何電腦：**開工先讀 `handoff.md`，收工必更新 `handoff.md`**
- `handoff.md` **不進 git**（含真實電腦名與本機絕對路徑），已列入 `.gitignore`，跨電腦靠雲端硬碟同步——不要把它加回版控
- 修改共用檔案前先讀最新內容，避免覆蓋其他 Agent 的變更
- 本 repo 在雲端硬碟上：**判斷檔案版本一律用 `git diff HEAD`／`git log`，不要靠讀檔內容或時間戳**——同步延遲會讓稍後才落地的改動看起來像第三方寫入
- 新電腦第一次用 HyperFrames，先執行 `npx --yes hyperframes@0.8.181 telemetry disable` 關閉匿名使用統計
- 所有回應與文件使用繁體中文
- 修改前先確認計畫，優先保留原有資料結構
- **產出一律放 `output/`**：本專案產生的檔案或資料夾（成品、匯出、報表、生成圖、渲染等）預設放專案根目錄的 `output/`，不另開 `outputs/`、`exports/`、`generated/`、`out/` 之類的資料夾，方便找；`output/` 不進 git。部署工具指定的建置目錄（`dist/`、`build/`）不在此限

## Claude Code 專屬

- 本專案支援四家 agent 且**刻意不以 Claude 為預設**。回應與文件不要寫成「這是 Claude 專用的 repo」，也不要把 Claude Code 的路徑／工具名當成通則寫進 `AGENTS.md`（本節除外）、`BOOTSTRAP.md`、`README.md` 或 `install/` 腳本——那四處要維持四家對等。
- 打包技能測試時，別只跑 `--target=claude`；四個 target 都要驗過再說「打包功能正常」。
- `examples/03-ai-context/` 的影片內容有提到 Claude 與 `/compact`，那是**影片主題本身**（在講 context window），不是品牌綁定，去識別化時不要動它。
