"""Threshold evaluation for alerting."""

from __future__ import annotations

from .config import Thresholds
from .metrics import Sample


def evaluate(sample: Sample, thresholds: Thresholds) -> list[str]:
    """Return human-readable alert lines for every breached threshold."""
    alerts: list[str] = []
    if sample.cpu > thresholds.cpu:
        alerts.append(f"CPU usage {sample.cpu:.0f}% > {thresholds.cpu:.0f}%")
    if sample.mem > thresholds.mem:
        alerts.append(f"RAM usage {sample.mem:.0f}% > {thresholds.mem:.0f}%")
    if sample.disk > thresholds.disk:
        alerts.append(f"Disk usage {sample.disk:.0f}% > {thresholds.disk:.0f}%")
    return alerts
