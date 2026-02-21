# Python 3.9 compatibility — PEP 604 union syntax fix

## Files and lines using PEP 604 unions (`X | None`)

| File | Line(s) | Current | Replace with |
|------|---------|---------|--------------|
| ohlcv_hub/errors.py | 25 | `status_code: int \| None = None` | `status_code: Optional[int] = None` |
| ohlcv_hub/providers/alpaca.py | 35 | `currency: str \| None = None` (BarsResponse) | `currency: Optional[str] = None` |
| ohlcv_hub/providers/alpaca.py | 187–188 | `feed: str \| None = None`, `asof: str \| None = None` | `Optional[str]` |
| ohlcv_hub/providers/alpaca.py | 243–244 | `currency: str \| None`, `page_token: str \| None` | `Optional[str]` |
| ohlcv_hub/dataset.py | 20 | `feed: str \| None = "iex"` | `feed: Optional[str] = "iex"` |
| ohlcv_hub/dataset.py | 70 | `feed: str \| None = "iex"` | `feed: Optional[str] = "iex"` |
| ohlcv_hub/normalize.py | 13 | `currency: str \| None` | `currency: Optional[str]` |

Note: `tuple[Optional[int], ...]`, `dict[str, ...]`, `list[str]` are PEP 585 (built-in generics) and are valid in Python 3.9; no change.

## Plan

1. Add `Optional` to typing imports where missing: errors.py, dataset.py, normalize.py. (alpaca.py already has `Optional`.)
2. Replace every `str | None` and `int | None` with `Optional[str]` and `Optional[int]` in the listed files.
3. Run `pytest -q` and optionally `python -m compileall ohlcv_hub`.
4. Add `docs/internal/changes/2026-02-21-py39-compat.md` summarizing the change.
