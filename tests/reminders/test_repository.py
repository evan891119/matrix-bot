import tempfile
import unittest

try:
    from app.reminders.repository import ReminderRepository
except ModuleNotFoundError:
    ReminderRepository = None


@unittest.skipIf(ReminderRepository is None, "aiosqlite not installed in test environment")
class ReminderRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = f"{self.tmpdir.name}/reminders.db"
        self.repo = ReminderRepository(self.db_path)
        await self.repo.init()

    async def asyncTearDown(self) -> None:
        self.tmpdir.cleanup()

    async def test_claim_changes_pending_to_sending_and_prevents_duplicate(self) -> None:
        reminder_id = await self.repo.add(
            user_id="@alice:example.com",
            room_id="!room:example.com",
            text="test reminder",
            due_at_utc="2026-02-20T01:00:00+00:00",
            tz="Asia/Taipei",
            created_at_utc="2026-02-19T00:00:00+00:00",
        )

        first = await self.repo.claim_due("2026-02-20T01:00:00+00:00", limit=10)
        second = await self.repo.claim_due("2026-02-20T01:00:00+00:00", limit=10)

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["id"], reminder_id)
        self.assertEqual(second, [])
