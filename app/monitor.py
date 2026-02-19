import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import psutil


@dataclass
class MonitorConfig:
    interval_sec: int
    alert_cooldown_min: int
    cpu_threshold: int
    cpu_consecutive: int
    ram_threshold: int
    disk_threshold: int
    loadavg_threshold: float
    loadavg_auto_per_core: bool


class Monitor:
    def __init__(self, cfg: MonitorConfig):
        self.cfg = cfg
        self.last_alert: Dict[str, float] = {}
        self.cpu_high_count = 0

    def _cooldown_ok(self, key: str) -> bool:
        last = self.last_alert.get(key, 0)
        return (time.time() - last) >= (self.cfg.alert_cooldown_min * 60)

    def _mark_alert(self, key: str) -> None:
        self.last_alert[key] = time.time()

    def collect(self) -> Dict[str, float]:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        load1, load5, load15 = psutil.getloadavg()
        return {
            "cpu": cpu,
            "mem": mem,
            "disk": disk,
            "load1": load1,
            "load5": load5,
            "load15": load15,
        }

    def evaluate(self, metrics: Dict[str, float]) -> Tuple[Optional[str], Optional[str]]:
        alerts = []
        recoveries = []

        cpu = metrics["cpu"]
        if cpu > self.cfg.cpu_threshold:
            self.cpu_high_count += 1
        else:
            if self.cpu_high_count >= self.cfg.cpu_consecutive:
                recoveries.append("CPU")
            self.cpu_high_count = 0

        if self.cpu_high_count >= self.cfg.cpu_consecutive and self._cooldown_ok("cpu"):
            alerts.append(f"CPU > {self.cfg.cpu_threshold}% 連續 {self.cfg.cpu_consecutive} 次")
            self._mark_alert("cpu")

        mem = metrics["mem"]
        if mem > self.cfg.ram_threshold and self._cooldown_ok("mem"):
            alerts.append(f"RAM > {self.cfg.ram_threshold}%")
            self._mark_alert("mem")
        elif mem <= self.cfg.ram_threshold and self.last_alert.get("mem"):
            recoveries.append("RAM")
            self.last_alert.pop("mem", None)

        disk = metrics["disk"]
        if disk > self.cfg.disk_threshold and self._cooldown_ok("disk"):
            alerts.append(f"Disk > {self.cfg.disk_threshold}%")
            self._mark_alert("disk")
        elif disk <= self.cfg.disk_threshold and self.last_alert.get("disk"):
            recoveries.append("Disk")
            self.last_alert.pop("disk", None)

        load1 = metrics["load1"]
        cores = psutil.cpu_count(logical=True) or 1
        load_threshold = (
            self.cfg.loadavg_threshold * cores
            if self.cfg.loadavg_auto_per_core
            else self.cfg.loadavg_threshold
        )
        if load1 > load_threshold and self._cooldown_ok("load"):
            alerts.append(f"Loadavg(1m) > {load_threshold:.2f}")
            self._mark_alert("load")
        elif load1 <= load_threshold and self.last_alert.get("load"):
            recoveries.append("Loadavg")
            self.last_alert.pop("load", None)

        alert_msg = None
        recovery_msg = None
        if alerts:
            alert_msg = "⚠️ 高負載告警: " + " / ".join(alerts)
        if recoveries:
            recovery_msg = "✅ 恢復: " + " / ".join(recoveries)
        return alert_msg, recovery_msg
