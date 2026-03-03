# AGENTS.md

本文件是這個 repo 的 AI agent 執行手冊。目標是讓進入專案的 agent 能快速理解架構、修改邊界、驗證方式與高風險操作，避免對 Matrix/E2EE/SQLite 狀態做出破壞性變更。

## 專案定位

- 這是基於 `matrix-nio` 的 Python Matrix bot。
- 主要功能包含 `!status`、`!todo`、`!note`、`!remind`。
- Bot 同時執行訊息事件處理、系統監控告警、提醒輪詢派送。
- 預設部署方式是 Docker / `docker compose`。
- 專案依賴本地 volume 持久化保存登入狀態、E2EE store 與 SQLite 資料。

## 先看哪裡

- `README.md`
  專案總覽、環境變數、Docker 啟動方式、指令列表。
- `app/bot.py`
  主入口。負責 config 載入、Matrix client 建立、事件分派、背景 task 啟動。
- `app/config.py`
  環境變數與 `CONFIG_YAML` 載入規則。env 優先於 yaml。
- `app/storage.py`
  Todo / Note 的 SQLite 儲存層。
- `app/monitor.py`
  CPU/RAM/Disk/Loadavg 監控與告警節流、恢復邏輯。
- `app/commands/status.py`
  `!status` 指令。
- `app/commands/todo.py`
  `!todo` 指令。
- `app/commands/note.py`
  `!note` 指令。
- `app/reminders/commands.py`
  `!remind` 指令解析、用法訊息、輸入格式正規化。
- `app/reminders/service.py`
  提醒建立、CSV 匯入、到期派送流程。
- `app/reminders/repository.py`
  reminders 資料表 schema 與 `pending -> sending -> done/pending` 狀態轉移。
- `app/reminders/time_utils.py`
  本地時間與 UTC 轉換。
- `docs/reminders.md`
  提醒功能規格補充。
- `tests/reminders/`
  目前已有的測試主要集中在 reminders 子系統。

## 架構摘要

### 指令處理流

1. Matrix 訊息從 `MatrixBot._handle_message()` 進入。
2. Bot 會先過濾自己發出的訊息、啟動前舊訊息、未允許房間與加密房間。
3. 再依前綴分派到 `!status`、`!todo`、`!note`、`!remind` 對應 handler。
4. 指令 handler 再呼叫 `Storage` 或 `ReminderService`。

### 提醒派送流

1. `ReminderService.run_loop()` 依 `POLL_INTERVAL_SECONDS` 輪詢。
2. `ReminderRepository.claim_due()` 先把到期 `pending` 提醒改成 `sending`。
3. 發送成功後 `mark_done()`。
4. 發送失敗後 `mark_pending()`，等待下次重試。

修改提醒功能時，必須維持這個 claim/send/ack 語意，避免重送、漏送或卡死在 `sending`。

## 執行與設定規則

- 目標 Python 版本是 3.11+。
- `Dockerfile` 使用 `python:3.11-slim`。
- 本地 shell 不一定有 `python`，這個 repo 的實際環境至少可能只有 `python3`。執行前先確認可用的 Python 指令。
- 相依套件定義在 `requirements.txt`。
- Bot 可使用密碼登入，也可用 `BOT_ACCESS_TOKEN` + `BOT_DEVICE_ID`。
- `CONFIG_YAML` 是可選設定來源，但環境變數優先。

### 核心環境變數

- `HOMESERVER_URL`
- `BOT_USER_ID`
- `BOT_PASSWORD`
- `BOT_ACCESS_TOKEN`
- `BOT_DEVICE_ID`
- `STORE_PATH`
- `DATA_PATH`
- `ALLOWED_ROOMS`
- `ADMIN_USERS`
- `TIMEZONE`
- `POLL_INTERVAL_SECONDS`

## 持久化與高風險操作

以下內容視為硬規則：

- 這個專案位於 GitHub public repo，任何修改都應預設為可能公開。
- 不要把密碼、token、API key、個資、隱私內容或其他敏感資訊寫入受 Git 追蹤的檔案。
- 若任務需要建立含敏感資訊的本地檔案，必須先確認該檔案不會被 Git 追蹤；必要時加入 `.gitignore`，但不應以提交敏感資訊為代價完成任務。
- 文件、範例設定與測試資料應使用 placeholder 或假資料，不要填入真實憑證、真實帳號或私密內容。
- 不要刪除、覆寫或隨意重建 `STORE_PATH` 內容。
  這裡包含登入持久化狀態與 E2EE 相關資料，遺失後可能需要重新登入、重新信任裝置、重新分享房間金鑰。
- `auth.json` 位於 store 目錄下，屬於登入持久化狀態。
- 不要刪除 `DATA_PATH` 內的 SQLite 檔案，除非任務明確要求做資料重建。
- Todo / Note 資料存在 `DATA_PATH/bot.db`。
- 提醒資料存在 `DATA_PATH/reminders.db`。
- 若修改 SQLite schema，必須同步考慮相容性。這個 repo 目前沒有正式 migration framework。
- 若修改提醒狀態欄位或派送流程，必須確認 `pending`、`sending`、`done`、`cancelled` 的行為仍一致。

## 修改指引

### 改指令行為時

- 改 `!todo` / `!note`：優先看 `app/commands/` 與 `app/storage.py`。
- 改 `!remind` 語法或錯誤訊息：優先看 `app/reminders/commands.py`。
- 改提醒資料模型、匯入、派送：看 `app/reminders/service.py` 與 `app/reminders/repository.py`。
- 改系統監控或告警閾值：看 `app/monitor.py` 與 `app/config.py`。
- 改房間白名單、管理者權限、訊息過濾：看 `app/bot.py`。

### 修改時的實務原則

- 維持現有 async 寫法與模組邊界。
- 新功能若需要持久化，優先沿用 SQLite 與既有 repository/service 分層。
- 若修改使用者可見指令、設定名稱或行為，應同步更新 `README.md` 與相關 `docs/*.md`。
- 沒有必要時，不要把簡單邏輯抽象成新的框架層。

## 測試與驗證

### 目前測試現況

- 現有測試主要覆蓋 reminders 子系統。
- 推薦優先執行：

```bash
python3 -m unittest tests.reminders.test_time_utils tests.reminders.test_service tests.reminders.test_repository
```

- 若直接跑：

```bash
python3 -m unittest
```

  在未安裝完整相依時，可能因 `app.commands.status` 匯入 `psutil` 失敗。這屬於環境缺依賴，不一定代表功能回歸。

### 本地啟動

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 -m app.bot
```

### Docker 啟動

```bash
docker compose up -d --build
```

## Matrix 與 E2EE 注意事項

- 這個 repo 的 README 已明確要求 `STORE_PATH` 必須掛 volume，這不是可選最佳化，而是功能前提。
- Bot 第一次進入加密房間後，通常需要在 Element 端信任 bot 裝置或重新分享房間金鑰。
- `ALLOWED_ROOMS` 與 `ADMIN_USERS` 是安全邊界，修改時應視為敏感變更。
- `app/bot.py` 目前對 encrypted room 有顯式跳過邏輯。若任務要改這段，先完整確認預期行為與 E2EE 支援策略，再動手修改。

## 建議工作流程

1. 先讀 `README.md`，再讀對應模組，不要只靠檔名猜行為。
2. 動到指令前先確認使用者可見語法與錯誤訊息。
3. 動到資料層前先確認 schema、狀態轉移與持久化位置。
4. 以最小變更完成任務，再跑最相關的測試。
5. 回報時說清楚改了哪些模組、怎麼驗證、還有哪些未覆蓋風險。

## 不要假設存在的東西

以下流程目前在 repo 中不存在，除非使用者要求新增，否則不要假設它們已存在：

- `Makefile`
- `pytest` 設定檔
- `ruff` / `black` / `mypy` 設定
- CI workflow
- 資料庫 migration 工具
- 額外的 worker/service 拆分

## 文件一致性要求

若任務改動以下內容，請同步更新文件：

- 指令語法或權限行為
- 環境變數名稱或預設值
- Docker 啟動方式
- reminders 功能規格

至少檢查：

- `README.md`
- `docs/reminders.md`
