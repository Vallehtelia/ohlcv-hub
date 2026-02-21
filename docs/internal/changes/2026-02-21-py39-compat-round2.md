# 2026-02-21: Python 3.9 compatibility — round 2 (remaining PEP 604 unions)

## What changed

Replaced remaining PEP 604 union type hints in `ohlcv_hub/providers/alpaca.py` with `typing.Union[...]` so the package is fully Python 3.9 compatible. No runtime behavior changes.

## Files touched

- **ohlcv_hub/providers/alpaca.py** — Added `Union` to typing imports; `date | datetime | str` → `Union[date, datetime, str]` for `_serialize_date(dt)` and for `fetch_stock_bars(start, end)`.

## How to test

- `pytest -q` — all tests pass.
- `python -m compileall ohlcv_hub` — no syntax errors.
- No ` | ` left in ohlcv_hub/**/*.py; CI on Python 3.9 should pass.
