import os
import aiosqlite
from typing import List, Optional, Tuple


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS todo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    done_at INTEGER
                );
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS note (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    room_id TEXT NOT NULL
                );
                """
            )
            await db.commit()

    async def todo_add(self, text: str, created_at: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO todo (text, created_at, done) VALUES (?, ?, 0)",
                (text, created_at),
            )
            await db.commit()
            return cur.lastrowid

    async def todo_list(self) -> List[Tuple[int, str, int]]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT id, text, done FROM todo ORDER BY id ASC"
            )
            return await cur.fetchall()

    async def todo_done(self, todo_id: int, done_at: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE todo SET done=1, done_at=? WHERE id=? AND done=0",
                (done_at, todo_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def todo_del(self, todo_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("DELETE FROM todo WHERE id=?", (todo_id,))
            await db.commit()
            return cur.rowcount > 0

    async def note_add(self, text: str, created_at: int, sender: str, room_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO note (text, created_at, sender, room_id) VALUES (?, ?, ?, ?)",
                (text, created_at, sender, room_id),
            )
            await db.commit()
            return cur.lastrowid

    async def note_list(self, limit: int = 10) -> List[Tuple[int, str, int, str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT id, text, created_at, sender, room_id FROM note ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return await cur.fetchall()

    async def note_search(self, keyword: str, limit: int = 20) -> List[Tuple[int, str, int, str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT id, text, created_at, sender, room_id FROM note WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{keyword}%", limit),
            )
            return await cur.fetchall()
