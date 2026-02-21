# 2026-02-21: Python 3.9 calendar fix — replace pandas_market_calendars with exchange_calendars

## What changed

Missing-trading-days detection now uses `exchange_calendars` instead of `pandas_market_calendars`. The latter uses PEP 604 union types internally, which breaks on Python 3.9 in CI. We keep Python 3.9 support and preserve the same report schema and behavior.

## Files touched

- **ohlcv_hub/validate.py** — Replaced `import pandas_market_calendars as mcal` with `import exchange_calendars as xcals`. NYSE calendar: `xcals.get_calendar("XNYS")`; expected sessions: `cal.sessions_in_range(start, end)` (timezone-naive `date`); `expected_dates = set(s.date() for s in sessions)`. Rest of logic (bar_date from ts in America/New_York, missing per symbol, totals) unchanged.
- **pyproject.toml** — Removed `pandas_market_calendars>=4.3.0`; added `exchange-calendars>=3.3` as a runtime dependency.

## How to test

- `pytest -q` — all tests pass.
- `python -c "import exchange_calendars as xc; print(xc.get_calendar('XNYS'))"` — import and calendar load.
- CI on Python 3.9 should pass (no PEP 604 in our deps).

## Why we replaced pandas_market_calendars

`pandas_market_calendars` (and/or its dependencies) use type hints with PEP 604 union syntax (`X | Y`), which requires Python 3.10+. That caused CI to fail on the Python 3.9 matrix job. `exchange_calendars` is Python 3.9–compatible and provides the same NYSE calendar (XNYS) and `sessions_in_range(start, end)` for expected trading days.
