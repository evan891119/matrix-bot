from app.reminders.time_utils import DATETIME_FORMAT, DEFAULT_TZ, format_utc_iso_to_local


USAGE = (
    "用法:\n"
    "!remind add YYYY-MM-DD HH:MM <內容>\n"
    "!remind list\n"
    "!remind cancel <id>\n"
    "!remind import\\n"
    "due_local,text,room_id(optional)"
)


async def handle_remind(bot, room_id: str, sender: str, body: str) -> None:
    if not bot.cfg.allow_todo_public and not bot._is_admin(sender):
        return

    parts = body.split(maxsplit=4)
    if len(parts) < 2:
        await bot._send_text(room_id, USAGE)
        return

    action = parts[1]
    default_tz = bot.cfg.timezone or DEFAULT_TZ

    if action == "add":
        if len(parts) < 5:
            await bot._send_text(room_id, f"格式錯誤，時間格式需為 {DATETIME_FORMAT}")
            return
        try:
            due_local = f"{parts[2]} {parts[3]}"
            text = parts[4].strip()
            if not text:
                await bot._send_text(room_id, "提醒內容不可為空")
                return
            reminder_id = await bot.reminder_service.add_reminder(
                user_id=sender,
                room_id=room_id,
                text=text,
                due_local=due_local,
                tz_name=default_tz,
            )
            await bot._send_text(room_id, f"已新增提醒 #{reminder_id}")
            return
        except Exception:
            await bot._send_text(room_id, f"格式錯誤，時間格式需為 {DATETIME_FORMAT}")
            return

    if action == "list":
        rows = await bot.reminder_service.list_reminders(user_id=sender)
        if not rows:
            await bot._send_text(room_id, "目前沒有待提醒事項")
            return
        lines = ["提醒清單:"]
        for row in rows:
            due_local = format_utc_iso_to_local(row["due_at_utc"], row["tz"])
            lines.append(f"#{row['id']} {due_local} {row['tz']} {row['text']}")
        await bot._send_text(room_id, "\n".join(lines))
        return

    if action == "cancel":
        if len(parts) < 3:
            await bot._send_text(room_id, "用法: !remind cancel <id>")
            return
        try:
            reminder_id = int(parts[2])
        except ValueError:
            await bot._send_text(room_id, "提醒 id 必須是數字")
            return
        ok = await bot.reminder_service.cancel_reminder(
            reminder_id=reminder_id, user_id=sender
        )
        await bot._send_text(room_id, "已取消" if ok else "找不到可取消的提醒")
        return

    if action == "import":
        csv_text = body[len("!remind import") :].strip()
        if not csv_text:
            await bot._send_text(
                room_id,
                "請在同一則訊息貼上 CSV 內容，例如:\n"
                "due_local,text,room_id\n"
                "2026-02-20 09:00,繳月費,!abc:example.com\n"
                "2026-02-20 12:30,開會\n",
            )
            return
        result = await bot.reminder_service.import_csv_text(
            user_id=sender,
            default_room_id=room_id,
            csv_text=csv_text,
            tz_name=default_tz,
        )
        await bot._send_text(
            room_id,
            f"匯入完成：成功 {result['ok']} 筆，失敗 {result['failed']} 筆",
        )
        return

    await bot._send_text(room_id, USAGE)
