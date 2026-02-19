import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.reminders.service import ReminderService


class _DummyRepository:
    async def init(self) -> None:
        return None

    async def add(self, **kwargs) -> int:
        return 1


class ReminderServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_add_reminder_rejects_past_time(self) -> None:
        service = ReminderService(
            repository=_DummyRepository(),
            poll_interval_seconds=20,
            default_tz="Asia/Taipei",
        )
        now_local = datetime.now(ZoneInfo("Asia/Taipei"))
        past_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        due_local = past_local.strftime("%Y-%m-%d %H:%M")

        with self.assertRaisesRegex(ValueError, "提醒時間早於目前時間"):
            await service.add_reminder(
                user_id="@alice:example.com",
                room_id="!room:example.com",
                text="past",
                due_local=due_local,
                tz_name="Asia/Taipei",
            )
