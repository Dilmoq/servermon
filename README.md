# servermon — lightweight server monitoring CLI

![CI](https://github.com/Dilmoq/servermon/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![pytest](https://img.shields.io/badge/tests-28%20passed-brightgreen.svg?logo=pytest&logoColor=white)

One-command server monitoring: instant CPU/RAM/disk snapshots, threshold alerts with
cron-friendly exit codes, and SQLite history. Zero dependencies beyond `psutil`.

```
$ servermon snapshot
time     2026-10-16T13:20:00
uptime   2h 15m
cpu        12.3 %
ram        61.0 %
swap        0.0 %
disk(/)    72.4 %
load       0.85

top CPU processes:
    4210  firefox              cpu  9.4%  mem  8.2%
    1850  python               cpu  2.1%  mem  1.4%
    ...
```

## Install

```bash
pip install servermon          # or: pipx install servermon
```

From source:

```bash
git clone https://github.com/Dilmoq/servermon && cd servermon
pip install -e .
```

## Commands

| Command | What it does |
|---|---|
| `servermon snapshot` | One metrics sample. `--json` for scripts, `--top N` for top processes by CPU |
| `servermon watch` | Collect samples into SQLite history until Ctrl+C. `--interval SEC`, `--db PATH` |
| `servermon check` | Exit **1** if any threshold is breached — perfect for cron/systemd |
| `servermon history` | Print recent samples. `--limit N` |

Global options: `--config PATH` (TOML file; default `~/.config/servermon/config.toml`).

## Configuration (`~/.config/servermon/config.toml`)

```toml
interval = 30        # seconds between snapshots in watch mode
history_db = "servermon.db"

[thresholds]         # alert thresholds, percent
cpu = 90
mem = 85
disk = 90
```

Missing file = sensible defaults (`60s`, `90/85/90`).

## Alerts and scheduling

`servermon check` is designed to be driven by cron or systemd timers:

```bash
* * * * * servermon check >> /var/log/servermon-alerts.log
```

Or with systemd see `examples/`: `servermon.service` (collector),
`servermon-check.service` + `servermoncheck.timer` (threshold check every 5 minutes,
fails loudly when breached — pair with `OnFailure=` to fire notifications).

## Example session — the whole story

```bash
servermon watch --interval 10          # terminal 1: collect history
servermon check; echo $?               # terminal 2: 1 = something is hot
servermon history --limit 5            # review recent samples
servermon snapshot --json              # feed to other tooling
```

## How it works

- **Metrics** come from [psutil](https://psutil.readthedocs.io/) (CPU, RAM, swap, root disk,
  load average where the OS provides it)
- **History** is a plain SQLite table (`ts, cpu, mem, disk`) — no daemons needed
- **Alerts** are pure functions of `(sample, thresholds)`; unit-tested, deterministic

## Project layout

```
servermon/
├── src/servermon/
│   ├── cli.py        # argparse UI: snapshot / watch / check / history
│   ├── config.py     # TOML loading + validation
│   ├── metrics.py    # psutil collection → Sample dataclass
│   ├── alerting.py   # threshold evaluation
│   └── history.py    # SQLite storage
├── examples/         # systemd unit, timer, check service
└── tests/            # 28 pytest tests (config, alerts, CLI e2e)
```
## License

MIT — see [LICENSE](LICENSE).
