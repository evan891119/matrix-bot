import asyncio
import json
import os
import time
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

import aiohttp
from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    JoinError,
    LoginResponse,
    MatrixRoom,
    RoomMessageText,
    SyncResponse,
)

from app.commands import handle_note, handle_status, handle_todo
from app.config import load_config
from app.monitor import Monitor, MonitorConfig
from app.storage import Storage


AUTH_FILE = "auth.json"
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("matrix-bot")
logging.getLogger("nio").setLevel(logging.WARNING)
logging.getLogger("nio.rooms").setLevel(logging.WARNING)


def now_ms() -> int:
    return int(time.time() * 1000)


class MatrixBot:
    def __init__(self):
        self.cfg = load_config()
        self.started_ms = now_ms()
        self.tz = ZoneInfo(self.cfg.timezone)
        self.last_sync_ms: Optional[int] = None

        self._ensure_writable_dir(
            self.cfg.store_path,
            "STORE_PATH 不可寫入，請在 docker-compose.yml 掛 volume 並修正權限。",
        )
        self._ensure_writable_dir(
            self.cfg.data_path,
            "DATA_PATH 不可寫入，請在 docker-compose.yml 掛 volume 並修正權限。",
        )

        self.auth_path = os.path.join(self.cfg.store_path, AUTH_FILE)
        self.auth = self._load_auth()

        client_config = AsyncClientConfig(
            encryption_enabled=False,
            store_sync_tokens=True,
        )

        self.client = AsyncClient(
            self.cfg.homeserver_url,
            self.cfg.bot_user_id,
            store_path=self.cfg.store_path,
            config=client_config,
        )
        self.client.user_agent = f"matrix-bot ({self.cfg.bot_user_id})"
        logger.info("STORE_PATH=%s", self.cfg.store_path)

        self.storage = Storage(os.path.join(self.cfg.data_path, "bot.db"))
        self.monitor = Monitor(
            MonitorConfig(
                interval_sec=self.cfg.monitor_interval_sec,
                alert_cooldown_min=self.cfg.alert_cooldown_min,
                cpu_threshold=self.cfg.cpu_threshold,
                cpu_consecutive=self.cfg.cpu_consecutive,
                ram_threshold=self.cfg.ram_threshold,
                disk_threshold=self.cfg.disk_threshold,
                loadavg_threshold=self.cfg.loadavg_threshold,
                loadavg_auto_per_core=self.cfg.loadavg_auto_per_core,
            )
        )

    def _ensure_writable_dir(self, path: str, error_message: str) -> None:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".write_test")
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_file)
        except Exception as exc:
            raise RuntimeError(error_message) from exc

    def _load_auth(self) -> dict:
        if os.path.exists(self.auth_path):
            try:
                with open(self.auth_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_auth(self) -> None:
        with open(self.auth_path, "w", encoding="utf-8") as f:
            json.dump(self.auth, f)

    def _is_admin(self, user_id: str) -> bool:
        return user_id in self.cfg.admin_users

    def _room_allowed(self, room_id: str) -> bool:
        return room_id in self.cfg.allowed_rooms

    def _format_ts(self, ms: int) -> str:
        dt = datetime.fromtimestamp(ms / 1000, tz=self.tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    async def _health_check(self) -> str:
        url = self.cfg.homeserver_url.rstrip("/") + "/_matrix/client/versions"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        return "OK"
                    return f"HTTP {resp.status}"
        except Exception:
            return "FAILED"

    async def _send_text(self, room_id: str, message: str) -> None:
        try:
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message},
            )
        except Exception:
            logger.exception("Failed to send message to %s", room_id)

    async def _send_markdown(self, room_id: str, message: str) -> None:
        await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": message},
        )

    async def _handle_invite(self, room: MatrixRoom, event: InviteMemberEvent) -> None:
        try:
            if not self._is_admin(event.sender):
                logger.info("Ignore invite from non-admin: %s", event.sender)
                return
            resp = await self.client.join(room.room_id)
            if isinstance(resp, JoinError):
                logger.error("Join failed: %s", resp)
            else:
                logger.info("Joined room %s (full room_id)", room.room_id)
        except Exception:
            logger.exception("Invite handler error")

    async def _handle_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        try:
            if event.sender == self.client.user_id:
                return
            if event.server_timestamp < self.started_ms:
                return
            if not self._room_allowed(room.room_id):
                return
            if getattr(room, "encrypted", False):
                return

            body = event.body.strip()
            if body.startswith("!status"):
                if not self._is_admin(event.sender):
                    return
                await handle_status(self, room.room_id)
                return
            if body.startswith("!ping"):
                await self._send_text(room.room_id, "pong")
                return

            if body.startswith("!todo"):
                await handle_todo(self, room.room_id, event.sender, body)
                return

            if body.startswith("!note"):
                await handle_note(self, room.room_id, event.sender, body)
                return
        except Exception:
            logger.exception("Message handler error in room %s", room.room_id)

    async def _monitor_loop(self) -> None:
        while True:
            try:
                metrics = self.monitor.collect()
                alert_msg, recovery_msg = self.monitor.evaluate(metrics)
                room_id = self.cfg.alert_room_id or (
                    self.cfg.allowed_rooms[0] if self.cfg.allowed_rooms else None
                )
                if room_id:
                    if alert_msg:
                        await self._send_text(room_id, alert_msg)
                    if recovery_msg:
                        await self._send_text(room_id, recovery_msg)
                await asyncio.sleep(self.cfg.monitor_interval_sec)
            except Exception:
                logger.exception("Monitor loop error")
                await asyncio.sleep(self.cfg.monitor_interval_sec)

    async def _login(self) -> None:
        if self.cfg.bot_access_token:
            self.client.access_token = self.cfg.bot_access_token
            if not self.cfg.bot_device_id:
                raise RuntimeError("BOT_DEVICE_ID is required when using BOT_ACCESS_TOKEN")
            self.client.device_id = self.cfg.bot_device_id
            self.client.user_id = self.cfg.bot_user_id
            self.client.restore_login(
                user_id=self.cfg.bot_user_id,
                device_id=self.client.device_id,
                access_token=self.client.access_token,
            )
            logger.info("Login via access token")
            return

        if self.auth.get("access_token") and self.auth.get("device_id"):
            self.client.access_token = self.auth.get("access_token")
            self.client.device_id = self.auth.get("device_id")
            self.client.user_id = self.cfg.bot_user_id
            self.client.restore_login(
                user_id=self.cfg.bot_user_id,
                device_id=self.client.device_id,
                access_token=self.client.access_token,
            )
            logger.info("Login via stored access token")
            return

        if not self.cfg.bot_password:
            raise RuntimeError("BOT_PASSWORD or BOT_ACCESS_TOKEN is required")

        resp = await self.client.login(
            password=self.cfg.bot_password, device_name=self.cfg.device_name
        )
        if isinstance(resp, LoginResponse):
            self.auth["access_token"] = resp.access_token
            self.auth["device_id"] = resp.device_id
            self._save_auth()
            logger.info("Login success, device_id=%s", resp.device_id)
        else:
            raise RuntimeError(f"Login failed: {resp}")

    async def _register_handlers(self) -> None:
        self.client.add_event_callback(self._handle_message, RoomMessageText)
        self.client.add_event_callback(self._handle_invite, InviteMemberEvent)
        async def on_sync(resp: SyncResponse):
            self.last_sync_ms = now_ms()

        self.client.add_response_callback(on_sync, SyncResponse)

    async def run(self) -> None:
        await self.storage.init()
        await self._login()
        await self._register_handlers()
        logger.info(
            "Bot started. User=%s Device=%s Rooms=%d",
            self.client.user_id,
            self.client.device_id,
            len(self.client.rooms),
        )
        asyncio.create_task(self._monitor_loop())
        await self.client.sync_forever(timeout=30000, full_state=True)


async def main():
    bot = MatrixBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
