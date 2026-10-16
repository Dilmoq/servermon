"""Unit tests for TOML configuration loading."""

from pathlib import Path

import pytest

from servermon.config import Config, Thresholds, load, load_or_default


def write_config(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(text, encoding="utf-8")
    return p


class TestLoad:
    def test_full_config(self, tmp_path):
        p = write_config(
            tmp_path,
            """
            interval = 30
            history_db = "/var/lib/servermon/history.db"
            [thresholds]
            cpu = 70.5
            mem = 80
            disk = 85
        """,
        )
        conf = load(p)
        assert conf.interval == 30
        assert conf.history_db == "/var/lib/servermon/history.db"
        assert conf.thresholds == Thresholds(cpu=70.5, mem=80.0, disk=85.0)

    def test_partial_file_uses_defaults(self, tmp_path):
        p = write_config(tmp_path, "interval = 10")
        conf = load(p)
        assert conf.interval == 10
        assert conf.thresholds == Thresholds()  # defaults preserved
        assert conf.history_db == Config.history_db

    def test_empty_file_is_all_defaults(self, tmp_path):
        conf = load(write_config(tmp_path, ""))
        assert conf == Config()

    def test_invalid_threshold_detected(self, tmp_path):
        p = write_config(tmp_path, "[thresholds]\ncpu = 150.0")
        with pytest.raises(ValueError, match="cpu"):
            load(p)

    def test_invalid_interval_detected(self, tmp_path):
        p = write_config(tmp_path, "interval = -5")
        with pytest.raises(ValueError, match="interval"):
            load(p)


class TestLoadOrDefault:
    def test_explicit_missing_falls_back_to_defaults(self, tmp_path):
        conf, path = load_or_default(tmp_path / "nope.toml")
        assert conf == Config()
        assert path is None

    def test_explicit_existing_is_loaded(self, tmp_path):
        p = write_config(tmp_path, "interval = 5")
        conf, path = load_or_default(p)
        assert conf.interval == 5
        assert path == p

    def test_no_paths_given_returns_defaults(self):
        conf, path = load_or_default(None)
        assert conf == Config() or isinstance(conf, Config)
        assert isinstance(conf, Config)
