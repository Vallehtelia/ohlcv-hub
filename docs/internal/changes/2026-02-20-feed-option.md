# 2026-02-20: `--feed` CLI Option

## What changed

- Added a **`--feed`** option to `ohlcv-hub fetch` with allowed values: `iex`, `sip`, `boats`, `otc`. Default is `iex` (unchanged).
- **Feed** enum added in `ohlcv_hub/types.py`; Typer enforces choices (invalid or empty value yields validation error).
- **CLI** passes `feed.value` into `build_daily_dataset` and `build_weekly_dataset` for both 1d and 1w.
- **dataset.py** unchanged in signature; already accepted `feed` and passed it to `AlpacaClient.fetch_stock_bars(... feed=feed)`.
- **Tests**: Mock handlers now capture request params; existing 1d/1w tests assert default `feed=iex`. New test `test_fetch_1d_with_feed_sip_passes_feed_to_client` asserts `--feed sip` is sent as `feed=sip` in the request.
- **README**: Examples updated to mention `--feed` and show optional `--feed iex`.

## Files touched

- `ohlcv_hub/types.py` — added `Feed` enum.
- `ohlcv_hub/cli.py` — added `--feed` option, pass `feed.value` to dataset builders.
- `ohlcv_hub/dataset.py` — no code change (already had `feed` param).
- `tests/test_fetch_1d_integration_mocked.py` — capture params, assert default feed; add `--feed sip` test.
- `tests/test_fetch_1w_integration_mocked.py` — capture params, assert default feed.
- `README.md` — usage examples and `--feed` note.
- `docs/llm-handoff/feature5a-feed-option-plan-2026-02-20.md` — plan (verification spike).
- `docs/changes/2026-02-20-feed-option.md` — this file.

## How to test

- **Automated**: `pytest -q` (all tests pass).
- **Manual**:  
  `ohlcv-hub fetch --symbols SPY --start 2024-01-01 --end 2024-01-10 --tf 1d --out ./data --feed iex`  
  Invalid/empty feed: `ohlcv-hub fetch ... --feed invalid` → validation error (Typer).

## TODOs

- None for this feature. Future: optional `--feed` for `doctor --ping` if desired.
