# Python 3.9 compatibility — PEP 604 union fix (round 2)

## Remaining `|` in type hints (runtime code only: ohlcv_hub/**/*.py)

| File | Line(s) | Current |
|------|---------|---------|
| ohlcv_hub/providers/alpaca.py | 92 | `dt: date \| datetime \| str` in `_serialize_date` |
| ohlcv_hub/providers/alpaca.py | 183–184 | `start: date \| datetime \| str`, `end: date \| datetime \| str` in `fetch_stock_bars` |

Replace with `Union[date, datetime, str]` and add `Union` to typing imports in alpaca.py.
