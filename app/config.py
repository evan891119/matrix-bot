import os
from dataclasses import dataclass
from typing import List, Optional
import yaml


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Config:
    homeserver_url: str
    bot_user_id: str
    bot_password: Optional[str]
    bot_access_token: Optional[str]
    bot_device_id: Optional[str]
    store_path: str
    allowed_rooms: List[str]
    admin_users: List[str]
    device_name: str
    alert_room_id: Optional[str]
    monitor_interval_sec: int
    alert_cooldown_min: int
    cpu_threshold: int
    cpu_consecutive: int
    ram_threshold: int
    disk_threshold: int
    loadavg_threshold: float
    loadavg_auto_per_core: bool
    allow_todo_public: bool
    timezone: str
    data_path: str


def load_config() -> Config:
    yaml_path = os.getenv("CONFIG_YAML", "").strip()
    data = {}
    if yaml_path and os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    def get(key: str, default=None):
        return os.getenv(key, data.get(key, default))

    allowed_rooms = _split_csv(get("ALLOWED_ROOMS", ""))
    admin_users = _split_csv(get("ADMIN_USERS", ""))

    return Config(
        homeserver_url=get("HOMESERVER_URL", ""),
        bot_user_id=get("BOT_USER_ID", ""),
        bot_password=get("BOT_PASSWORD"),
        bot_access_token=get("BOT_ACCESS_TOKEN"),
        bot_device_id=get("BOT_DEVICE_ID"),
        store_path=get("STORE_PATH", "./store"),
        allowed_rooms=allowed_rooms,
        admin_users=admin_users,
        device_name=get("DEVICE_NAME", "matrix-bot"),
        alert_room_id=get("ALERT_ROOM_ID"),
        monitor_interval_sec=int(get("MONITOR_INTERVAL_SEC", 30)),
        alert_cooldown_min=int(get("ALERT_COOLDOWN_MIN", 10)),
        cpu_threshold=int(get("CPU_THRESHOLD", 85)),
        cpu_consecutive=int(get("CPU_CONSECUTIVE", 2)),
        ram_threshold=int(get("RAM_THRESHOLD", 90)),
        disk_threshold=int(get("DISK_THRESHOLD", 90)),
        loadavg_threshold=float(get("LOADAVG_THRESHOLD", 2.0)),
        loadavg_auto_per_core=str(get("LOADAVG_AUTO_PER_CORE", "true")).lower()
        in ("1", "true", "yes", "y"),
        allow_todo_public=str(get("ALLOW_TODO_PUBLIC", "false")).lower()
        in ("1", "true", "yes", "y"),
        timezone=get("TIMEZONE", "Asia/Taipei"),
        data_path=get("DATA_PATH", "./data"),
    )
