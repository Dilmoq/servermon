"""Tests for threshold evaluation and sample formatting."""

import datetime as dt

from servermon.alerting import evaluate
from servermon.cli import format_uptime
from servermon.config import Thresholds
from servermon.metrics import Sample


def make_sample(cpu=10.0, mem=40.0, swap=0.0, disk=55.0) -> Sample:
    return Sample(
        ts=dt.datetime(2026, 10, 16, 12, 0).isoformat(),
        cpu=cpu,
        mem=mem,
        swap=swap,
        disk=disk,
        load1=1.25,
        uptime_s=86400,
    )


DEFAULT = Thresholds(cpu=90.0, mem=85.0, disk=90.0)


class TestEvaluate:
    def test_healthy_sample_has_no_alerts(self):
        assert evaluate(make_sample(), DEFAULT) == []

    def test_cpu_breach(self):
        alerts = evaluate(make_sample(cpu=95.0), DEFAULT)
        assert len(alerts) == 1
        assert "CPU" in alerts[0]

    def test_mem_breach(self):
        alerts = evaluate(make_sample(mem=99.0), DEFAULT)
        assert len(alerts) == 1
        assert "RAM" in alerts[0]

    def test_disk_breach(self):
        alerts = evaluate(make_sample(disk=97.0), DEFAULT)
        assert len(alerts) == 1
        assert "Disk" in alerts[0]

    def test_all_at_once(self):
        alerts = evaluate(make_sample(cpu=95.0, mem=99.0, disk=97.0), DEFAULT)
        assert len(alerts) == 3

    def test_exact_threshold_is_not_breach(self):
        assert evaluate(make_sample(cpu=90.0, mem=85.0, disk=90.0), DEFAULT) == []


class TestFormatUptime:
    def test_minutes_only(self):
        assert format_uptime(59) == "0h 00m"

    def test_hours(self):
        assert format_uptime(3600 * 2 + 180) == "2h 03m"

    def test_days(self):
        assert format_uptime(86400 + 3600 * 3 + 60 * 5) == "1d 03h 05m"
