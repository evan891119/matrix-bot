import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.reminders.time_utils import DATETIME_FORMAT, DEFAULT_TZ, format_utc_iso_to_local


USAGE = (
    "用法:\n"
    "!remind add YYYY-MM-DD HH:MM <內容>\n"
    "!remind add MM-DD HH:MM <內容>（預設今年）\n"
    "!remind add MM-DD HH <內容>（預設今年，分=00）\n"
    "!remind add HH <內容>（今天）\n"
    "!remind add HH:MM <內容>（今天）\n"
    "!remind list\n"
    "!remind cancel <id>\n"
    "!remind import\\n"
    "due_local,text,room_id(optional)"
)


def _normalize_today_due_local(time_token: str, tz_name: str) -> str:
    hour, minute = _parse_hour_minute(time_token)

    today = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")
    return f"{today} {hour:02d}:{minute:02d}"


def _parse_hour_minute(time_token: str) -> tuple[int, int]:
    if re.fullmatch(r"\d{1,2}", time_token):
        hour = int(time_token)
        minute = 0
    elif re.fullmatch(r"\d{1,2}:\d{2}", time_token):
        hour_str, minute_str = time_token.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
    else:
        raise ValueError("invalid time token")

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("invalid time range")
    return hour, minute


def _normalize_yearless_due_local(date_token: str, time_token: str, tz_name: str) -> str:
    if not re.fullmatch(r"\d{1,2}-\d{1,2}", date_token):
        raise ValueError("invalid date token")

    month_str, day_str = date_token.split("-")
    month = int(month_str)
    day = int(day_str)
    hour, minute = _parse_hour_minute(time_token)
    if month < 1 or month > 12:
        raise ValueError("invalid month")
    if day < 1 or day > 31:
        raise ValueError("invalid day")

    year = datetime.now(ZoneInfo(tz_name)).year
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"


async def handle_remind(bot, room_id: str, sender: str, body: str) -> None:
    if not bot.cfg.allow_todo_public and not bot._is_admin(sender):
        return

    parts = body.split(maxsplit=2)
    if len(parts) < 2:
        await bot._send_text(room_id, USAGE)
        return

    action = parts[1]
    default_tz = bot.cfg.timezone or DEFAULT_TZ

    if action == "add":
        payload = body[len("!remind add") :].strip()
        if not payload:
            await bot._send_text(
                room_id,
                f"格式錯誤，可用 {DATETIME_FORMAT}、MM-DD HH:MM、HH 或 HH:MM",
            )
            return
        try:
            tokens = payload.split()
            if len(tokens) < 2:
                await bot._send_text(room_id, "提醒內容不可為空")
                return

            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tokens[0]) and len(tokens) >= 3:
                due_local = f"{tokens[0]} {tokens[1]}"
                text = " ".join(tokens[2:]).strip()
            elif re.fullmatch(r"\d{1,2}-\d{1,2}", tokens[0]) and len(tokens) >= 3:
                due_local = _normalize_yearless_due_local(
                    tokens[0], tokens[1], default_tz
                )
                text = " ".join(tokens[2:]).strip()
            else:
                due_local = _normalize_today_due_local(tokens[0], default_tz)
                text = " ".join(tokens[1:]).strip()

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
        except ValueError:
            await bot._send_text(
                room_id,
                "提醒設定失敗：請確認時間格式正確，且必須是未來時間",
            )
            return
        except Exception:
            await bot._send_text(
                room_id,
                f"格式錯誤，可用 {DATETIME_FORMAT}、MM-DD HH:MM、HH 或 HH:MM",
            )
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
