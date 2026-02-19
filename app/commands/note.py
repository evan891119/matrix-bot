import time


def _now_ms() -> int:
    return int(time.time() * 1000)


async def handle_note(bot, room_id: str, sender: str, body: str) -> None:
    if not bot.cfg.allow_todo_public and not bot._is_admin(sender):
        return
    parts = body.split(maxsplit=2)
    if len(parts) < 2:
        await bot._send_text(
            room_id, "用法: !note <文字> | !note list [n] | !note search <keyword>"
        )
        return

    sub = parts[1]
    if sub == "list":
        n = 10
        if len(parts) >= 3:
            try:
                n = int(parts[2])
            except ValueError:
                n = 10
        rows = await bot.storage.note_list(n)
        if not rows:
            await bot._send_text(room_id, "沒有筆記")
            return
        lines = ["最近筆記:"]
        for nid, text, created_at, sender_id, rid in rows:
            ts = bot._format_ts(created_at)
            lines.append(f"#{nid} {ts} {sender_id}: {text}")
        await bot._send_text(room_id, "\n".join(lines))
        return

    if sub == "search" and len(parts) >= 3:
        keyword = parts[2]
        rows = await bot.storage.note_search(keyword)
        if not rows:
            await bot._send_text(room_id, "找不到")
            return
        lines = ["搜尋結果:"]
        for nid, text, created_at, sender_id, rid in rows:
            ts = bot._format_ts(created_at)
            lines.append(f"#{nid} {ts} {sender_id}: {text}")
        await bot._send_text(room_id, "\n".join(lines))
        return

    text = body[len("!note") :].strip()
    if text:
        note_id = await bot.storage.note_add(text, _now_ms(), sender, room_id)
        await bot._send_text(room_id, f"已新增 Note #{note_id}")
        return

    await bot._send_text(
        room_id, "用法: !note <文字> | !note list [n] | !note search <keyword>"
    )
