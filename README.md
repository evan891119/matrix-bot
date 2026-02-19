# Matrix Python Client Bot (matrix-nio)

可用於雲端 server 的 Docker 化 Matrix bot，支援 E2EE（加密房間可解密與回覆）。

**重點提醒**
- 請務必掛載 `STORE_PATH` 的 volume，刪掉會導致 E2EE 金鑰遺失。
- 加密房間首次使用時，需要在 Element 端信任 bot 裝置或重新分享房間金鑰。

## 功能
- 高負載監控與告警（CPU/RAM/Disk/Loadavg，支援節流與恢復通知）
- `!status` 顯示狀態（僅 ADMIN_USERS）
- `!todo` / `!note` 私人待辦與筆記（預設僅 ADMIN_USERS）
- `!remind` 提醒事項（SQLite 持久化 + 定時自動發送）
- 自動接受邀請（僅限 invited_by 為 ADMIN_USERS）

## 專案結構
- `app/bot.py`
- `app/storage.py`
- `app/monitor.py`
- `app/config.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`

## 環境需求
- Python 3.11+
- Docker & docker-compose

## 快速開始（Docker）
1. 編輯 `docker-compose.yml` 中的環境變數。
2. 啟動：
```bash
docker compose up -d --build
```
3. 確保 bot 加入房間（邀請需由 ADMIN_USERS 發出）。

## 環境變數
至少需設定以下項目：
- `HOMESERVER_URL` 例如 `https://matrix.example.com`
- `BOT_USER_ID` 例如 `@mybot:example.com`
- `BOT_PASSWORD`
- `STORE_PATH`（E2EE store，請掛 volume）
- `ALLOWED_ROOMS`（room_id 白名單，逗號分隔）
- `ADMIN_USERS`（user_id 白名單，逗號分隔）
- `DEVICE_NAME`

可選：
- `ALERT_ROOM_ID` 告警固定房間，未設定則使用 `ALLOWED_ROOMS` 第一個
- `MONITOR_INTERVAL_SEC` 預設 30
- `ALERT_COOLDOWN_MIN` 預設 10
- `CPU_THRESHOLD` 預設 85
- `CPU_CONSECUTIVE` 預設 2
- `RAM_THRESHOLD` 預設 90
- `DISK_THRESHOLD` 預設 90
- `LOADAVG_THRESHOLD` 預設 2.0
- `LOADAVG_AUTO_PER_CORE` 預設 true
- `ALLOW_TODO_PUBLIC` 預設 false
- `TIMEZONE` 預設 Asia/Taipei
- `DATA_PATH`（SQLite 位置，請掛 volume）
- `POLL_INTERVAL_SECONDS`（提醒輪詢秒數，預設 `20`）
- `BOT_ACCESS_TOKEN`（使用 access token 免密登入）
- `BOT_DEVICE_ID`（搭配 access token）
- `CONFIG_YAML`（可選，指定 config.yaml 路徑）

## config.yaml（可選）
```yaml
HOMESERVER_URL: "https://matrix.example.com"
BOT_USER_ID: "@mybot:example.com"
BOT_PASSWORD: "CHANGE_ME"
STORE_PATH: "/data/store"
DATA_PATH: "/data/db"
ALLOWED_ROOMS: "!roomid1:example.com,!roomid2:example.com"
ADMIN_USERS: "@admin:example.com"
DEVICE_NAME: "matrix-bot"
```

## 指令
- `!status`（僅 ADMIN_USERS）
- `!todo add <文字>`
- `!todo list`
- `!todo done <id>`
- `!todo del <id>`
- `!note <文字>`
- `!note list [n]`
- `!note search <keyword>`
- `!remind add YYYY-MM-DD HH:MM <內容>`
- `!remind add MM-DD HH:MM <內容>`（預設今年）
- `!remind add HH <內容>`（預設今天）
- `!remind add HH:MM <內容>`（預設今天）
- `!remind list`
- `!remind cancel <id>`
- `!remind import`（同一則訊息貼上 CSV）

提醒功能細節請見 `docs/reminders.md`。

## E2EE 使用與注意事項
1. 第一次讓 bot 加入加密房間後：
   - 請在 Element 中找到 bot 裝置並 **信任**，或
   - 在該房間中 **重新分享金鑰** 給 bot。
2. `STORE_PATH` 一定要掛 volume，重啟後才能解密歷史訊息。
3. 若換新裝置或刪掉 store，必須重新分享金鑰。
4. 若加密房間無法回覆，請確認 log 是否有顯示 `device_id`，並在 Element 對應裝置信任/驗證。
5. `sync_forever()` 會自動處理 `keys_upload()`，不需要手動呼叫，避免 store 尚未載入時發生錯誤。

## 加密房間注意事項（常見問題）
- 若 bot 無法解密，請確認：
  - `STORE_PATH` volume 是否持久化
  - Element 是否已信任 bot 裝置
  - 是否已重新分享房間金鑰

## 本地開發
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m app.bot
```
