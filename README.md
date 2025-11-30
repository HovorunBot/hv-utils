# hv-utils

Typed utility library for consolidating reusable Python helpers. The project is in early alpha; the current public
surface includes the cron expression parser (`parse_cron`) and expiration helpers (`Expiration`, `ExpiresIn`,
`ExpiresAfter`, `ExpiresAtTS`, `ExpiresAtDT`).

## Requirements

- Use: Python 3.12+; install from PyPI with pip/uv/Poetry (see install commands below); no external runtime
  dependencies.

## Install

- pip: `pip install hv-utils`
- uv: `uv add hv-utils`
- Poetry: `poetry add hv-utils`

## Quick start

- Install: `pip install hv-utils` (or add an extra such as `pip install hv-utils[cron]`).
- Use:

```python
from datetime import UTC, datetime, timedelta

from hv_utils.cron import cron_matches, parse_cron
from hv_utils.expiration import ExpiresAfter

schedule = parse_cron("*/15 0-12/6 1,15 1-3 MON-FRI")
print(schedule.minute)  # (0, 15, 30, 45)
print(cron_matches(schedule, datetime(2025, 1, 13, 12, 0, tzinfo=UTC)))

expires = ExpiresAfter(ttl=timedelta(hours=1), since=datetime.now(tz=UTC))
print(expires.as_ttl())  # Remaining time before expiration, clamped to zero
```

## Cron utility

- Parse: `hv_utils.cron.parse_cron(expression: str) -> CronSchedule` — expands a 5-field cron string into concrete minute,
  hour, day-of-month, month, and day-of-week tuples. Supports literals, ranges, steps (`*/n`), comma lists, and
  case-insensitive month/day names. Day-of-week treats both `0` and `7` as Sunday; invalid input raises `ValueError`
  with a consistent message.
- Match: `hv_utils.cron.cron_matches(expression: str | CronSchedule, when: datetime) -> bool` — checks whether a datetime
  satisfies a schedule. Day-of-month and day-of-week use cron OR semantics: if both are restricted, a match occurs when
  either field matches (all other fields must also match). If one is a wildcard, only the other is considered.
- Schedule helpers:
    - `CronSchedule.from_exp(expr: str)` — convenience constructor around `parse_cron`.
    - `CronSchedule.matches(dt: datetime) -> bool` — instance wrapper over `cron_matches`.
    - `CronSchedule.next(start: datetime, *, inclusive: bool = False, max_lookahead_days: int = 366) -> datetime` —
      returns the next occurrence after `start`, optionally including `start`, bounded by `max_lookahead_days`.
    -
    `CronSchedule.iter(start: datetime, *, inclusive: bool = False, max_lookahead_days: int = 366) -> Iterable[datetime]`
    — yields successive matching datetimes; callers should consume responsibly to avoid unbounded iteration.

## Expiration utilities

- Interfaces: `Expiration` standardizes conversion to timestamp (`as_timestamp()`), datetime (`as_datetime(tz=UTC)`), and
  remaining TTL (`as_ttl()`).
- Relative TTL: `ExpiresIn` computes expiration relative to the call time; TTL is constant because the target is always
  "now + ttl".
- Anchored TTL: `ExpiresAfter` adds a TTL to a timezone-aware start datetime and clamps negative TTL to zero.
- Absolute: `ExpiresAtTS` targets a Unix timestamp; `ExpiresAtDT` targets a timezone-aware datetime. Both clamp expired
  TTLs to zero.

## Development requirements

- Python 3.12+ for development; optionally install 3.13/3.14 to run the full test matrix.
- [uv](https://docs.astral.sh/uv/) for dependency management; sync dev tools via `uv sync --group dev`.
- Pre-commit hooks available; install with `pre-commit install`.

## How we work

- Functional-first utilities; keep state to a minimum.
- Standard library only at runtime. If an optional dependency is unavoidable, add an extra in `pyproject.toml`, guard
  the import with `try/except ImportError`, and raise a friendly install hint.
- Absolute imports only. Expose public helpers from `src/hv_utils/__init__.py`.
- Always type everything and keep `mypy --strict` green.
- TDD over heroics: write or update tests before implementing behavior, cover edge cases, and keep functions small and
  composable.
- Follow `ruff`/PEP 8 style (line length 120).

## Common commands

- Format: `uv run ruff format .`
- Lint (autofix): `uv run ruff check --fix .`
- Type-check: `uv run mypy src tests`
- Tests (current Python): `uv run pytest`
- Tests on a specific interpreter: `uv run --python 3.13 pytest`
- Full matrix (requires those interpreters installed):
    - `uv run --python 3.12 pytest`
    - `uv run --python 3.13 pytest`
    - `uv run --python 3.14 pytest`

## Pre-commit

- Install hooks: `pre-commit install` (uses your machine-level pre-commit)
- Run all hooks manually: `pre-commit run --all-files`
- Hooks auto-add the BSD-3 header (via `python -m tools.copyright_header`), then run the same uv-powered format, lint,
  type-check, and test commands listed above.

## Contributing

- Keep PRs small and focused on one utility or fix.
- Add tests, docstrings, and `__init__` exports alongside new utilities.
- Run format, lint, mypy, and pytest before opening a PR; for compatibility-sensitive changes, run the full matrix.
- Note: uv commands may need escalated permission in some environments. I will ask for escalation before running `uv` so
  tasks can proceed. The uv cache directory is already configured in `pyproject.toml`; no need to set `UV_CACHE_DIR`
  manually.
