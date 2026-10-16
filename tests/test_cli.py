"""End-to-end CLI tests: snapshot, history storage, exit codes."""

import json
from pathlib import Path

import pytest

from servermon.cli import main


@pytest.fixture()
def quiet_config(tmp_path: Path) -> str:
    """Config with impossible-to-breach thresholds → deterministic exit codes.

    The dev machine may itself be over the default thresholds, so tests must not
    depend on live system state.
    """
    p = tmp_path / "limit.toml"
    p.write_text("[thresholds]\ncpu = 100.0\nmem = 100.0\ndisk = 100.0\n", encoding="utf-8")
    return str(p)


class TestSnapshot:
    def test_snapshot_text_ok(self, capsys, quiet_config):
        assert main(["--config", quiet_config, "snapshot"]) == 0
        out = capsys.readouterr().out
        for key in ("cpu", "ram", "swap", "disk", "load", "uptime"):
            assert key in out

    def test_snapshot_json_valid_and_sane(self, capsys, quiet_config):
        assert main(["--config", quiet_config, "snapshot", "--json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert 0 <= data["cpu"] <= 100
        assert 0 <= data["mem"] <= 100
        assert 0 <= data["disk"] <= 100
        assert isinstance(data["uptime_s"], int)
        assert "ts" in data

    def test_breach_returns_exit_code_1(self, capsys, tmp_path):
        # thresholds at 0 → any real usage exceeds them
        p = tmp_path / "zero.toml"
        p.write_text("[thresholds]\ncpu = 0.0001\nmem = 0.0001\ndisk = 0.0001\n", encoding="utf-8")
        assert main(["--config", str(p), "snapshot"]) == 1

    def test_top_processes(self, capsys, quiet_config):
        assert main(["--config", quiet_config, "snapshot", "--top", "3"]) == 0
        out = capsys.readouterr().out
        assert "top CPU processes" in out


class TestCheck:
    def test_check_ok_with_high_thresholds(self, capsys, quiet_config):
        assert main(["--config", quiet_config, "check"]) == 0
        assert "OK" in capsys.readouterr().out

    def test_check_alert_with_zero_thresholds(self, tmp_path, capsys):
        p = tmp_path / "zero.toml"
        p.write_text("[thresholds]\ncpu = 0.0001\nmem = 0.0001\ndisk = 0.0001\n", encoding="utf-8")
        assert main(["--config", str(p), "check"]) == 1
        assert "ALERT" in capsys.readouterr().err


class TestHistory:
    def test_roundtrip_through_watch(self, tmp_path):
        db = tmp_path / "history.db"
        # watch runs forever; instead use its storage path via history.save()
        import datetime as dt

        from servermon import history
        from servermon.metrics import Sample

        for i, cpu in enumerate((10.0, 20.0, 30.0)):
            history.save(
                db,
                Sample(
                    ts=(dt.datetime(2026, 10, 16, 12, i)),
                    cpu=cpu,
                    mem=40.0,
                    swap=0.0,
                    disk=55.0,
                    load1=None,
                    uptime_s=i,
                ),
            )
        rows = history.last(db, 2)
        assert [r["cpu"] for r in rows] == [20.0, 30.0]

    def test_history_missing_db(self, tmp_path, capsys):
        code = main(["history", "--db", str(tmp_path / "no.db")])
        assert code == 2
        assert "No history database" in capsys.readouterr().err

    def test_history_cli_prints_table(self, tmp_path, capsys):
        db = tmp_path / "history.db"
        import datetime as dt

        from servermon import history
        from servermon.metrics import Sample

        history.save(
            db,
            Sample(
                ts=dt.datetime(2026, 10, 16, 12, 0, 0).isoformat(),
                cpu=11.0,
                mem=22.0,
                swap=0,
                disk=33.0,
                load1=None,
                uptime_s=1,
            ),
        )
        assert main(["history", "--db", str(db)]) == 0
        out = capsys.readouterr().out
        assert "2026-10-16T12:00:00" in out
        assert "11.0" in out


class TestCliUx:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert "servermon" in capsys.readouterr().out

    def test_no_command_shows_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2
