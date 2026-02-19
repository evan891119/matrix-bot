import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional

from app.reminders.time_utils import (
    DATETIME_FORMAT,
    DEFAULT_TZ,
    format_utc_iso_to_local,
    now_utc_iso,
    parse_local_to_utc_iso,
)


logger = logging.getLogger("matrix-bot.reminder")

if TYPE_CHECKING:
    from app.reminders.repository import ReminderRepository


class ReminderService:
    def __init__(
        self,
        *,
        repository: "ReminderRepository",
        poll_interval_seconds: int = 20,
        default_tz: str = DEFAULT_TZ,
    ):
        self.repository = repository
        self.poll_interval_seconds = poll_interval_seconds
        self.default_tz = default_tz or DEFAULT_TZ

    async def init(self) -> None:
        await self.repository.init()

    async def add_reminder(
        self,
        *,
        user_id: str,
        room_id: str,
        text: str,
        due_local: str,
        tz_name: Optional[str] = None,
    ) -> int:
        tz = tz_name or self.default_tz
        try:
            due_at_utc = parse_local_to_utc_iso(due_local, tz)
        except ValueError:
            raise ValueError(
                f"時間格式錯誤，請使用 {DATETIME_FORMAT}、MM-DD HH:MM、HH 或 HH:MM"
            ) from None

        due_dt_utc = datetime.fromisoformat(due_at_utc)
        now_dt_utc = datetime.now(timezone.utc)
        if due_dt_utc <= now_dt_utc:
            raise ValueError("提醒時間早於目前時間，請設定未來時間")

        return await self.repository.add(
            user_id=user_id,
            room_id=room_id,
            text=text.strip(),
            due_at_utc=due_at_utc,
            tz=tz,
            created_at_utc=now_utc_iso(),
        )

    async def list_reminders(self, *, user_id: str) -> List[Dict]:
        return await self.repository.list_active_for_user(user_id)

    async def cancel_reminder(self, *, reminder_id: int, user_id: str) -> bool:
        return await self.repository.cancel(reminder_id, user_id)

    async def import_csv_text(
        self,
        *,
        user_id: str,
        default_room_id: str,
        csv_text: str,
        tz_name: Optional[str] = None,
    ) -> Dict[str, int]:
        tz = tz_name or self.default_tz
        reader = csv.reader(io.StringIO(csv_text))
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
        if not rows:
            return {"ok": 0, "failed": 0}

        start_idx = 0
        first = ",".join(rows[0]).lower().replace(" ", "")
        if first.startswith("due_local,text"):
            start_idx = 1

        ok = 0
        failed = 0
        for row in rows[start_idx:]:
            parts = [p.strip() for p in row]
            if len(parts) < 2:
                failed += 1
                continue
            due_local = parts[0]
            text = parts[1]
            room_id = parts[2] if len(parts) >= 3 and parts[2] else default_room_id
            if not text:
                failed += 1
                continue
            try:
                await self.add_reminder(
                    user_id=user_id,
                    room_id=room_id,
                    text=text,
                    due_local=due_local,
                    tz_name=tz,
                )
                ok += 1
            except Exception:
                failed += 1
        return {"ok": ok, "failed": failed}

    async def run_loop(self, send_text_callable) -> None:
        while True:
            try:
                await self.dispatch_due(send_text_callable)
            except Exception:
                logger.exception("Reminder loop error")
            await asyncio.sleep(self.poll_interval_seconds)

    async def dispatch_due(self, send_text_callable) -> None:
        due_items = await self.repository.claim_due(now_utc_iso(), limit=20)
        for item in due_items:
            reminder_id = item["id"]
            try:
                due_local = format_utc_iso_to_local(item["due_at_utc"], item["tz"])
                msg = f"⏰ 提醒：{item['text']}（原訂時間：{due_local} {item['tz']}）"
                await send_text_callable(item["room_id"], msg)
                await self.repository.mark_done(reminder_id, now_utc_iso())
            except Exception:
                logger.exception("Reminder send failed id=%s", reminder_id)
                await self.repository.mark_pending(reminder_id)
