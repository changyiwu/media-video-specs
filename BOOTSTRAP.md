# BOOTSTRAP.md — 5 階段影片製作流程

> **你是 AI agent。使用者要做影片時，讀完本檔後按 5 個階段依序執行，每個階段都要主動詢問使用者再進行下一步。**
> 本 repo 是「三類影片製作規範 + 可 fork 範本」，不含任何 binary 素材，由 bootstrap 動態準備。
> 專案藍圖與常設規則在 [AGENTS.md](AGENTS.md)；踩坑清單在 [GOTCHAS.md](GOTCHAS.md)。

---

## 階段 0｜識別你自己（agent 相容性）

本 repo 支援四家 agent，**沒有預設偏好**。先確認你是哪一種，再依下表調整動作：

| Agent | 讀本檔的方式 | Skill 安裝路徑 | 特殊備註 |
|-------|-------------|---------------|---------|
| **Claude Code**（CLI / Desktop）| 由 `CLAUDE.md` import `AGENTS.md`，再依指示讀本檔 | `~/.claude/skills/<name>/SKILL.md` | 只讀 `CLAUDE.md`，不讀 `AGENTS.md` |
| **Codex**（CLI）| ✅ 原生讀 `AGENTS.md` | `~/.agents/skills/<name>/SKILL.md`（或專案內 `.agents/skills/`）| YAML frontmatter 格式與 Claude 相同 |
| **OpenCode**（CLI）| 由 `opencode.json` 的 `instructions` 引導 | `~/.config/opencode/skills/<name>/` 或 `.opencode/skills/` | 已附 `opencode.json` 自動引導 |
| **Antigravity 2.x**（Google 桌面 Agent 應用，**不是 IDE**）| ⚠️ 不一定自動讀，必要時請使用者貼本檔給你 | `~/.gemini/config/skills/<name>/` 或 `.agents/skills/` | 它是獨立的 agent 管理應用（可另外把外掛裝進你的編輯器），skill 放進上述目錄後在 App 內確認有被載入 |

### CLI vs Desktop 差異

- **CLI 版**：通常有完整 shell 權限，可直接跑 `install/*.sh`
- **Desktop / IDE 版**：可能需要先在內建終端機跑指令，或請使用者手動執行某些命令
- **Web 版**（無 shell 的聊天介面）：無法跑安裝腳本。請告知使用者本 repo 需 CLI 環境，並轉發 `specs/` 內的規範供他手動參考

### Windows 特殊提醒

- `install/*.sh` 需要 **bash**。Windows 用戶用 **Git Bash**（隨 Git for Windows 安裝）
- 若使用者只有 PowerShell，請用 `install/setup.py`（Python orchestrator，跨平台）或 `install/install_all.ps1`
- 環境變數 `%TEMP%`（cmd/PS）等於 `$TMPDIR` / `$TEMP`（bash）

### 工具名稱對照

不同 agent 的工具名不同，請翻譯為你的工具：

| 動作 | Claude Code | Codex | OpenCode | Antigravity |
|------|-------------|-------|----------|-------------|
| 執行 shell | `Bash` | `shell` | `bash` | 內建終端機 |
| 讀檔 | `Read` | `read_file` | `read` | `read_file` |
| 寫檔 | `Write` | `apply_patch` | `write` | `write_file` |
| 編輯 | `Edit` | `apply_patch` | `edit` | `edit_file` |
| 抓網頁 | `WebFetch` | `web_search` / `fetch` | `webfetch` | 內建瀏覽器 |

---

## 啟動條件

當使用者下達以下指令時，你應**立即**讀取本文件並啟動 5 階段流程：
- 「啟動 media-video-specs」
- 「我要做影片」
- 「按照三類影片規範做⋯」
- 主動發現 cwd 含此 repo 時

---

## 階段 1｜環境檢查

### 你要做的事

依序檢查下列元件，把結果整理成表格給使用者：

| 元件 | 檢查指令 | 必要 |
|------|---------|------|
| Python 3.8+ | `python --version` | ✅ |
| pip | `pip --version` | ✅ |
| edge-tts | `pip show edge-tts` | ✅ TTS 旁白 |
| Node.js 22+ | `node --version` | ✅ HyperFrames 需要 |
| ffmpeg | `ffmpeg -version` | ✅ HyperFrames 算繪與 ffprobe 量旁白長度 |
| HyperFrames | `npx --no-install hyperframes@0.8.181 --version` | ✅ 算繪引擎（GSAP 時間軸 → mp4） |
| 算繪用 Chrome | `npx --no-install hyperframes@0.8.181 browser path` | ✅ HyperFrames 自己管理，不是系統的 Chrome |
| 源石黑體 | 範本內的 `examples/*/assets/fonts/GenSekiGothic2TW-H.otf` | ⚠️ 視覺一致（HyperFrames 只認專案內的字檔，GOTCHAS D-2） |
| kokoro-onnx | `python -c "import kokoro_onnx"` | ⭕ **選用**，只有 `--tts kokoro` 才要（GOTCHAS H-1） |
| fonttools | `python -c "import fontTools"` | ✅ 出片前字型瘦身（`tools/subset_fonts.py`，GOTCHAS D-12）；加裝 `brotli` 才輸出 woff2 |
| Pillow | `python -c "import PIL"` | ⭕ **選用**，只有照片套色（`tools/treat_images.py`）才要 |
| pypinyin＋opencc | `python -c "import pypinyin, opencc"` | ⭕ **選用**，旁白稿多音字預檢（`tools/polyphone_check.py`，GOTCHAS H-4） |

也可以直接跑 `bash install/check_env.sh`（或 `python install/setup.py check`）取得同一份結果。

### 缺少的元件，逐項詢問

對每個**缺失的元件**，詢問使用者：

> 偵測到缺少 **X**。要不要幫你安裝？
> 1. 是，幫我裝
> 2. 我自己處理
> 3. 跳過（不用這個元件）

如果回答「是」，依下表執行：

| 元件 | 安裝指令 |
|------|---------|
| Python | 提示去 https://python.org（不自動裝）|
| pip | `python -m ensurepip --upgrade` |
| edge-tts | `pip install edge-tts` |
| Node.js | 提示去 https://nodejs.org（不自動裝，需 22 以上）|
| ffmpeg | Win x64: `winget install Gyan.FFmpeg`；Win ARM64: 先試 `winget install BtbN.FFmpeg.GPL.9.0 --architecture arm64`，跑 `ffmpeg -version` 若回「應用程式控制原則已封鎖此檔案」（Smart App Control）就 `winget uninstall BtbN.FFmpeg.GPL.9.0` 改裝 `Gyan.FFmpeg`（x64，2026-10-28 LT-YI-RS 實測 ARM64 版被擋）；Mac: `brew install ffmpeg`；Linux: `apt install ffmpeg` |
| HyperFrames + 算繪用 Chrome | 跑 `install/setup_hyperframes.sh`（或 `python install/setup.py hyperframes`）。一律用 `npx` 執行，不在雲端硬碟的專案裡 `npm install`（GOTCHAS D-1） |
| 源石黑體 | 跑 `install/install_fonts.sh`（從 ButTaiwan/genseki-font 下載，並複製進每個範本的 `assets/fonts/`）|
| kokoro-onnx | `pip install kokoro-onnx soundfile`（或裝在獨立 venv 再設 `HYPERFRAMES_PYTHON`，見 GOTCHAS H-1）|
| fonttools | `pip install fonttools brotli` |
| Pillow | `pip install pillow` |
| pypinyin＋opencc | `pip install pypinyin opencc-python-reimplemented` |

完成檢查後，告訴使用者**全部就緒**，準備進入階段 2。

---

## 階段 2｜介紹三類影片

### 你要做的事

讀取 `specs/` 內三份規範的「定位」段，整理成**簡短**對照表給使用者看（**不要把整份 spec 倒給他**）：

```
┌────────────────────────────────────────────────────────────┐
│ 01 活動紀錄影片  60–180s  口白 + 大字卡 + BGM              │
│   ↳ 婚禮、研習、運動會、馬拉松紀念短片                      │
│   ↳ 重點：重現當下情緒                                      │
├────────────────────────────────────────────────────────────┤
│ 02 教學影片     4–8 min  SOIL 教學脈絡 + 動畫 + TTS         │
│   ↳ 國中數學、高中物理、學科概念解釋                        │
│   ↳ 重點：學生看完能複述、能應用                            │
├────────────────────────────────────────────────────────────┤
│ 03 社群科普     2–3 min  強 Hook + 多版面 + 照片佐證        │
│   ↳ FB / IG / YouTube Shorts 上的知識短片                  │
│   ↳ 重點：前 3 秒抓住滑手 + 由淺入深                       │
└────────────────────────────────────────────────────────────┘
```

### 詢問

> 想試做哪一類？
> 1. 試做 01 活動紀錄
> 2. 試做 02 教學影片
> 3. 試做 03 社群科普
> 4. 先看詳細規範
> 5. 跳過試做，直接打包成技能（去階段 5）

如果回答 4：把對應 spec 的「第 9 章 給 agent 的執行 checklist」**整段** show 給他看，然後再次詢問要不要試做。

---

## 階段 3｜試作

> ⚠️ **開工前先讀 [GOTCHAS.md](GOTCHAS.md)**，尤其 A 流程、B 字幕、D HyperFrames 算繪、E 音訊四節。

### 試作前

請使用者提供：
- 主題（如「我女兒的生日影片」「光的折射」「什麼是區塊鏈」）
- 片長偏好（用 spec 預設可）
- 素材狀況（有實拍照？要 Unsplash 氣氛照？要 Wikimedia Commons 證據照（specs/03 6.5）？要 AI 生圖？）
- 對象學到哪裡：教學片問「學生目前學到第幾冊第幾章」，其他類型問觀眾看片時處在什麼階段；開場第一句與結尾預告要對得上（GOTCHAS A-4）
- 旁白聲音與語速（預設 Edge-TTS 女聲 `zh-TW-HsiaoChenNeural`）：教學片**新學單元慢（`-10%`、念完留白 2～4 秒）、複習快（`+35%`、留白 1～2 秒）**，見 specs/02 7.1；以及能不能暫停：預設從頭播到尾，不做按暫停練習頁（GOTCHAS A-5）

### 渲染方式

三支範本都是 [HyperFrames](https://github.com/heygen-com/hyperframes) composition：每頁是一個 clip，
動畫寫在同一條 GSAP 時間軸上，由 HyperFrames 逐格算繪成 mp4。只用到它的 CLI（`npx --yes hyperframes@0.8.181 …`），
是一般的 shell 指令，四家 agent 都能跑；HyperFrames 另外提供給 agent 的 skills（`npx skills add heygen-com/hyperframes`）
是選配，不裝也能照本流程出片。

字型瘦身、成片響度、修唸錯字、找授權照片這幾件事用 repo 根目錄的共用工具（[tools/README.md](tools/README.md)），
都是一般的 Python 指令，用 `--project output/<主題>` 指向影片專案。

### 動工

1. **fork 範本**：複製對應 `examples/0X-XXX/` 到本 repo 的 `output/<主題>/`（已列入 `.gitignore`，作品不進公開 repo），**連同 `assets/fonts/`**（GOTCHAS D-2）
2. **跑對應 spec 的 checklist**：
   - 01：5 段敘事 → 字卡 → 旁白 → BGM 對齊
   - 02：SOIL 1-3 引擎 → 頁面架構 → Edge-TTS → KaTeX/SVG
   - 03：5 段敘事（Hook→比喻→機制→反轉→結語）→ Unsplash／Wikimedia 素材 → 多版面 → Edge-TTS
3. **旁白與時間軸**（02／03）：寫完旁白稿先跑 `python tools/polyphone_check.py --project output/<主題>` 預檢多音字（GOTCHAS H-4），再產生前兩頁給使用者試聽聲音與語速（`python generate_narration.py --page 1 --take try`，GOTCHAS H-7），確認後 `python generate_narration.py` 生成整支旁白並稽核，依稽核表調每頁的 `data-duration`，直到通過
4. **預覽**：`npx --yes hyperframes@0.8.181 preview` 開瀏覽器預覽（存檔自動重新整理），讓使用者先看
5. **關卡**：文字定稿後先 `python tools/subset_fonts.py --project output/<主題>` 瘦身字型（GOTCHAS D-12），再 `npx --yes hyperframes@0.8.181 check`，必須顯示 `Check passed`（缺素材、動畫被切掉都在這裡擋，GOTCHAS D-8）
6. **產出**：`npx --yes hyperframes@0.8.181 render -o final.mp4`，再 `python tools/loudness.py output/<主題>/final.mp4 --apply` 把成片正規化到 −15 LUFS（GOTCHAS E-6），給使用者預覽
7. **每完成一個重要里程碑都告知使用者**（不要悶頭做 10 分鐘才回報）

### 試作完，詢問

> 影片完成了：`<path>`
> 滿意嗎？
> 1. 滿意，進階段 5（打包成技能）
> 2. 想調整（進階段 4）
> 3. 重做（回到階段 3 起點）

---

## 階段 4｜調整

### 詢問

> 想調整哪裡？（可複選）
> 1. 字幕文案 / 旁白內容
> 2. 視覺風格（字級、配色、版面）
> 3. 動畫節奏
> 4. 替換照片素材
> 5. 改片長
> 6. 其他（自由描述）

### 處理

每個調整選項對應的修改路徑：

| 選項 | 改哪裡 |
|------|--------|
| 字幕/旁白 | `generate_narration.py` 內 SCRIPT 陣列 + `index.html` 各頁的 `.subtitle`，改完重跑 `generate_narration.py` |
| 視覺風格 | `index.html` 的 `<style>` 區（依 spec 風格節重新調）|
| 動畫節奏 | `index.html` 檔尾時間軸裡各 tween 的 `S(n) + 秒數` 與 `duration`（03 的 `.anim` 另有 `data-d` 毫秒延遲）|
| 替換照片 | 重新跑 Unsplash 搜尋、`tools/find_images.py`（Wikimedia 證據照）或生圖技能；換 `assets/images/` 內檔案並更新 `CREDITS.md`，要統一配色跑 `tools/treat_images.py` |
| 某頁念錯字 | 不要整頁重跑 TTS：`tools/fix_voice.py` 產生候選 → 試聽 → 等比伸縮換回原長度（GOTCHAS H-5），定案的改寫加進讀音替換表 |
| 改片長 | 改各頁與對應 `<audio>` 的 `data-start`／`data-duration`、根節點的 `data-duration`，跑 `generate_narration.py --audit` 確認 |
| 改語速／換聲音 | `generate_narration.py` 的 `RATE`／`VOICE`，重跑後整支時間軸要重排（GOTCHAS H-3） |

每次調整後跑 `npx --yes hyperframes@0.8.181 check`、**重新算繪**、再跑 `tools/loudness.py --apply`（改過字的話先重跑 `tools/subset_fonts.py`），並再次詢問是否滿意。

---

## 階段 5｜打包成技能（選配）

### 詢問

> 要不要把這次的影片製作流程，打包成可重複呼叫的技能？
> 1. 打包給我用的 agent（Claude Code / Codex / OpenCode / Antigravity 擇一或全部）
> 2. 只生成獨立的 README 範本，不打包
> 3. 不用，到此為止

### 打包指令

四家 agent 用同一支腳本，只差 `--target`：

```bash
bash install/pack_skill.sh <skill-name> <01|02|03> --target=claude
bash install/pack_skill.sh <skill-name> <01|02|03> --target=codex
bash install/pack_skill.sh <skill-name> <01|02|03> --target=opencode
bash install/pack_skill.sh <skill-name> <01|02|03> --target=antigravity

# 沒有 bash 時用 Python 版（同樣四個 target）
python install/setup.py pack <skill-name> <01|02|03> --target=claude
```

腳本會：
1. 建立該 agent 的 skill 目錄
2. 產出 `SKILL.md`（含觸發詞、流程、引用本 repo 的 spec）
3. 告訴使用者觸發詞（如「做一支教學影片」「做社群科普」）

安裝路徑見階段 0 的對照表。**OpenCode** 需確認 config 的 `skills` 路徑包含該目錄；**Antigravity 2.x** 要確認 `~/.gemini/config/skills/` 下的 skill 有被 App 載入（它是獨立桌面應用，不是 IDE）。

### 結束

> ✅ 全部完成！
> - 影片：`<path>`
> - 技能：`<skill-path>`（如有）
> - 下次只要說「<觸發詞>」就會啟動這個工作流。

---

## 給你（agent）的核心提醒

1. **每階段都要等使用者確認再進下一步**，不要連跑五階段
2. **不要悶頭做**，每完成一個小里程碑就回報
3. **缺什麼問什麼**，不要假設使用者已經裝好所有東西
4. **照 spec 走**，不要自由發揮
5. **試作完用使用者的真實主題**，不要用範例主題交差

---

## 失敗排除

**完整踩坑清單見 [GOTCHAS.md](GOTCHAS.md)（開工前必讀）。** 高頻幾條：

| 問題 | 處理 | 詳見 |
|------|------|------|
| npm install 在 GDrive 壞掉 | HyperFrames 一律用 `npx`，不在專案裡裝 | GOTCHAS D-1 |
| 字體沒顯示 / `invalid_parent_traversal_in_asset_path` | 字檔放專案內 `assets/fonts/`，跑 install_fonts | GOTCHAS D-2 / C-5 |
| 每段旁白都從 0 秒開始 | `data-start`／`data-duration` 寫在標籤上，不要用 JS 設 | GOTCHAS D-3 |
| render 出來的公式重複兩次 | KaTeX 樣式改由 JS 載入，載完才註冊時間軸 | GOTCHAS D-6 |
| `check` 報 404／`audio_src_not_found` | 補素材（BGM、照片） | GOTCHAS E-3 |
| 整支片沒聲音 | 每個 `<audio>` 都要有 `id` | GOTCHAS E-1 |
| 動畫最後幾階沒出現就切頁 | `check` 會報「分階動畫被切掉」，加長該頁 `data-duration` | GOTCHAS C-7 |
| Edge-TTS 被斷線 | 序列執行 + retry 3 次 | — |
| `--tts kokoro` 報缺 kokoro-onnx | `pip install kokoro-onnx soundfile` 或設 `HYPERFRAMES_PYTHON` | GOTCHAS H-1 |
| Python 中文崩潰（CP950）| 設 `PYTHONUTF8=1` | GOTCHAS F-1 |
| PowerShell 中文路徑複製失敗 | 用 `Get-ChildItem \| Copy-Item` | GOTCHAS F-2 |
| HyperFrames CLI `init` 在 Node 24 crash | 不需要 `init`，直接 fork 範本 | GOTCHAS C-4 |

---

> 📚 對應文件
> - [AGENTS.md](AGENTS.md)（專案藍圖）
> - [README.md](README.md)（人類入口）
> - [GOTCHAS.md](GOTCHAS.md)（踩坑筆記）
> - [specs/01-活動紀錄影片.md](specs/01-活動紀錄影片.md)
> - [specs/02-教學影片.md](specs/02-教學影片.md)
> - [specs/03-社群科普影片.md](specs/03-社群科普影片.md)
