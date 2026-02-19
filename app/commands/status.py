import time

import psutil


async def handle_status(bot, room_id: str) -> None:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    load1, load5, load15 = psutil.getloadavg()
    uptime = time.time() - psutil.boot_time()
    health = await bot._health_check()
    last_sync = bot._format_ts(bot.last_sync_ms) if bot.last_sync_ms else "unknown"
    msg = (
        "狀態資訊:\n"
        f"CPU: {cpu:.1f}%\n"
        f"RAM: {mem:.1f}%\n"
        f"Disk: {disk:.1f}%\n"
        f"Loadavg: {load1:.2f} {load5:.2f} {load15:.2f}\n"
        f"Uptime: {uptime/3600:.1f} hours\n"
        f"Matrix health: {health}\n"
        f"Last sync: {last_sync}"
    )
    await bot._send_text(room_id, msg)
