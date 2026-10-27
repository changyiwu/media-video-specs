# GOTCHAS — 踩坑筆記

> 實戰中累積的坑，**開工前先讀一遍**。多數是跨 agent 通則，少數標注特定環境。
> 來源：在 OpenCode / Claude Code / **Antigravity** / Windows 上實際跑這套流程踩到的。
> 每條格式：**現象 → 原因 → 教訓**。

圖例：🌍 所有 agent 通則 ｜ 🪟 Windows 專屬 ｜ 🔧 特定工具

📎 引自 [claude-motion-explainer](https://github.com/mathruffian-dot/claude-motion-explainer-video) 的實戰紀錄（lessons.md），本 repo 的範本還沒有重現過；照做無妨，遇到和描述不同時以實測為準

---

## A. 流程（最重要，先看）

### A-1 🌍 未先寫腳本對齊就直接開工
- **現象**：照片還沒拷到 assets，agent 已經悶頭開始錄；做到一半才發現素材沒到位、結構不對，整支重做。
- **原因**：agent 預設「使用者已同意」，沒先確認素材到位、沒寫 SCRIPT.md 對齊就跳進執行階段。
- **教訓**：做任何影片，**第一步一定是寫 `SCRIPT.md`（旁白 + 字卡 + 分鏡）+ 素材清單給使用者確認**。確認後才動工。

### A-2 🌍 未先展示視覺規範就開始實作
- **現象**：做到一半，使用者才問「視覺規範是什麼？我要先看過」。
- **原因**：agent 跳過 DESIGN.md 的展示與確認，直接從腳本跳到 code。
- **教訓**：腳本確認後、實作之前，**必須先產出 `DESIGN.md`（字體 / 配色 / 字級 / 版面 / 動畫節奏）給使用者看過**，確認才寫 code。

### A-3 🌍 預設直接開工，未主動前置對齊（最高安全防線）
- **現象**：收到影片指令就直接寫播放器 + 渲染代碼，事後大規模返工。
- **原因**：缺乏「腳本與視覺規範為前置條件」的鐵律意識，沒有主動煞車對齊。
- **教訓**：任何 code / TTS / 渲染之前，**第一步必須產出 `SCRIPT.md` 與 `DESIGN.md` 並在對話中展示給使用者審查**；等使用者明確說「go」才動工。**這是無可妥協的最高防線。**

### A-4 🌍 對象的「時間點」沒問清楚，開場第一句就講錯
- **現象**：腳本寫「升上國中之前，先複習⋯」，使用者回「對象是已經升上國一的學生」；改完又再補一句「是已經要學第 1 冊第 2 章的國一生」。開場、封面、結尾預告前後改了三輪。
- **原因**：只問了年級，沒問觀眾**現在學到課本的哪裡**。同一個年級，「升學前」「開學後」「要學第 2 章」對觀眾是完全不同的情境，開場與結尾預告的說法也跟著不同。
- **教訓**：設定對象時**一定要問「學生目前學到第幾冊第幾章」**（教學片），非教學片則問觀眾看片時處在什麼階段。答案寫進 SCRIPT.md 的對象欄；開場第一句、封面標語、結尾預告都要對得上那個冊次章節。

### A-5 🌍 不要擅自加「按暫停練習」頁
- **現象**：腳本放了「換你試試看，按下暫停」＋ 5 秒倒數，使用者要求刪掉：影片要從頭播到尾，不暫停。
- **原因**：把課堂講義的「練習題」習慣搬進影片；但影片常在課堂投影或自學時連續播放，倒數只是空白。
- **教訓**：**預設影片從頭播到尾**。想加練習，就做成直接講解的第二道例題（「再看一題」）；只有使用者要求才做暫停頁。

---

## B. 字幕（通則）

### B-1 🌍 字幕換行 / 過長
- **現象**：字幕折成兩三行、或一行塞太多字，閱讀節奏被打斷。
- **原因**：文案沒壓縮、強迫換行。
- **教訓**：**字幕壓成單行，每段 ≤ 25 字，以不換行為最大原則**。寧可縮短文案，也不要兩行字幕。太長就拆成兩個 beat。

---

## C. GSAP 時間軸（範本的動畫寫法）

> 三支範本都是 [HyperFrames](https://github.com/heygen-com/hyperframes)（HeyGen 開源，Apache 2.0）的 composition：
> 每頁是一個帶 `data-start`／`data-duration` 的 `class="clip"`，所有動畫寫在**同一條** `gsap.timeline({ paused: true })`，
> 註冊到 `window.__timelines["main"]`。HyperFrames 逐格把時間軸撥到指定秒數再截圖，所以畫面只能由「時間」決定。
> 驗證版本：HyperFrames **0.8.181**（2026-10-20 從 0.8.171 升級：三支範本的 `check` 結果與舊版相同，02 實際算繪過）。指令一律 `npx --yes hyperframes@0.8.181 …`，行為若和本筆記不同，先 pin 回這個版本比對。

### C-1 🔧 `class="clip"` 在時段外會被隱藏
- **現象**：只有最後一幕出現，前面場景空白；或交叉淡化時上一頁突然消失、閃一下黑。
- **原因**：clip 只在 `data-start` 到 `data-start + data-duration` 之間顯示，時間到就被框架隱藏。
- **教訓**：`data-duration` 必須覆蓋到該元素**退場動畫完全結束**的時間。要做交叉淡化，就讓上一頁的 `data-duration` 多延長淡化的長度、和下一頁重疊（01 範本每拍 5 秒、clip 5.8 秒）。

### C-2 🔧 tween 的開始時間要落在 clip 時段內
- **現象**：元素出現後沒動畫，直接靜態顯示或位置錯誤。
- **原因**：tween 在 clip 還沒顯示時就跑完了，觀眾看到的只剩終點狀態。
- **教訓**：時間軸裡一律寫「該頁起點 + 頁內秒數」。範本用 `S(n) + 秒數`（`S(n)` 從標籤讀第 n 頁的 `data-start`），不要手算絕對秒數。

### C-3 🔧 CSS `transform` 被 GSAP 覆蓋
- **現象**：元素偏移、不置中（`translate(-50%,-50%)` 失效）。
- **原因**：GSAP 動 `x/y/scale/rotation` 時會**完全覆蓋** CSS 的 `transform`；lint 會報 `gsap_css_transform_conflict`。
- **教訓**：會被 GSAP 動到的元素，CSS 不要寫 `transform`。置中改用 flex 或 `left:0; right:0; margin:0 auto`（見 D-4）；起始位移寫進 `fromTo` 的起點。
- 📎 **旋轉過的容器也一樣**：斜放的方塊（例如畢氏定理斜邊上的正方形）用 CSS `rotate` 擺好角度後，再對它本身做 GSAP 動畫，角度會被蓋掉。容器只負責旋轉，動畫只動它**裡面**的子元素。

### C-4 🪟🔧 HyperFrames CLI `init` 在 Windows + Node 24 crash
- **現象**：Exit code `-1073740791`（STATUS_STACK_BUFFER_OVERRUN）。
- **原因**：CLI 的 native module 與 Node 24 / Windows 相容性問題（舊版 CLI 的紀錄）。
- **教訓**：加 `--non-interactive --example blank --skip-skills` 可避開；或改用 Node 22 LTS。0.8.171 在 Windows + Node 24 實測 `check`／`render`／`tts` 都正常；0.8.181 實測 `check`／`render` 正常（`tts`、`init` 未重測）。本 repo 的範本直接 fork 即可，不需要 `init`。

### C-5 🌍🔧 字型需要 `@font-face` 宣告
- **現象**：影片文字用了預設字型而非指定字型；lint 報 `font_family_without_font_face`。
- **原因**：HyperFrames 不會去找系統字型名稱。
- **教訓**：`<style>` 內必須有 `@font-face` 指向**專案資料夾內**的 `.otf`（見 D-2）。Google Fonts 的 `<link>` 例外：HyperFrames 會在算繪時自動換成固定版本的字檔（01 範本就是這樣用）。

### C-6 🔧 影片音訊要分離
- **現象**：`<video>` 內嵌音軌在時間軸上無法正確 seek。
- **原因**：HyperFrames 要求 video 與音軌分開管理。
- **教訓**：`<video muted>` + 另開 `<audio>`；子合成用 `data-composition-src="compositions/file.html"`。

### C-7 🌍 分階動畫比旁白長，`data-duration` 只照旁白算會被切掉
- **現象**：某頁的逐步動畫（因數樹、知識地圖）最後一兩階還沒出現，就切到下一頁了。
- **原因**：頁長是照「旁白時長 + 2–4s tail」訂的，但分階動畫的總長是**最後一階的開始時間 + 該階長度**，跟旁白長度無關。旁白短、動畫長的頁（金句頁、總結圖）最容易中招。
- **教訓**：頁長取**兩個下限的較大者**——`旁白 + 2~4s` 與 `動畫完成 + 1.5s`（規範 5.2「動畫結束後靜止 1.5s 以上」）。
- **範本已機制化，不必自己記**：兩道關卡各管一個下限。
  - `generate_narration.py`：量每頁旁白，`旁白 > 頁長` 直接 `exit 1`，tail 不在 2–4s 印警告。
  - 每支 `index.html` 檔尾的**分階動畫守衛**：逐一量時間軸上每個 tween 的實際結束時間，超過「頁尾 − 1.5s」就丟錯。`npx --yes hyperframes@0.8.181 check` 會把它列成 `page_error` 並判定失敗；直接 `render` 也會被擋（但要等整支擷取完才報錯，所以先跑 `check`）。
- **刻意持續到頁尾的動畫**（粒子、脈動、Ken Burns、進度條）在 tween 加 `data: 'ambient'`；拍尾的退場淡出加 `data: 'exit'`。守衛會略過這兩種。教學內容的 reveal 不要加，加了就等於關掉檢查。
- **為什麼現在可以自動量**：舊版用 CSS transition + `setTimeout`，靜態分析猜不準，只好讓人手動宣告 `anim`。改成 HyperFrames 後所有動畫都在同一條 GSAP 時間軸上，`tl.getChildren()` 拿得到每個 tween 的確切起訖，量出來的就是實際會播的，所以不必再宣告、也不會忘記同步。

### C-8 🔧 SVG 群組用 `scale` 進場，結束後可能殘留位移
- **現象**：兩條數線上的圓點（JS 動態建立的 `<g>`，含圓圈＋數字）用 `scale 0.5→1` 進場，算繪後整組往上偏了約 20px，圓點浮在數線上方；同頁另一顆圓也錯位。
- **原因**：GSAP 對 SVG 元素的 `transformOrigin` 是用 bbox 換算成平移補償，元素建立當下（字型未載完、群組尚未顯示）量到的 bbox 不準，補償就殘留在最終 transform 裡。不是每頁都會發生，難以事前判斷。
- **教訓**：**資料點、座標上的標記這類「位置就是意義」的 SVG 元素，進場只用 `opacity`**；`scale` 留給 HTML 元素或位置錯一點也無妨的裝飾。出片前用 `snapshot --zoom` 放大檢查（D-10）。

### C-9 🔧📎 遮罩揭示的文字，起點就露出一條邊
- **現象**：文字從遮罩下方滑上來（`overflow: hidden` 的外框 + 內層 `yPercent: 100 → 0`），還沒開始動就看得到一條字的上緣。
- **原因**：內層同時加了 `rotation`（例如 3°）時，旋轉讓一角翹到遮罩邊緣上方；中文字比 line box 高，更容易露出來。
- **教訓**：有旋轉的遮罩揭示，起點改成 `yPercent: 135`；出片前用 `snapshot --zoom` 看起點那一格。

### C-10 🔧📎 計數器和長條同時長大，方向卻相反
- **現象**：數字由 0 數到 100（`power2.out`，先快後慢），旁邊一排長條用 `stagger: { each, ease: "power2.out" }` 依序出現，結果長條先慢後快，和數字對不上。
- **原因**：stagger 的 `ease` 管的是「各元素的**起跑時間**怎麼分配」，不是每根長條自己的動畫曲線，所以同一個 ease 效果剛好反過來。
- **教訓**：要讓第 k 根長條在數字數到它代表的值時出現，起跑時間用計數器 ease 的**反函數**算：`power2.out` 是 `1 - sqrt(1 - y)`、`power3.out` 是 `1 - cbrt(1 - y)`（y 是該長條的值佔總值的比例），一根一根排進時間軸，不要用 stagger。

### C-11 🌍📎 數字要在旁白念到之前數完，不要用 `onUpdate` 改文字
- **現象**：旁白念「等於十六」時，畫面上的倒數還停在 17；或預覽正常、算繪出來數字卡住不動。
- **原因**：計數動畫開始得太晚、數太久；另外 HyperFrames 是把時間軸 seek 到每一格再截圖，GSAP 的 `seek()` 預設不觸發 callback，靠 `onUpdate` 改 `textContent` 的計數器在算繪時不可靠（也違反 D-5「畫面只能由時間決定」）。
- **教訓**：數字的動畫要在念到那個數字的時間點（H-2 的逐詞秒數）**之後 0.5 秒內結束**。計數器寫成「每個值一個元素、在時間軸上依序切換 `opacity`／`visibility`」，跳到任何一格都正確；用 `snapshot` 在念到數字的那一格確認（D-10）。

### C-12 🔧📎 描線動畫的路徑，還沒開始畫就先露出一個小點
- **現象**：用 `stroke-dasharray`／`stroke-dashoffset` 從 0 開始畫線，開始前畫面上已經有一個小方塊或小圓點。
- **原因**：`stroke-linecap: square`（或 `round`）在線段長度為 0 時仍會畫出線帽。
- **教訓**：做描線動畫的路徑一律 `stroke-linecap: butt`。

---

## D. HyperFrames 算繪 / 雲端硬碟

### D-1 🌍 不要在雲端硬碟上的專案裡 `npm install`
- **現象**：卡住、大量 `TAR_ENTRY_ERROR`、timeout、`Invalid package config`。
- **原因**：Google Drive 同步引擎對大量小檔案操作效能極差。
- **教訓**：HyperFrames **一律用 `npx --yes hyperframes@0.8.181 …` 執行**，套件落在 npm 快取（`~/.npm/_npx`）、算繪用的 Chrome 落在 `~/.cache/hyperframes/`，都不在專案裡。專案內只會多出 `.hyperframes/`（本機狀態與 check／snapshot 產物），已列入 `.gitignore`。第一次用先跑 `bash install/setup_hyperframes.sh`。

### D-2 🌍 字檔必須在專案資料夾內
- **現象**：lint 報 `invalid_parent_traversal_in_asset_path`，字型沒套上。
- **原因**：HyperFrames 把專案資料夾當根目錄，`../../assets/fonts/` 這種跳出去的路徑會被夾回根目錄或解析到別處。
- **教訓**：每個影片專案都放一份 `assets/fonts/`，`@font-face` 寫 `url('assets/fonts/…')`。`install_fonts.sh`／`setup.py fonts` 會自動複製進 `examples/*/assets/fonts/`；**fork 範本到別處時連同 `assets/fonts/` 一起複製**。字檔不進 git（`.gitignore` 已排除）。

### D-3 🌍 時間軸屬性要直接寫在標籤上
- **現象**：lint 報 `media_missing_data_start`；`npx --yes hyperframes@0.8.181 timeline` 顯示每段旁白都從 0 秒開始。
- **原因**：HyperFrames 先**靜態**讀 HTML 決定時間軸，用 JS 在載入後才設定的 `data-start`／`data-duration` 它看不到。根節點的 `data-duration`（總長）更是只讀一次。
- **教訓**：每頁 `<section>` 與對應的 `<audio>` 都把 `data-start`／`data-duration` 寫死在標籤上。規則：`data-start` = 前一頁 start + duration、根節點 `data-duration` = 各頁加總、旁白 `<audio>` 時段與該頁相同。改完跑 `python generate_narration.py --audit`，它會逐條檢查並印出正確值。

### D-4 🔧 畫布尺寸與置中
- **現象**：版面跑掉、字幕不置中、GSAP 動畫後元素歪掉。
- **原因**：畫布尺寸由根節點的 `data-width`／`data-height` 決定；CSS 寫死 `1920px` 或用 `translate(-50%)` 置中都會和框架或 GSAP 打架（C-3）。
- **教訓**：`#root` 寫 `width:100%; height:100%`；置中用 flex，或 `left:0; right:0; margin:0 auto; width:fit-content`（範本字幕的寫法）。

### D-5 🌍 畫面只能由時間決定（確定性）
- **現象**：每次算繪的粒子位置不同；或動畫在算繪結果裡完全不動。
- **原因**：HyperFrames 逐格撥動時間軸再截圖，沒有「實際經過的時間」。`Math.random()`、`Date.now()`、`setTimeout`、`requestAnimationFrame`、CSS transition 配 class 切換，都不受時間軸控制。
- **教訓**：亂數用固定種子（範本的 `mulberry32`）；所有動畫寫成 GSAP tween；無限循環改成有限次數 `repeat: Math.max(0, Math.floor(長度 / 週期) - 1)`（`max(0, …)` 不可省，算出 -1 會變成無限循環，lint 報 `gsap_repeat_floor_unclamped`）。

### D-6 🔧 外部樣式表在算繪時只剩 `@font-face`
- **現象**：預覽（`preview`／`snapshot`）正常，`render` 出來的 KaTeX 公式卻**重複顯示兩次**、字型跑掉。
- **原因**：算繪前 HyperFrames 會把非 Google Fonts 的 `<link rel="stylesheet">` 換成「只留 `@font-face` 的內嵌樣式」，排版規則全丟（KaTeX 用來隱藏 MathML 的那條也沒了）。改寫成 `<style>@import url(…)</style>` 也一樣，會先被轉回 `<link>`。
- **教訓**：這類樣式表改在執行期用 JS 載入，**載完才註冊時間軸**（02 範本檔尾的 `loadCss()`）。HyperFrames 支援非同步註冊，看到 `window.__timelines["main"]` 才開始擷取。只用 Google Fonts 的範本（01）不受影響。

### D-7 🔧 選擇器不能用 template literal 拼變數
- **現象**：lint 報 `template_literal_selector`（error）。
- **原因**：HyperFrames 的打包器解析 script 時，遇到 `` querySelector(`[data-step="${k}"]`) `` 會出錯。
- **教訓**：先用固定選擇器抓一批，再用 `.filter(el => +el.dataset.step === k)` 篩（範本的 `step()` 輔助函式）。

### D-8 🌍 `check` 才是出片前的關卡，`render` 不會替你擋缺檔
- **現象**：照片缺檔照樣算出一支 mp4，畫面上是空白色塊；或算了好幾分鐘才失敗。
- **原因**：`render` 遇到 404 的圖片不會中止；頁面 script 丟錯雖然會擋，但要等整支擷取完才報。
- **教訓**：流程固定為 `generate_narration.py`（稽核）→ **`npx --yes hyperframes@0.8.181 check` 必須顯示 `Check passed`** → `npx --yes hyperframes@0.8.181 render -o final.mp4`。`check` 會擋下：缺素材（404、`audio_src_not_found`）、分階動畫守衛（C-7）、交叉淡化時文字疊在一起（`content_overlap`）。

### D-9 🔧 範本會有的固定警告，可忽略
- `nested_structure_needs_subcomposition`、`composition_file_too_large`、`studio_missing_editable_id`：範本刻意把整支片寫在單一 `index.html`，方便 fork 與閱讀，不影響出片。
- `clip_media_fit`（旁白比頁面短）：頁尾本來就要留 2–4s 空白，這是設計。
- `Not inlining assets/fonts/*.otf (exceeds the 2 MB inline limit)`：字檔照常從專案資料夾載入。
- 淡入中途取樣到的對比度警告（例如 `1.65:1`）：元素還是半透明時被量到，淡入完成就正常。

### D-11 🌍 HyperFrames 發新版後，`npx --no-install hyperframes` 會直接失敗
- **現象**：前一天還能跑的 `npx --no-install hyperframes check`，突然報 `npx canceled due to missing packages and no YES option: ["hyperframes@0.8.172"]`；加 `--offline` 也一樣。
- **原因**：npx 每次都去查最新版，最新版不在快取裡就拒絕執行，即使快取裡有可用的舊版。
- **教訓**：本 repo 所有指令都寫成指定版本：`npx --yes hyperframes@0.8.181 <指令>`（環境檢查用 `npx --no-install hyperframes@0.8.181`，只看快取、不下載）。套件只會落在 npm 快取，不會在專案裡建 `node_modules`（仍符合 D-1）。
- **升級版本**：先在三支範本跑過 `check`／`render`，再用 `git grep -n <舊版本號>` 把文件、腳本、範本、`tools/` 裡的版本號一起改（`install/setup.py` 集中在 `HF` 常數；中文檔名要用 `git grep -lz … | xargs -0`，不然 specs 底下的檔會被漏掉）。驗證內容寫進 C 節開頭的「驗證版本」，舊版的實測陳述不要跟著改號。
- **不要改成 `@latest` 或全域安裝**：HyperFrames 一天發好幾版（0.8.171 → 0.8.181 只隔兩天），不鎖版本時同一支片前後可能用不同版本算繪，出問題分不清是自己改壞還是工具變了。有需要的修正或開新片前再照上一條升級。

### D-10 🌍 用 `snapshot` 逐頁目視驗收，`check` 抓不到排版問題
- **現象**：`check` 通過，但畫面上有：封面標題斷行後行尾懸著一個「・」、文氏圖標籤貼著數字、時間軸右端的「分」被切掉、卡片下半部大片留白。
- **原因**：`check` 只驗缺檔、時間軸、文字重疊與對比，不判斷「好不好看」。
- **教訓**：出片前對**每頁頁尾前約 1.6 秒**（動畫都跑完的時刻）拍一張：`npx --yes hyperframes@0.8.181 snapshot --at <秒數,…> --no-end --describe false -o <資料夾>`，看它產生的 contact sheet；可疑處再用 `--zoom "x,y,w,h"` 放大。全片 16 頁拍一輪約 1 分鐘，比算繪完才發現便宜得多。
- **同類元素放在一起比**：章節卡、標籤、圖說這類每頁都有的元素，把各頁的截圖並排看大小與位置是否一致，不一致就統一成同一個值（📎 實例：章節卡在不同頁分別是 6.8cqw 與 2.6cqw）。
- **單張異常先重拍再判斷**：0.8.181 實測過一次第一張拍成空白頁，重拍兩次都正常；同一個時間點連續兩次都異常才是真的問題。後來連兩輪都是第一張空白，所以 `--at` 的**第一個時間點放一個不需要驗的時刻**（或重複一次第二個），要驗的頁別排第一張。

### D-12 🌍 字型瘦身：出片前把字型切成片中用到的字
- **現象**：每頁都載入源石黑體三個字重，各約 15 MB；每個算繪用的 Chrome worker 都要各自載入一次，專案搬移、上傳也很重。
- **教訓**：所有文字都改完、`check` 之前，跑 `python tools/subset_fonts.py --project output/<主題>`：掃描 `index.html` 用到的字，在 `assets/fonts/` 寫出 `*.subset.woff2`，並把 `@font-face` 的 `url()` 與 `format()` 改指向瘦身版；之後改過任何字就重跑（它每次都從完整字型重切）；`--restore` 改回完整字型。
  - 02 範本實測：497 個字，三個字重各從約 15 MB 降到約 100 KB；`check` 通過，五個時間點的截圖和完整字型版**逐像素相同**。算繪速度沒有量過（原作者在快的電腦上量到沒有變快，好處主要是 worker 記憶體與檔案大小；0.8.175 起 HyperFrames 也會直接嵌入專案字型）。
  - **只能在 `output/<主題>/` 跑**：在 `examples/` 跑會把版控中的範本改成指向不在 git 裡的字檔，腳本會直接拒絕。
  - 需要 `pip install fonttools`（加裝 `brotli` 才會輸出 woff2，沒裝就維持 .otf）。

### D-13 🔧📎 翻牌卡的正反兩面被 `check` 判成文字重疊
- **現象**：正反兩面疊在同一個位置、用 `rotationY` 翻面，`check` 報文字重疊（error）。
- **教訓**：在**兩面各自的容器**上加 `data-layout-allow-overlap`；加在整頁的根元素上沒有用。

### D-14 🔧 放 `<video>` 時的三個規則（社群科普的影片素材、AI 生成片段）
- **沒有 `id`，算繪時會凍結成一張圖**：renderer 靠 id 找媒體，lint 報 `media_missing_id`（error），和 E-1 的 audio 同一條規則。
- **不能放在有計時的元素裡面**：背景圖層本身是 `class="clip"` 時，`<video>` 要放在它**後面（同層）**，放在裡面播放的畫面會錯；lint 報 `video_nested_in_timed_element`。
- **影片比那一頁短，播完會留下空框**：clip 播完就被隱藏（C-1），在影片結束前用 tween 把整張影片卡淡出。
- 影片一律 `muted`，聲音另開 `<audio>`（C-6）。以上兩條 lint 規則名稱已在 0.8.181 的套件裡確認存在；三條現象引自 📎 claude-motion-explainer。

---

## E. 音訊

### E-1 🌍 每個 `<audio>` 都要有 `id`
- **現象**：整支片無聲，畫面正常。
- **原因**：沒有 `id` 的 `<audio>` 會被 HyperFrames 的混音器略過（lint 報 `media_missing_id`）。
- **教訓**：旁白一律 `<audio id="nar-NN" src="assets/narration/page-NN.mp3" data-start data-duration>`，`generate_narration.py --audit` 會檢查 id、src、時段三者。不需要再預先串成 master.mp3，也不需要 ffmpeg mux。

### E-2 🌍 BGM 淡出與 ducking 用屬性，不要自己動 volume
- **現象**：音量忽大忽小，或淡出沒作用。
- **原因**：同一軌同時有 `volume` tween 與 `data-automation` 時，以 automation 為準，tween 被忽略（lint 報 `audio_volume_double_automation`）。
- **教訓**：頭尾淡入淡出用 `data-fade-in`／`data-fade-out`（秒）；旁白期間壓低 BGM 用 `data-automation` 的 volume lane（時間是**該軌自己的頁內秒數**），兩者擇一管理音量。

### E-3 🌍 缺 BGM 或照片時由 `check` 擋下
- **現象**：01 範本沒放 BGM、03 範本沒下載照片。
- **原因**：本 repo 不含 binary 素材。
- **教訓**：缺音檔時 lint 報 `audio_src_not_found`（error）；缺圖片時 runtime 報 `http_error: 404`（error）。兩者都會讓 `check` 失敗——這就是素材守衛，看到就去補素材，不要繞過（見 D-8）。

### E-4 🌍 `afade` 的 `ss` vs `st` 時間單位地雷（手動用 ffmpeg 剪音檔時）
- **現象**：背景音樂開頭播 5 秒就直接淡出無聲。
- **原因**：`afade` 的 `ss` 是「開始採樣點 Start Sample」，`st` 才是「開始時間（秒）」。誤用 `ss=45` ≈ 在第 0.0009 秒就開始淡出。
- **教訓**：淡入淡出開始點**必須用 `st`（秒）**：`afade=t=out:st=45:d=5`。能用 E-2 的屬性就不必手動處理。

### E-5 🪟 concat demuxer 無法讀中文路徑的 list.txt（手動用 ffmpeg 串音檔時）
- **現象**：`ffmpeg -f concat -i list.txt` 報 `No such file or directory`。
- **原因**：concat demuxer 內部檔案路徑含中文時 ffmpeg 無法解析。
- **教訓**：在 temp（純英文）目錄建所有暫存檔與 list.txt，concat 完再 `cp` 回 GDrive；或用 filter_complex concat。

### E-6 🌍 成片響度：一律正規化到 −15 LUFS
- **現象**：02 範本用 0.8.181 算繪出來是 −16.2 LUFS（真峰值 −3.4 dBTP），各支片之間音量不一致；media-short-film 的片當時又是另一個目標（−16），兩個 repo 做出來的片放在一起忽大忽小。
- **原因**：HyperFrames 不管整支片混音後的響度；它的 `normalize-audio` 只調單一音軌的 `data-volume`（預設 −16 LUFS），用來平衡旁白和 BGM，不是成片的響度。
- **教訓（規範）**：每支片 `render` 完都跑 `python tools/loudness.py output/<主題>/final.mp4 --apply` 再交片：整合響度 **−15 LUFS ±0.5**、真峰值 **≤ −1 dBTP**，只換音軌，視訊串流直接複製不重新編碼。不帶 `--apply` 只量測。02 範本實測：算繪原始 −16.2 LUFS → **−15.0 LUFS**、真峰值 −2.3 dBTP，一輪就達標，片長不變。
  - **要量編成 AAC 之後的真峰值**：AAC 編碼本身會把真峰值推高，只量編碼前的音檔會漏掉。工具每一輪都實際編成 AAC 再量，響度差就調增益、真峰值超標就壓低 4 倍超取樣限幅器的門檻，最多 8 輪（做法移植自 media-short-film 的 `make_film.py cut`）。8 輪還沒同時達標通常是某處爆音，聽一下再決定。
  - 旁白和 BGM 的相對音量仍照 E-2 處理；loudness.py 只管最後的整體響度。
  - **兩個影片 repo 統一 −15 LUFS**（2026-10-20 使用者決定）：media-short-film 的 `film.json` `target_lufs` 與 `make_film.py` 的預設也是 −15。YouTube 的播放基準是 −14，−15 會小聲約 1 dB，但給有配樂、音效、喊叫的片留了限幅餘裕。真峰值上限兩邊仍不同：本 repo −1 dBTP、media-short-film −1.2 dBTP。

---

## F. Windows / PowerShell / 編碼

### F-1 🪟 CP950 編碼導致 Python 崩潰
- **現象**：`UnicodeEncodeError` 崩潰，印不出 `✓` `❌` 等符號；或錯誤訊息變成亂碼。
- **原因**：Windows CMD/PowerShell 預設 CP950，無法解碼 Python 輸出的 UTF-8 特殊符號。`SystemExit("…")` 的訊息走 stderr，只改 stdout 不夠。
- **教訓**：設 `PYTHONUTF8=1`，或在腳本開頭把 `sys.stdout` **與** `sys.stderr` 都 `reconfigure(encoding="utf-8")`（範本與 `setup.py` 都這樣寫）；寫檔一律 `open(..., encoding="utf-8")`。

### F-2 🪟 `Copy-Item "中文路徑\*"` 靜默失敗
- **現象**：回報 "done" 但實際 0 檔案被複製。
- **原因**：PowerShell 處理含中文的路徑 + `*` 萬用字元時，擴充異常但不拋錯。
- **教訓**：用 `Get-ChildItem -LiteralPath $src | foreach { Copy-Item -LiteralPath $_.FullName -Destination $dst }` 逐檔處理；或改用 bash `cp`。

### F-3 🪟 PowerShell 變數內嵌路徑冒號衝突
- **現象**：`"$base\page-$p.mp3"` 或 `"$drive:\path"` 報「變數參考無效」。
- **原因**：PowerShell 把 `$p`/`$drive` 後的 `:` 當 scope 修飾字。
- **教訓**：用 `${p}` 明確界定變數範圍，或改用 `Join-Path`。

---

## G. Python

### G-1 🌍 `generate_narration.py` 相對路徑依賴 cwd
- **現象**：Edge-TTS 生成的 mp3 跑到上層目錄而非 `assets/narration/`。
- **原因**：`OUTPUT = "assets/narration"` 是相對 cwd 的路徑，不是相對 `.py` 檔位置。
- **教訓**：用 `os.path.join(os.path.dirname(__file__), 'assets/narration')`（或 `Path(__file__).parent`）。範例已這樣寫，改腳本時別退化。

---

## H. TTS

### H-1 🔧 HyperFrames 內建的 Kokoro TTS 是備案，不是預設
- **現象**：`npx --yes hyperframes@0.8.181 tts` 報 `The kokoro-onnx package is not installed`；或旁白口音不對。
- **原因**：Kokoro 跑在 Python，需要另外裝 `kokoro-onnx` 與 `soundfile`；中文只有 `zf_xiaobei` 一個聲音，是中國口音。
- **教訓**：預設用 Edge-TTS（台灣腔）。要用 Kokoro（免網路、免金鑰）時：`pip install kokoro-onnx soundfile`，或裝在獨立 venv 再設環境變數 `HYPERFRAMES_PYTHON` 指向那個 python；然後 `python generate_narration.py --tts kokoro`。第一次會下載約 27 MB 的聲音資料。
- **換引擎等於旁白長度全變**：同一份稿子，Kokoro 和 Edge-TTS 每頁長度差 1–3 秒，稽核常會報「旁白超出版面」。換完一定重看稽核表、重調 `data-duration`。旁白裡的英文詞（GPT-4、token）也要實際聽過。

### H-2 🌍 動畫對齊旁白：用 `WordBoundary` 拿逐詞時間，不要用估的
- **現象**：動畫照「大概第幾秒念到」排，數字已經亮起，旁白還沒念到（或反過來）。
- **教訓**：edge-tts 7.x 可以在串流時回傳每個詞的起始秒數：
  ```python
  c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary")
  async for ch in c.stream():
      if ch["type"] == "WordBoundary":
          print(ch["offset"] / 1e7, ch["text"])   # 秒數、詞
  ```
  印出每頁的「詞@秒數」清單，tween 就排在 `S(n) + 該詞秒數`。同一段文字、同一組聲音參數，合成結果是固定的，和實際生成的 mp3 對得上。
- **串流可能中途斷掉、只回傳一部分**：實測連跑 16 頁時有 2 頁只拿到前 2 個詞，沒有報錯。使用前先比對每頁的詞數與最後一個詞的秒數（應接近旁白長度），不對就重抓那幾頁。

### H-3 🌍 改語速或換聲音 = 整支時間軸重排
- **現象**：使用者說「加快到 1.25 倍」或「改女聲」，每頁旁白長度全變；只重跑 TTS，動畫就對不上字、頁尾不是太長就是太短。
- **教訓**：照這個順序處理：
  1. 換算語速：Edge-TTS 的 rate 是相對正常速度，`-10%` 的 1.25 倍 = 0.9 × 1.25 ≈ 1.13 → `+13%`。最好一開始就避免：教學片先問是新學（`-10%`、留白 2～4 秒）還是複習（`+35%`、留白 1～2 秒），國一複習片就是從 -10% 被要求加快了三次才定在 +35%。
  2. 重跑 `generate_narration.py`，用 ffprobe 量每頁新長度，頁長取 `ceil(旁白 + 2.2)`（tail 落在 2–4s）。
  3. 文字沒改的頁：頁內動畫秒數乘上「新旁白長 ÷ 舊旁白長」。範本寫法是 `const T = (n, t) => S(n) + t * SPD[n]`，把 `S(n) + 秒數` 全換成 `T(n, 秒數)`，只維護一張縮放表。改了文字的頁照 H-2 重拿逐詞時間。
  4. `--audit` → `check` → `snapshot` 逐頁看（D-10）。
- 換聲音也一樣：同一份稿子，女聲 HsiaoChen 比男聲 YunJhe 略長，02 範本換女聲後有 4 頁 tail 掉到 2 秒以下，要各加 1 秒。
- **換聲音時比語速縮放更準的做法**：同一段文字，兩種聲音的 `WordBoundary` 斷詞完全相同（實測 16 頁逐詞一致），把「舊聲音詞秒數 → 新聲音詞秒數」做成每頁一張對照表，`T(n, t)` 用分段線性內插換算，動畫就精確落在新聲音念到的字上，不必重排任何秒數。

### H-4 🌍 多音字、英文詞念錯：用讀音替換表改字，不要改旁白稿
- **現象**：「十比十一少一」的「少」被念成 shào（應為 3 聲 shǎo）；「奇數位」的「奇」被念成 qí（應為 1 聲 jī）；03 範本的「GPT-4」念法不自然。
- **原因**：Edge-TTS 不能用 SSML 指定讀音（`<phoneme>` 無效），只能從字面猜，多音字在數學語境常猜錯。
- **教訓**：維護讀音替換表 `tts-lexicon.md`（Markdown 表格 `| 原文 | 改寫 | 說明 |`）：`generate_narration.py` 產生旁白前自動把原文換成念得對的寫法（例：奇數 → 基數、GPT-4 → GPT four），**只改送進 TTS 的文字，字幕與 SCRIPT.md 照常寫正確用字**。
  - **表在本 repo 根目錄**（[tts-lexicon.md](tts-lexicon.md)，格式與規則寫在表的開頭）。腳本從影片資料夾往上找，專案在本 repo 的 `output/` 裡就會讀到它；**專案 fork 到 repo 以外的地方時，設環境變數 `TTS_LEXICON` 指向它**。找不到會印「找不到 tts-lexicon.md」，不做替換。
  - **四個 repo 各一份、內容逐位元組相同**：本 repo、[media-short-film](https://github.com/changyiwu/media-short-film)、[media-voice-clone](https://github.com/changyiwu/media-voice-clone)、[agent-speak](https://github.com/changyiwu/agent-speak)（`speak/`）。四個都公開，不能假設使用者每個都下載，所以各自要完整可用；放在同一層時腳本會**合併讀取**，同一個原文以本 repo 的為準。**改表時四份一起改**：改完任一份跑 `python ../media-short-film/tools/tts_lexicon.py --sync` 合併寫回四份，`--check` 只檢查。本機合併讀取時漏同步察覺不到，但只下載其中一個 repo 的人就會缺。（2026-10-20 曾把表只放在 media-short-film 當「主表」，結果單獨下載本 repo 的人完全沒有替換，連 03 範本自己的 GPT-4 都會念錯，所以改成每個 repo 各帶一份。）
  - 影片資料夾（或上層）放一份同名的 `tts-lexicon.md`（同樣的表格格式）就能加只對該片生效的條目，近的覆蓋遠的。對所有片都有用的條目加進 repo 根目錄的表。
  - **產生旁白前先預檢**：`python tools/polyphone_check.py --project output/<主題>` 會把旁白稿轉成簡體查 pypinyin（它的詞典收簡體詞，直接查繁體會把「長方形」猜成 zhǎng），標出兩種地方：讀音不是該字最常見讀法的詞（奇數的奇 jī、還原的還 huán），以及常錯清單裡的字、詞典沒收的詞（十一少一的少）。同一個詞只列一次、附頁碼，02 範本約 10 個詞。它列的讀音**不保證對**（實測「數一數」仍猜錯），是「產生旁白後該優先聽哪裡」的清單，不是自動判讀；「一」「不」的變調與輕聲不列。
  - 改寫優先用**同音字**（奇 → 基）；找不到同音字就加字讓語境變明確（少一 → 少了一）。條目寫得越具體越安全，避免誤換其他詞。
  - 使用者回報念錯時：先加條目、重跑那幾頁、實際聽過，再寫進表裡的說明欄。改字會改變旁白長度與逐詞時間，那幾頁的動畫要依新的 `WordBoundary` 重對（H-2）。

### H-5 🌍 片做完才發現念錯字：重念候選、用耳朵挑、整句等比伸縮換回去
- **現象**：H-4 的讀音替換表是事前預防；片已經算繪完才聽到某頁念錯（多音字、聲調、英文詞），整頁重跑 TTS 會讓旁白長度改變，那頁的動畫時間（H-2）要重對。
- **教訓**：用 `tools/fix_voice.py`，頁長與動畫都不必動：
  1. 在專案資料夾產生候選：`python generate_narration.py --page 3 --take A --rate=-5%`、`--take B --text "換了拼法的整句"`（同音字、加字讓語境明確，和 H-4 的改寫原則相同）。
  2. 試聽：`python tools/fix_voice.py --project output/<主題> audition --page 3 --clauses 1 2`，把念錯那個詞所在的子句（依標點切、從 0 起算）從「原本」與每個候選剪出來，串成一個檔。**用耳朵選**：ASR 抓得到念成別的詞，抓不到聲調錯。
  3. 套用：`… apply --page 3 --take B`。候選整句等比伸縮回原句的語音長度、補回原句開頭的靜音、音量對齊，覆蓋 `page-03.mp3`（原檔備份成 `fix/page-03.before-fix.mp3`，`restore` 還原）。接著用 Edge-TTS 重抓兩邊的逐詞時間，把候選換算成伸縮後的秒數逐詞比對，**差超過 0.2 秒的詞會列出來**，那幾個 tween 照 H-3 的 `T(n, t)` 修；沒列出就不用動。
  4. 定案的改寫加進讀音替換表（H-4），下次重跑整支旁白也念得對。
- **不要照停頓把候選切成子句再拼回去**：重念的停頓位置和原句不同，切點會落在字中間，結果漏字或重複（📎 實例）。整句等比伸縮在 ±5% 內聽不出來，超過 ±15% 工具會建議換一個候選。
- 實測（02 範本第 13 頁）：伸縮 0.951 倍，語音起訖和原句差不到 0.02 秒、總長與響度相同；改了一個詞的候選，逐詞比對自動略過不同的詞。

### H-6 🌍📎 旁白稿裡的數字寫國字，字幕照常寫阿拉伯數字
- **現象**：「0.81 秒」「1700 公斤」被念成逐位數字或念法不自然。
- **教訓**：`SCRIPT` 裡的數字寫成念法（零點八一秒、一千七百公斤），畫面與 `.subtitle` 照常寫阿拉伯數字。02 範本一直是這樣寫（「二十四個人」），這裡把它寫成規則。

### H-7 🌍 先試聽聲音與前兩頁，再產生整支旁白
- **現象**：整支旁白生成完、動畫也對好了，使用者才說聲音或語速不對，只好整支時間軸重排（H-3）。
- **教訓**：定稿後先只產生前兩頁給使用者聽（`python generate_narration.py --page 1 --take try` 會存到 `assets/narration/fix/cand/`，不會動到正式旁白），聲音、語速確認了再跑整支。片長估算：本 repo 的 Edge-TTS 旁白實測約 **每秒 3 個字**（語速 −8%～−10%、含標點停頓，02／03 範本），每頁再加 2～4 秒留白。

### H-8 🌍 edge-tts 要 7.3.1 以上，舊版會被微軟擋
- **現象**：`generate_narration.py` 一跑就失敗，edge-tts 回 `403`，同一台電腦前幾天還正常。
- **原因**：微軟改了服務端的驗證，edge-tts 7.2.8 以前的版本送出的請求會被拒；7.3.1 已跟上。`check_env.sh` 只檢查有沒有裝，不檢查版本。
- **教訓**：換電腦或隔一陣子再出片，先 `pip install -U edge-tts`（`pip show edge-tts` 要看到 7.3.1 以上）再產生旁白。

---

## 快速自檢（開工前 30 秒）

- [ ] 已先寫 SCRIPT.md 給使用者確認？（A-1）
- [ ] 問清楚學生學到第幾冊第幾章、新學還是複習（語速）、能不能暫停？（A-4 / A-5 / H-3）
- [ ] 已展示 DESIGN.md 視覺規範？（A-2 / A-3）
- [ ] 字幕單行 ≤ 25 字、不換行？（B-1）
- [ ] HyperFrames 用 `npx` 跑，沒在雲端硬碟的專案裡 `npm install`？（D-1）
- [ ] 專案內有 `assets/fonts/`，`@font-face` 不用 `../`？（D-2 / C-5）
- [ ] 每頁與每段旁白的 `data-start`／`data-duration` 寫在標籤上，`--audit` 通過？（D-3）
- [ ] 沒用 `Math.random`／`setTimeout`／CSS transition 做動畫？（D-5）
- [ ] 外部 CDN 樣式表改由 JS 載入、載完才註冊時間軸？（D-6）
- [ ] 每個 `<audio>` 都有 `id`？（E-1）
- [ ] 裝飾性的持續動畫標了 `data: 'ambient'`，教學 reveal 沒標？（C-7）
- [ ] `npx --yes hyperframes@0.8.181 check` 顯示 `Check passed` 才 `render`？（D-8）
- [ ] 用 `snapshot` 逐頁看過？SVG 資料點進場只用 opacity？（D-10 / C-8）
- [ ] 旁白裡的多音字、英文詞查過讀音替換表 `tts-lexicon.md`，念錯的已加條目？（H-4）
- [ ] 旁白稿的數字寫國字、字幕寫阿拉伯數字？先試聽前兩頁才產生整支？（H-6 / H-7）
- [ ] 所有文字定稿後才跑 `tools/subset_fonts.py`，改過字就重跑？（D-12）
- [ ] `render` 完跑了 `tools/loudness.py --apply`，成片 −15 LUFS？（E-6）
- [ ] Windows 設了 `PYTHONUTF8=1`？（F-1）
- [ ] Python 輸出路徑用 `__file__` 不靠 cwd？（G-1）

---

## 貢獻來源

本筆記彙整自多個 agent 實跑經驗：
- 流程類（A）、字幕（B）：跨 agent 共通教訓
- GSAP 時間軸（C）與 HyperFrames 算繪（D）：HyperFrames 框架規則 + 把三支範本從 Playwright 遷移到 HyperFrames 時的實測
- FFmpeg / Windows / Python：**Antigravity** 在 Windows 實跑時詳細記錄（含確切錯誤碼與修法）
- 標 📎 的條目、D-12 字型瘦身、H-5 修唸錯字：引自 [mathruffian-dot/claude-motion-explainer-video](https://github.com/mathruffian-dot/claude-motion-explainer-video) 的 `lessons.md` 與工具（MIT License），`tools/` 底下的對應腳本改寫成本 repo 的管線後實測
