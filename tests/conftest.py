"""Shared pytest fixtures for servermon tests."""

import sys
from pathlib import Path

# Make `src/servermon` importable without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest


@pytest.fixture()
def sample_factory():
    """Factory to build Sample objects with custom fields."""
    import datetime as dt

    from servermon.metrics import Sample

    def _make(**overrides) -> Sample:
        defaults = {
            "ts": dt.datetime(2026, 10, 16, 12, 0, 0).isoformat(),
            "cpu": 10.0,
            "mem": 40.0,
            "swap": 0.0,
            "disk": 55.0,
            "load1": None,
            "uptime_s": 100,
        }
        defaults.update(overrides)
        return Sample(**defaults)

    return _make
