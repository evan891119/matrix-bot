# Reminders / TODO (MVP)

## 功能
- 新增提醒：`!remind add YYYY-MM-DD HH:MM <內容>`
- 新增提醒：`!remind add MM-DD HH:MM <內容>`（預設今年）
- 新增提醒：`!remind add HH <內容>`（預設今天）
- 新增提醒：`!remind add HH:MM <內容>`（預設今天）
- 查詢提醒：`!remind list`
- 取消提醒：`!remind cancel <id>`
- 匯入提醒：`!remind import` + 同訊息貼上 CSV 內容
- 若時間早於目前時間，會拒絕建立並提示錯誤

## SQLite
- 路徑：`DATA_PATH/reminders.db`（預設 `./data/reminders.db`）
- table：`reminders`
- 欄位：
  - `id` INTEGER PRIMARY KEY AUTOINCREMENT
  - `user_id` TEXT
  - `room_id` TEXT
  - `text` TEXT
  - `due_at_utc` TEXT（ISO8601 UTC）
  - `tz` TEXT（預設 `Asia/Taipei`）
  - `status` TEXT（`pending/sending/done/cancelled`）
  - `repeat_rule` TEXT NULL
  - `created_at_utc` TEXT
  - `sent_at_utc` TEXT NULL
- index：`(status, due_at_utc)`

## Polling
- 背景 task 每 `POLL_INTERVAL_SECONDS`（預設 20 秒）輪詢
- 流程：
  1. claim 到期且 `pending` 的提醒並標記成 `sending`
  2. 發送 `m.room.message` 純文字
  3. 成功標記 `done` + `sent_at_utc`
  4. 失敗還原為 `pending`，下次重試

## 匯入格式（CSV）
- 欄位：`due_local,text,room_id(optional)`
- `due_local` 格式：`YYYY-MM-DD HH:MM`
- `room_id` 未填時，使用觸發指令的房間
- 可有 header，也可無 header

範例：
```csv
due_local,text,room_id
2026-02-20 09:00,繳月費,!abc:example.com
2026-02-20 12:30,開會
```

## 訊息格式
- `⏰ 提醒：<text>（原訂時間：YYYY-MM-DD HH:MM <tz>）`

## 相關環境變數
- `TIMEZONE`：預設解析時區（預設 `Asia/Taipei`）
- `POLL_INTERVAL_SECONDS`：提醒輪詢秒數（預設 `20`）
