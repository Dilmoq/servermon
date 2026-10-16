"""Application configuration loaded from a TOML file."""

from __future__ import annotations

import dataclasses
import pathlib
import tomllib


@dataclasses.dataclass(frozen=True)
class Thresholds:
    """Alert thresholds in percent."""

    cpu: float = 90.0
    mem: float = 85.0
    disk: float = 90.0


@dataclasses.dataclass(frozen=True)
class Config:
    """Full servermon configuration."""

    interval: int = 60  # seconds between samples in watch mode
    history_db: str = "servermon.db"
    thresholds: Thresholds = dataclasses.field(default_factory=Thresholds)

    def validate(self) -> list[str]:
        """Return a list of validation error strings (empty means valid)."""
        errors: list[str] = []
        if self.interval <= 0:
            errors.append("interval must be a positive number of seconds")
        if not (0 < self.thresholds.cpu <= 100):
            errors.append("thresholds.cpu must be in (0, 100]")
        if not (0 < self.thresholds.mem <= 100):
            errors.append("thresholds.mem must be in (0, 100]")
        if not (0 < self.thresholds.disk <= 100):
            errors.append("thresholds.disk must be in (0, 100]")
        return errors


DEFAULT_PATHS: tuple[pathlib.Path, ...] = (
    pathlib.Path.home() / ".config" / "servermon" / "config.toml",
    pathlib.Path.cwd() / "servermon.toml",
)


def load(path: pathlib.Path) -> Config:
    """Load configuration from a TOML file.

    Missing file is an error here; CLI falls back to defaults if no path given.
    """
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    thr_raw = raw.get("thresholds", {})
    config = Config(
        interval=int(raw.get("interval", Config.interval)),
        history_db=str(raw.get("history_db", Config.history_db)),
        thresholds=Thresholds(
            cpu=float(thr_raw.get("cpu", Thresholds.cpu)),
            mem=float(thr_raw.get("mem", Thresholds.mem)),
            disk=float(thr_raw.get("disk", Thresholds.disk)),
        ),
    )
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid config {path}: " + "; ".join(errors))
    return config


def load_or_default(explicit: pathlib.Path | None) -> tuple[Config, pathlib.Path | None]:
    """Return (config, used_path). Uses defaults when no file is found."""
    paths = (explicit,) if explicit is not None else DEFAULT_PATHS
    for p in paths:
        if p is not None and p.is_file():
            return load(p), p
    return Config(), None
