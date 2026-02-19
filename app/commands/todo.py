import time


def _now_ms() -> int:
    return int(time.time() * 1000)


async def handle_todo(bot, room_id: str, sender: str, body: str) -> None:
    if not bot.cfg.allow_todo_public and not bot._is_admin(sender):
        return
    parts = body.split(maxsplit=2)
    if len(parts) < 2:
        await bot._send_text(room_id, "用法: !todo add|list|done|del ...")
        return

    action = parts[1]
    if action == "add" and len(parts) >= 3:
        todo_id = await bot.storage.todo_add(parts[2], _now_ms())
        await bot._send_text(room_id, f"已新增 Todo #{todo_id}")
        return
    if action == "list":
        items = await bot.storage.todo_list()
        if not items:
            await bot._send_text(room_id, "Todo 清單為空")
            return
        lines = ["Todo 清單:"]
        for tid, text, done in items:
            mark = "✅" if done else "⬜"
            lines.append(f"{mark} #{tid} {text}")
        await bot._send_text(room_id, "\n".join(lines))
        return
    if action == "done" and len(parts) >= 3:
        try:
            todo_id = int(parts[2])
        except ValueError:
            await bot._send_text(room_id, "Todo id 必須是數字")
            return
        ok = await bot.storage.todo_done(todo_id, _now_ms())
        await bot._send_text(room_id, "完成" if ok else "找不到或已完成")
        return
    if action == "del" and len(parts) >= 3:
        try:
            todo_id = int(parts[2])
        except ValueError:
            await bot._send_text(room_id, "Todo id 必須是數字")
            return
        ok = await bot.storage.todo_del(todo_id)
        await bot._send_text(room_id, "已刪除" if ok else "找不到")
        return

    await bot._send_text(room_id, "用法: !todo add|list|done|del ...")
