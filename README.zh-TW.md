# course-search-bot

[English](README.md) · **繁體中文**

台灣大學課程查詢 Discord 機器人。共用一套資料格式，每所學校只需要一個 adapter。

## 關於本專案的開發方式

這個專案的程式碼、測試與文件幾乎都是由
[Claude Code](https://claude.com/claude-code) 產生的。
設計決策、程式碼審查與每一次變更的最終決定權都在作者手上 —
沒有讀過並理解的內容不會被合併 — 但請直接假設這裡的文字與實作出自模型之手。

這一點在 adapter 上特別重要。每個 adapter 在提交前都對實際資料來源驗證過
（所有 `時間` 字串、所有 `cos_time` 語法都實際跑過一遍），
integration 測試也能隨時重新驗證。請相信測試，而不是文字的語氣。

## 執行

```sh
uv sync
uv run pytest -q                       # 103 個測試
uv run pytest -q -m "not integration"  # 96 個，不需連網
uv run ruff check . && uv run ruff format --check .
DISCORD_TOKEN=... uv run bot.py        # /course 微積分
```

只有標記 `integration` 的測試會連到學校的實際資料來源，離線時會跳過而不是失敗。
其餘測試都跑在 `tests/data/` 裡的固定樣本上，每一筆都是為了某個實際存在的特殊格式而保留的。

## 檔案結構

| 檔案 | 維護者 | 是否與學校相關 |
|---|---|---|
| `schema.py` | 本專案 | 否 — 共用的資料格式 |
| `search.py` | 本專案 | 否 |
| `bot.py` | 本專案 | 否 |
| `conformance.py` | 本專案 | 否 — 格式檢查 |
| `adapters/*.py` | 貢獻者 | **是** — 唯一需要為各校客製的部分 |

## 資料來源

| 學校 | 來源 | 登入 | 形式 |
|---|---|---|---|
| 清大 | [`open_course_data.json`](https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/OPENDATA/open_course_data.json) | 不需要 | 官方每日更新，約 3.4 MB，一次請求 |
| 陽明交大 | [`timetable.nycu.edu.tw`](https://timetable.nycu.edu.tw/) | 不需要 | `?r=main/*` JSON，每個系所一次請求（約 257 次） |
| 成大 | [`nckuhub.com`](https://nckuhub.com/course/) | 不需要 | 第三方鏡像，一次請求 |

所有 adapter 都不會存取需要登入的頁面、不破解驗證碼、也不使用 proxy pool。
需要這些手段的 adapter 不適合放進這個專案。

成大官方課程查詢系統無法直接取用：每個查詢條件的值都是綁定 session 的加密字串，
查詢用的 JavaScript 經過混淆，流量一大還會出現驗證碼。NCKU HUB 在伺服器端爬取後
以公開 JSON 重新發布，因此本專案讀取的是 NCKU HUB。

三所學校都沒有提供可靠的選課人數：清大不公布，陽明交大在選課期間外回傳 `-999`，
NCKU HUB 的數字則新舊不一。因此 `capacity` 與 `enrolled` 一律為 `None`，
而不是給出會誤導人的數字。

## 新增一所學校

1. 複製 `adapters/nthu.py`，實作 `semesters()` 與 `courses(semester)`
2. 回傳 `Course` 物件 — 只能使用公開課程資料，絕不碰需要登入的頁面
3. 通過 `conformance.py` 裡的 `conforms()`

每所學校把資訊藏在不同的地方：清大藏在課號的字元位置裡，陽明交大擠在 `cos_time`
字串中，成大則是用中括號的星期節次語法，而且欄位裡還混著 HTML。
adapter 的工作就是把這些差異吸收掉，讓後面的程式完全不必知道。

## 資料使用與規範

程式碼採用 MIT 授權。**但課程資料不屬於本專案。**
資料屬於各校，成大的部分則屬於 NCKU HUB — 一個與學校無關的志工專案。

如果你要執行或 fork 這個專案：

- 只讀取公開端點，絕不以學生身分登入。
- 用排程爬取，不要在每次使用者查詢時才爬。陽明交大完整爬一次約 257 次請求，
  一天跑一次就好，不要每查一次就跑一次。
- 做快取。這些是學校的小型伺服器，不是 CDN。
- 不要把整批課程資料當成自己的東西重新發布。

## 佈署說明

`discord.py` 使用 gateway 連線，因此需要一個常駐的程序。
`schema.py`、`search.py` 與各個 adapter 都不依賴 Discord，
所以之後若要改用 HTTP interactions（serverless），只需要重寫 `bot.py`。
