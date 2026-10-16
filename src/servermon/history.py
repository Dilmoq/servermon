"""SQLite-backed metrics history."""

from __future__ import annotations

import pathlib
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    ts      TEXT PRIMARY KEY,
    cpu     REAL NOT NULL,
    mem     REAL NOT NULL,
    disk    REAL NOT NULL
);
"""

_COLS = ("ts", "cpu", "mem", "disk")


def connect(db_path: str | pathlib.Path) -> sqlite3.Connection:
    """Open history database and ensure the schema exists."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def save(db_path: str | pathlib.Path, sample) -> None:
    """Append one sample to history."""
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO samples (ts, cpu, mem, disk) VALUES (?, ?, ?, ?)",
                (sample.ts, sample.cpu, sample.mem, sample.disk),
            )
    finally:
        conn.close()


def last(db_path: str | pathlib.Path, limit: int = 10) -> list[dict]:
    """Return the most recent `limit` samples as dicts (oldest first)."""
    conn = connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT {', '.join(_COLS)} FROM samples ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()
    return [dict(zip(_COLS, row, strict=True)) for row in reversed(rows)]
