# 審片循環

你看不了影片，但看得了畫面。**沒有看過「目前這一版」的 contact sheet，不要回報影片完成。**
畫面或時間有任何修改、以及宣告影片完成之前，都跑一輪。為什麼要這樣做見 [GOTCHAS D-10](../GOTCHAS.md)。

> 改編自 [whaleyxbt/claude-motion](https://github.com/whaleyxbt/claude-motion) 的 `review-loop` skill（MIT），
> 經 [mathruffian-dot/claude-motion-explainer-video](https://github.com/mathruffian-dot/claude-motion-explainer-video) 改寫成 HyperFrames 版（MIT）；
> 兩者的授權全文在 [LICENSE](../LICENSE) 的 THIRD-PARTY CODE 段。本版把流程接上本 repo 的工具，標示「（本版新增）」的是兩個上游都沒有的內容。

下面的指令在 repo 根目錄執行；`npx` 那幾行在影片專案資料夾內執行。需要 ffmpeg 和 Pillow。

## 循環

0. **機器檢查**：`npx --yes hyperframes@0.8.181 check` 必須顯示 `Check passed`（GOTCHAS D-8），有錯先修。
1. **草稿**：`npx --yes hyperframes@0.8.181 render --quality draft -o renders/draft.mp4`。
2. **Contact sheet**：`python tools/sheet.py --project output/<主題>`。
   它用 `tools/review_times.py` 算時間點：每個旁白子句結束前 0.15 秒，加上每頁頁尾前 1.6 秒（動畫都跑完的時刻），太近的略過；4×2 拼成 `.hyperframes/review/draft-N.png`，`draft-table.txt` 列出每格對應哪句旁白。沒有逐頁旁白的片（01）只截每頁落定時刻。
3. **每一張 sheet 都打開來看**（用你讀圖片檔的工具），逐項對照下面的檢查表。只看檔名或 log 不算看過。
4. **可疑的地方放大看**：
   - 掃一段轉場：`python tools/sheet.py --project output/<主題> --from 3 --to 5 --every 0.2 --name scrub`
   - 看特定時刻：`… --at 3.7,3.75,3.8 --name exact`
   - 看局部細節：`npx --yes hyperframes@0.8.181 snapshot --at 3.7 --zoom "x,y,w,h" --no-end --describe false -o <資料夾>`
5. **修正後回到第 0 步**。只改了幾頁的排版時，可以先不重算草稿：`python tools/review_times.py --project output/<主題> --pages` 給每頁落定時刻，用 `snapshot --at <秒數,…>` 拍（D-10）；動到時間或動畫，就要回到第 1 步。完整跑一輪都沒有發現問題才停。
6. **定稿**：`npx --yes hyperframes@0.8.181 render -o final.mp4`，再 `python tools/loudness.py output/<主題>/final.mp4 --apply`（GOTCHAS E-6）。對成片再跑一次第 2 步（`--video` 指向成片），做聲音檢查。

## 檢查表

對旁白（本版新增）
- 對照 `draft-table.txt`：這句念完時，它講的東西畫面上已經出現，下一句的東西還沒搶先出現（H-2）。
- 數字在念到之後 0.5 秒內落定（C-11）。

構圖
- 每格只有一個焦點。兩個東西搶戲時，其中一個要等。
- 沒有非刻意的碰撞或重疊，特別是轉場時，退場和進場的元素共用同一塊空間。
- 安全區：重要內容不要離邊緣不到約 60 px。
- 第 0 格是真正的畫面，不是黑的（社群平台的縮圖、規範 8.4 的封面都從這裡來）。
- 同類元素（章節卡、標籤、圖說）各頁大小與位置一致（D-10）。
- 座標上的標記沒有偏移（C-8）。

文字
- 沒有被遮罩、容器或畫面邊緣切到（除非是刻意的）。
- 縮成手機寬度（sheet 的格子）時，關鍵訊息仍然讀得清楚。
- 該被閱讀的時候，文字沒有在動。
- 中文：沒有錯字；全部是繁體字形；標點用全形；沒有缺字（方框或明顯不同的字體）。
- 字幕單行、不超過 25 字（B-1）；依教材做的片，畫面和字幕沒有提「課本」（本版新增）。

節奏
- 每個要讓人讀的狀態都停得夠久。停留中段的格子裡文字還在動，就代表停留太短。
- 場景之間是重疊銜接，不是切到空白畫面（C-1）。
- 退場比進場快。

一致性
- 只用 DESIGN.md 色票裡的顏色；強調色標的就是這一格的重點。
- 同一個元素在每個出現的場景裡看起來都一樣。

聲音（只在定稿時）
- 波形：`ffmpeg -v error -i <成片> -filter_complex "showwavespic=s=1600x240" -frames:v 1 wave.png`，打開圖片看峰值有沒有落在節拍上。
- 響度：`python tools/loudness.py <成片>` 只量測，目標 −15 LUFS ±0.5、真峰值 ≤ −1 dBTP（E-6）。
- 中文旁白的口音和情緒，請使用者用耳朵聽，不要拿分數代替。

## 回報

完成時說清楚：檢查了什麼、修了什麼、哪一張 sheet 看得到結果。沒有重新輸出並親眼看過的修正，不要宣稱已經修好。
