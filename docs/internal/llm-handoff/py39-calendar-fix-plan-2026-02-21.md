# Python 3.9 calendar fix — replace pandas_market_calendars with exchange_calendars

## Current missing-days logic and report schema

- **validate.py**: `validate_daily_bars` builds a report with `_validate_bars_issues` then fills `report["missing_days"]`.
- **Current calendar usage**: `mcal.get_calendar("NYSE")`, then `nyse.valid_days(start_date=start, end_date=end)` → `expected_days.date` → `set(expected_dates)`.
- **Bar date**: `symbol_df_ny["bar_date"] = symbol_df_ny["ts"].dt.tz_convert(NY_TZ).dt.date`; `present_dates = set(symbol_df_ny["bar_date"])`.
- **Missing**: `missing_dates = sorted(expected_dates - present_dates)` per symbol; stored as list of ISO date strings.
- **Report schema**: `report["missing_days"]` = dict with per-symbol keys (symbol → list of "YYYY-MM-DD") and `"totals": {"missing_days_count_total": int}`. On error, `report["missing_days"]["error"]` and totals 0.

## Where pandas_market_calendars is used

- **ohlcv_hub/validate.py**: line 7 `import pandas_market_calendars as mcal`; lines 157–161 `nyse = mcal.get_calendar("NYSE")`, `expected_days = nyse.valid_days(start_date=start, end_date=end)`, `expected_dates = set(expected_days.date)`.
- **pyproject.toml**: line 32 `pandas_market_calendars>=4.3.0` in dependencies.

## Test schema constraints

- **test_fetch_1d_integration_mocked.py**: Asserts `"missing_days" in report`; report has summary, issues, missing_days; no assertion on exact missing_days_count_total value.
- **test_fetch_1w_integration_mocked.py**: Asserts `report["missing_days"]["totals"]["missing_days_count_total"] == 0` (weekly has no missing-days logic; totals 0).
- Schema stability: `missing_days` must exist; `missing_days.totals.missing_days_count_total` must be an int.

## Proposed replacement (exchange_calendars)

- **Import**: `import exchange_calendars as xcals` (no pandas_market_calendars).
- **Calendar**: `cal = xcals.get_calendar("XNYS")` (NYSE).
- **Expected sessions**: `start_ts = pd.Timestamp(start, tz="America/New_York")`, `end_ts = pd.Timestamp(end, tz="America/New_York")`, `sessions = cal.sessions_in_range(start_ts, end_ts)`. `sessions` is a DatetimeIndex; get dates via `expected_dates = set(sessions.date)` (if sessions are date-only or midnight) or `expected_dates = set(pd.DatetimeIndex(sessions).tz_convert("America/New_York").date)`.
- **Rest**: Keep same logic (bar_date from ts in NY, missing = expected - present per symbol, same report structure). Report schema unchanged.
