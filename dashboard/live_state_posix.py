# -*- coding: utf-8 -*-
"""POSIX/macOS host sampler for Mac Studio themes.

Mirrors the portable fields used by dashboard/themes without spawning PowerShell.
Unavailable sensors stay None — never fabricate values.
"""

from __future__ import annotations

import datetime as dt
import socket
import time
from pathlib import Path

try:
    import psutil
except ImportError as exc:  # pragma: no cover
    raise SystemExit("psutil required: pip install -r requirements-mac.txt") from exc


class Sampler:
    """Sample CPU / memory / net / battery once per call."""

    def __init__(self):
        self.net = psutil.net_io_counters()
        self.tick = time.monotonic()
        psutil.cpu_percent(interval=None)

    def once(self) -> dict:
        now = dt.datetime.now()
        mem = psutil.virtual_memory()
        net, tick = psutil.net_io_counters(), time.monotonic()
        elapsed = max(0.01, tick - self.tick)
        down = max(0, net.bytes_recv - self.net.bytes_recv) * 8 / elapsed / 1e6
        up = max(0, net.bytes_sent - self.net.bytes_sent) * 8 / elapsed / 1e6
        self.net, self.tick = net, tick

        bat = psutil.sensors_battery()
        try:
            freq = psutil.cpu_freq()
        except (OSError, NotImplementedError, RuntimeError):
            freq = None

        ip = next(
            (
                a.address
                for name, values in psutil.net_if_addrs().items()
                if psutil.net_if_stats().get(name) and psutil.net_if_stats()[name].isup
                for a in values
                if a.family == socket.AF_INET and not a.address.startswith("127.")
            ),
            None,
        )

        cpu = float(psutil.cpu_percent(interval=0.15))
        mem_pct = float(mem.percent)
        bat_pct = float(bat.percent) if bat else None

        return {
            "timestamp": now.isoformat(timespec="seconds"),
            "time": now.strftime("%H:%M:%S"),
            "clock": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "host": socket.gethostname(),
            "ip": ip,
            "cpu": cpu,
            "cpu_percent": cpu,
            "cpu_load": cpu,
            "cpu_freq_ghz": (freq.current / 1000.0) if freq and freq.current else None,
            "mem_percent": mem_pct,
            "memory_percent": mem_pct,
            "mem_pct": mem_pct,
            "mem_used_gb": mem.used / 2**30,
            "mem_total_gb": mem.total / 2**30,
            "disk_free_gb": psutil.disk_usage(str(Path.home().anchor)).free / 2**30,
            "net_down_mbps": down,
            "net_up_mbps": up,
            "battery_percent": bat_pct,
            "bat_pct": bat_pct,
            "bat_ac": bat.power_plugged if bat else None,
            "bat_charging": bool(bat and bat.power_plugged and bat.percent is not None and bat.percent < 100),
        }

    def read(self) -> dict:
        return self.once()
