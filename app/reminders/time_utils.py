from datetime import datetime, timezone
from zoneinfo import ZoneInfo


DEFAULT_TZ = "Asia/Taipei"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def parse_local_to_utc_iso(local_dt_str: str, tz_name: str = DEFAULT_TZ) -> str:
    dt_local = datetime.strptime(local_dt_str.strip(), DATETIME_FORMAT)
    dt_local = dt_local.replace(tzinfo=ZoneInfo(tz_name))
    return dt_local.astimezone(timezone.utc).isoformat()


def format_utc_iso_to_local(utc_iso: str, tz_name: str = DEFAULT_TZ) -> str:
    dt_utc = datetime.fromisoformat(utc_iso)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(ZoneInfo(tz_name))
    return dt_local.strftime(DATETIME_FORMAT)
