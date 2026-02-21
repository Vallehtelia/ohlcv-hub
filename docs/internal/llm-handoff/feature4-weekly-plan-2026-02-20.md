# Feature 4 Plan - Weekly (1w) Resample Path

## Current State Summary

### Daily Fetch Path Flow

1. **CLI** (`ohlcv_hub/cli.py`):
   - Validates args (symbols, dates, out path).
   - If `tf == 1d`: loads config → `_make_alpaca_client(config)` → `build_daily_dataset(...)` → export → write report → print summary.
   - Returns: exit 0 on success, 1 on validation/provider errors (export-on-error policy).

2. **Dataset** (`ohlcv_hub/dataset.py`):
   - `build_daily_dataset(client, symbols, start, end, adjustment, feed)`:
     - Calls `client.fetch_stock_bars(timeframe="1Day", ...)`.
     - Normalizes via `bars_dict_to_dataframe(..., timeframe="1d", ...)`.
     - Validates via `validate_daily_bars(df, start=start, end=end)`.
     - Returns `(df: DataFrame, report: dict)`.

3. **Normalize** (`ohlcv_hub/normalize.py`):
   - `bars_dict_to_dataframe(bars, timeframe, source, currency, adjustment)` → DataFrame with schema: symbol, timeframe, ts, open, high, low, close, volume, source, currency, adjustment. Sorted by symbol, ts.

4. **Validate** (`ohlcv_hub/validate.py`):
   - `validate_daily_bars(df, start, end)` → `(ok: bool, report: dict)`.
   - Report keys: `summary` (symbols_count, bars_count, date_range), `issues` (duplicates, non_monotonic, ohlc_violations, volume_violations), `missing_days` (per-symbol lists + `totals.missing_days_count_total`).
   - Missing days: NYSE calendar `valid_days(start, end)`, bar_date = ts in NY timezone.

5. **Export** (`ohlcv_hub/export.py`):
   - `export_dataframe(df, out_dir, format, filename)` → full path. Creates dir, writes parquet or csv.

6. **Return values**: `build_daily_dataset` returns `(df, report)`. CLI uses report for summary and for writing `validation_report.json`.

### Validation Report Schema (Current)

```json
{
  "summary": {
    "symbols_count": int,
    "bars_count": int,
    "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
  },
  "issues": {
    "duplicates": [{"symbol", "ts", "count"}],
    "non_monotonic": [{"symbol", "example_ts_prev", "example_ts_next"}],
    "ohlc_violations": {"count": int, "samples": [...]},
    "volume_violations": {"count": int, "samples": [...]}
  },
  "missing_days": {
    "SYMBOL": ["YYYY-MM-DD", ...],
    "totals": {"missing_days_count_total": int}
  }
}
```

For weekly we must keep the same top-level keys. For `missing_days`: set to `{}` with `totals: { "missing_days_count_total": 0 }` (no per-symbol missing days for weekly).

### Proposed Weekly Timestamp Policy

- **Policy**: Monday 00:00 UTC (week start), deterministic.
- **Implementation**: pandas `resample('W-MON', label='left', closed='left')`.
- **Requirements**: Input `ts` must be tz-aware UTC and set as index before resampling.
- **Aggregation**: open=first, high=max, low=min, close=last, volume=sum.
- **Output**: `timeframe = "1w"`, same schema columns otherwise.

### Test Strategy

- **Approach**: Same as daily — `httpx.MockTransport` for Alpaca bars; monkeypatch `ohlcv_hub.cli._make_alpaca_client` to inject client with mock transport.
- **Fixtures**: Minimal daily bars spanning ≥2 calendar weeks for two symbols (e.g. 6–8 daily bars per symbol so we get 2 weeks × 2 symbols = 4 weekly rows).
- **Assertions**:
  - Exit 0 when mock returns valid daily bars.
  - Weekly parquet exists; `timeframe` column only `"1w"`; `ts` values are Mondays 00:00:00+00:00; row count = expected weeks × symbols.
  - `validation_report.json` exists; `missing_days.totals.missing_days_count_total == 0`.
  - Provider error (e.g. 401) → exit 1 and message mentions provider.

### Files to Add/Modify

- **Add**: `ohlcv_hub/resample.py` (`to_weekly`), `tests/test_fetch_1w_integration_mocked.py`, `docs/changes/2026-02-20-fetch-1w.md`.
- **Modify**: `ohlcv_hub/dataset.py` (add `build_weekly_dataset`), `ohlcv_hub/cli.py` (wire `tf==1w` to weekly builder), `ohlcv_hub/validate.py` (add `validate_weekly_bars` or shared validator + skip missing-days for weekly).
- **Update**: `tests/test_fetch_1d_integration_mocked.py` — remove or change `test_fetch_1w_still_exits_2` to expect weekly implemented (exit 0 with weekly file).
