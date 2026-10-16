"""Metric collection built on psutil."""

from __future__ import annotations

import dataclasses
import datetime as dt
import typing

import psutil


@dataclasses.dataclass(frozen=True)
class Sample:
    """A single metrics sample."""

    ts: str
    cpu: float  # percent, 0..100
    mem: float  # percent, 0..100
    swap: float  # percent, 0..100
    disk: float  # root filesystem usage percent, 0..100
    load1: float | None  # 1-minute load average (None on platforms without it)
    uptime_s: int  # seconds since boot

    def as_dict(self) -> dict[str, typing.Any]:
        return dataclasses.asdict(self)


def disk_percent() -> float:
    """Root-mount disk usage in percent (works on Windows and Linux)."""
    # On Windows "C:\\" behaves like "/" here; "/" is used on POSIX systems.
    target = "/" if psutil.POSIX else "C:\\"
    return typing.cast(float, psutil.disk_usage(target).percent)


def load_avg1() -> float | None:
    """1-minute load average, or None where the OS does not provide it."""
    if getattr(psutil, "getloadavg", None) is None:
        return None
    try:
        return round(psutil.getloadavg()[0], 2)
    except (OSError, NotImplementedError):
        return None


def collect() -> Sample:
    """Take one metrics sample of the local machine."""
    load1 = load_avg1()
    return Sample(
        ts=dt.datetime.now().replace(microsecond=0).isoformat(),
        cpu=psutil.cpu_percent(interval=0.2),
        mem=psutil.virtual_memory().percent,
        swap=psutil.swap_memory().percent,
        disk=round(disk_percent(), 1),
        load1=load1,
        uptime_s=int(dt.datetime.now().timestamp() - psutil.boot_time()),
    )


def top_processes(limit: int = 5) -> list[tuple[int, str, float, float]]:
    """Top `limit` processes by CPU as (pid, name, cpu_percent, mem_percent)."""
    procs: list[tuple[int, str, float, float]] = []
    for p in psutil.process_iter(["pid", "name"]):
        with p.oneshot():
            try:
                pinfo = p.as_dict(attrs=["pid", "name", "cpu_percent", "memory_percent"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.append(
            (pinfo["pid"], pinfo["name"] or "?", pinfo["cpu_percent"], pinfo["memory_percent"])
        )
    procs.sort(key=lambda item: item[2], reverse=True)
    return procs[:limit]
