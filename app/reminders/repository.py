import os
from typing import Dict, List, Optional

import aiosqlite


class ReminderRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    due_at_utc TEXT NOT NULL,
                    tz TEXT NOT NULL DEFAULT 'Asia/Taipei',
                    status TEXT NOT NULL DEFAULT 'pending',
                    repeat_rule TEXT,
                    created_at_utc TEXT NOT NULL,
                    sent_at_utc TEXT
                );
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reminders_status_due
                ON reminders(status, due_at_utc);
                """
            )
            await db.commit()

    async def add(
        self,
        *,
        user_id: str,
        room_id: str,
        text: str,
        due_at_utc: str,
        tz: str,
        created_at_utc: str,
        repeat_rule: Optional[str] = None,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO reminders (
                    user_id, room_id, text, due_at_utc, tz, status, repeat_rule, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (user_id, room_id, text, due_at_utc, tz, repeat_rule, created_at_utc),
            )
            await db.commit()
            return cur.lastrowid

    async def list_active_for_user(self, user_id: str) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT id, room_id, text, due_at_utc, tz, status
                FROM reminders
                WHERE user_id = ?
                  AND status IN ('pending', 'sending')
                ORDER BY due_at_utc ASC, id ASC
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

    async def cancel(self, reminder_id: int, user_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                UPDATE reminders
                SET status = 'cancelled'
                WHERE id = ?
                  AND user_id = ?
                  AND status IN ('pending', 'sending')
                """,
                (reminder_id, user_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def claim_due(self, now_utc: str, limit: int = 20) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute(
                """
                SELECT id, user_id, room_id, text, due_at_utc, tz
                FROM reminders
                WHERE status = 'pending'
                  AND due_at_utc <= ?
                ORDER BY due_at_utc ASC, id ASC
                LIMIT ?
                """,
                (now_utc, limit),
            )
            rows = await cur.fetchall()
            reminder_ids = [row["id"] for row in rows]
            if reminder_ids:
                placeholders = ",".join("?" for _ in reminder_ids)
                await db.execute(
                    f"UPDATE reminders SET status = 'sending' WHERE id IN ({placeholders})",
                    reminder_ids,
                )
            await db.commit()
            return [dict(row) for row in rows]

    async def mark_done(self, reminder_id: int, sent_at_utc: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE reminders
                SET status = 'done',
                    sent_at_utc = ?
                WHERE id = ?
                  AND status = 'sending'
                """,
                (sent_at_utc, reminder_id),
            )
            await db.commit()

    async def mark_pending(self, reminder_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE reminders
                SET status = 'pending'
                WHERE id = ?
                  AND status = 'sending'
                """,
                (reminder_id,),
            )
            await db.commit()
