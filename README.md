# media-video-specs

> 三類影片製作規範 + 自動 bootstrap 流程，給 AI agent 和創作者用。
> 支援 **Claude Code、Codex、OpenCode、Antigravity** 四家 agent，無預設偏好。
> **AI agent 讀本 repo 後，請先讀 [AGENTS.md](AGENTS.md)，再依 [BOOTSTRAP.md](BOOTSTRAP.md) 跑 5 階段流程。**

---

## 一句話總結

把「我想做一支影片」這句話，自動分流到三類規範之一，依規範跑完整工作流，最後可打包成可重複呼叫的技能。

---

## Repo 內容

```
media-video-specs/
├── README.md                    ← 本檔（人類入口）
├── AGENTS.md                    ← 專案藍圖（Codex / OpenCode / Antigravity 原生讀）
├── CLAUDE.md                    ← 橋接檔（Claude Code 讀，import AGENTS.md）
├── BOOTSTRAP.md                 ← AI agent 入口，5 階段影片製作流程
├── GOTCHAS.md                   ← 踩坑筆記（開工前必讀）
├── LICENSE
├── opencode.json                ← OpenCode 的 instructions 引導
├── tts-lexicon.md               ← 讀音替換表（多音字、英文詞 → TTS 念得對的寫法）
├── specs/                       ← 三類影片規範（核心）
│   ├── 01-活動紀錄影片.md
│   ├── 01-活動紀錄影片.html     ← 規範視覺化版
│   ├── 02-教學影片.md
│   └── 03-社群科普影片.md
├── examples/                    ← 三個 HyperFrames 範本可 fork（HTML + GSAP → mp4）
│   ├── 01-marathon-light/
│   ├── 02-factors-multiples/
│   └── 03-ai-context/
├── templates/                   ← 發布資訊範本（YouTube／FB／IG／Threads 文案）
├── tools/                       ← 三類共用的出片工具（字型瘦身、成片響度、修念錯字、授權照片）
└── install/                     ← 自動安裝工具
    ├── check_env.sh
    ├── install_fonts.sh         ← 源石黑體（從 ButTaiwan 下載）
    ├── setup_hyperframes.sh     ← 算繪引擎（Node 22+、FFmpeg、算繪用 Chrome）
    ├── pack_skill.sh            ← 打包成四家 agent 的 skill
    ├── install_all.sh           ← 一鍵裝全部 optional 元件
    ├── install_all.ps1          ← Windows 無 bash 時用
    └── setup.py                 ← 跨平台 Python orchestrator
```

**不含任何 binary 素材**（mp4、mp3、png、字體）— 全部透過 bootstrap 動態取得。

---

## 三類影片速覽

| # | 類型 | 片長 | 核心元素 |
|---|------|------|---------|
| **01** | 活動紀錄影片 | 60–180s | 口白 + 大字卡 + BGM 過場 |
| **02** | 教學影片 | 4–8 min | SOIL 教學脈絡 + 動畫 + Edge-TTS |
| **03** | 社群科普影片 | 2–3 min | 強 Hook + 多版面 + 照片佐證 |

完整規範在 [`specs/`](specs/)。

三類都用同一條管線：HTML/CSS/SVG 排版、GSAP 時間軸做動畫、Edge-TTS 生旁白，再由 [HyperFrames](https://github.com/heygen-com/hyperframes) 逐格算繪成 mp4（`npx --yes hyperframes@0.8.181 render`），最後把成片響度正規化到 −15 LUFS。出片前後用到的共用工具見 [tools/README.md](tools/README.md)。

---

## 給 AI Agent 用

當你（AI agent）看到這個 repo：

1. 開啟 [AGENTS.md](AGENTS.md)（Claude Code 走 [CLAUDE.md](CLAUDE.md) 橋接）了解專案藍圖與常設規則
2. 開啟 [BOOTSTRAP.md](BOOTSTRAP.md)，**先讀階段 0 確認自己的相容性**
3. 從**階段 1 環境檢查**開始
4. 每個階段都要**主動詢問使用者**再進下一步
5. 不要悶頭做，每完成一個里程碑就回報

### 四家 agent 相容性

| Agent | 讀專案藍圖的方式 | Skill 路徑 | 狀態 |
|-------|-----------------|----------|------|
| **Claude Code**（CLI + Desktop）| `CLAUDE.md` → `@AGENTS.md` | `~/.claude/skills/` | 完整支援 |
| **Codex**（CLI）| ✅ 原生讀 `AGENTS.md` | `~/.agents/skills/` | 完整支援 |
| **OpenCode**（CLI）| ✅ 透過 `opencode.json` 引導 | `~/.config/opencode/skills/` | 已附 opencode.json |
| **Antigravity 2.x**（Google 桌面 Agent 應用，非 IDE）| ⚠️ 部分，必要時手動貼檔 | `~/.gemini/antigravity/skills/` | 需在 App 內確認 skill 已載入 |
| **Web-only agents** | ❌ 無 shell | n/a | 只能參考 specs，無法跑 install |

---

## 給人類用

```bash
# 1. 取得 repo（或直接把資料夾放進你的工作目錄）
cd media-video-specs

# 2. 環境檢查 + 安裝（任選一個跑法）
#  選項 A：bash（macOS / Linux / Windows Git Bash）
bash install/check_env.sh && bash install/install_all.sh

#  選項 B：PowerShell（Windows 沒裝 Git Bash 的用）
powershell -ExecutionPolicy Bypass -File install/install_all.ps1

#  選項 C：Python（全平台通用，無需 bash）
python install/setup.py check
python install/setup.py all

# 3. 對你的 Claude Code / Codex / OpenCode / Antigravity 說：
#    「啟動 media-video-specs」
#    或直接：「我要做一支教學影片」

# Agent 會自動依 BOOTSTRAP.md 的 5 階段流程進行
```

### 打包成技能（四家 agent 同一支腳本，只差 `--target`）

```bash
# Bash 版
bash install/pack_skill.sh my-video 02 --target=claude
bash install/pack_skill.sh my-video 02 --target=codex
bash install/pack_skill.sh my-video 02 --target=opencode
bash install/pack_skill.sh my-video 02 --target=antigravity

# Python 版（同樣四個 target）
python install/setup.py pack my-video 02 --target=claude
```

---

## 設計依據

- **SOIL 教學心法**（李俊儀教授）— spec 02 骨架
- **林長揚 30 原則** — 字級階、配色、留白規則
- **林長揚 #7**「字體選黑體粗體」— 為何選源石黑體
- **林長揚 #1**「黃金比例 55/34/21/13」— 字級階梯

---

## 原作者與致謝

**本專案的三類影片規範、範本與 bootstrap 流程，原作者是「三師爸」。**
本 repo 是在其作品基礎上的衍生版本，主要改動是把原本以單一 agent 為預設的設計，改成 Claude Code／Codex／OpenCode／Antigravity 四家對等支援。原始著作權聲明保留於 [LICENSE](LICENSE)。

其他致謝：[李俊儀教授](https://www.facebook.com/profile.php?id=100007283099373)（SOIL 教學心法） · [林長揚](https://www.facebook.com/changyanglin)（簡報 30 原則） · [ButTaiwan/genseki-font](https://github.com/ButTaiwan/genseki-font)（源石黑體） · [Unsplash](https://unsplash.com) · [edge-tts](https://github.com/rany2/edge-tts) · [HyperFrames](https://github.com/heygen-com/hyperframes)（HeyGen，算繪引擎） · [GSAP](https://gsap.com)（動畫時間軸） · [claude-motion-explainer](https://github.com/mathruffian-dot/claude-motion-explainer-video)（`tools/` 的字型瘦身、修念錯字、授權照片工具與 GOTCHAS 📎 條目的來源，MIT） · [Wikimedia Commons](https://commons.wikimedia.org)（授權照片）

---

## 授權

- 程式碼與規範：**MIT License**（原作者三師爸 + 本版修改者，兩份聲明並列於 [LICENSE](LICENSE)）
- 字體：源石黑體 SIL Open Font License
- 範例會用到的 Unsplash 照片：Unsplash License
- `tools/` 改編自 claude-motion-explainer 的四支腳本：MIT License（原著作權聲明附於 [LICENSE](LICENSE) 的 THIRD-PARTY CODE 段）
- `tools/find_images.py` 取得的 Wikimedia Commons 照片：各依其授權（PD／CC0／CC BY／CC BY-SA），來源記在各影片專案的 `assets/images/CREDITS.md`
- 執行時取得、不隨 repo 散布的工具：HyperFrames（Apache 2.0）、GSAP、KaTeX（MIT），各依其授權
