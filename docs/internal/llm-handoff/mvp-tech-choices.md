# MVP Tech Stack Choices

## Overview

This document captures the concrete technology choices for the MVP implementation, with justifications and dependency lists.

## HTTP Client

### Choice: **httpx**

**Rationale**:
- Modern, fully type-annotated library with excellent async support
- Maintains requests-compatible API for easy migration
- Supports HTTP/2 (future-proof)
- Better connection pooling and built-in testing support
- Strict timeouts everywhere (safer defaults)
- Active development and strong community adoption

**Alternative Considered**: `requests`
- **Why not**: Synchronous only, no HTTP/2, less modern API
- **When to reconsider**: If we need maximum ecosystem maturity and zero async requirements

**Dependency**: `httpx>=0.27.0`

## Dataframe Stack

### Choice: **pandas + pyarrow**

**Rationale**:
- Mature ecosystem with extensive documentation and community support
- Excellent Parquet support via pyarrow (native integration)
- Familiar API for most Python developers
- Sufficient performance for MVP scope (daily/weekly bars, not high-frequency)
- Better integration with existing Python data science tooling
- Smaller learning curve for future maintainers

**Alternative Considered**: `polars + pyarrow`
- **Why not**: 
  - Polars is faster (3-10x) but adds complexity for MVP
  - Less familiar API, smaller ecosystem
  - Performance gains not critical for daily/weekly aggregation workloads
  - Can migrate to Polars later if performance becomes bottleneck
- **When to reconsider**: If we need to process millions of bars or require streaming capabilities

**Dependencies**:
- `pandas>=2.2.0`
- `pyarrow>=15.0.0` (for Parquet read/write)

**Parquet Writing Approach**:
- Use `pandas.DataFrame.to_parquet()` with `engine='pyarrow'`
- Schema mapping: Alpaca fields → our stable schema:
  - `t` (timestamp) → `timestamp` (datetime64[ns, UTC])
  - `o` (open) → `open` (float64)
  - `h` (high) → `high` (float64)
  - `l` (low) → `low` (float64)
  - `c` (close) → `close` (float64)
  - `v` (volume) → `volume` (int64)
  - `n` (trade_count) → `trade_count` (int64, optional)
  - `vw` (VWAP) → `vwap` (float64, optional)
- Use partitioned Parquet files by symbol and date range for efficient querying
- Compression: `snappy` (good balance of speed and compression ratio)

## CLI Framework

### Choice: **typer**

**Rationale**:
- Modern, type-hint based API (significantly less boilerplate than Click)
- Built by FastAPI creator (Sebastián Ramírez) - modern Python best practices
- Automatic documentation generation from type hints
- Native async support if needed later
- Cleaner, more Pythonic code (18 lines vs 30+ lines for equivalent Click code)
- Built on Click (can leverage Click ecosystem if needed)

**Alternative Considered**: `click`
- **Why not**: More verbose, requires manual type specification, decorator-heavy
- **When to reconsider**: If we need Click-specific plugins or ecosystem features

**Dependency**: `typer>=0.12.0`

## Time Handling

### Choice: **zoneinfo** (Python 3.9+) + **python-dateutil** (for parsing)

**Rationale**:
- `zoneinfo` is built into Python 3.9+ (no external dependency for timezone handling)
- `python-dateutil` provides robust date parsing (handles RFC-3339, ISO formats, etc.)
- Standard library `datetime` for core datetime operations
- Minimal dependencies, maximum compatibility

**Dependencies**:
- `python-dateutil>=2.8.0` (for parsing Alpaca RFC-3339 timestamps)
- `zoneinfo` (built-in Python 3.9+)

**Usage**:
- Parse Alpaca timestamps: `dateutil.parser.parse(timestamp_str)` → UTC datetime
- Store all timestamps as UTC (`datetime` with `timezone.utc`)
- Use `zoneinfo.ZoneInfo("America/New_York")` for trading calendar operations

## Weekly Resample Timestamp Policy

### Choice: **Monday 00:00 UTC**

**Rationale**:
- **Pros**:
  - Deterministic and timezone-independent (no DST issues)
  - Simple to implement (`resample('W-MON', closed='left', label='left')`)
  - Consistent week boundaries regardless of trading calendar
  - Easy to reason about (week = Monday 00:00 UTC to next Monday 00:00 UTC)
- **Cons**:
  - May not align with actual trading week boundaries (e.g., if Monday is a holiday)
  - Weekly bars may span partial trading weeks

**Alternative Considered**: **First Trading Day of Week**
- **Pros**: Aligns with actual trading activity
- **Cons**:
  - Requires trading calendar lookup (adds dependency)
  - More complex implementation (custom resampling logic)
  - Week boundaries vary by year (holidays shift boundaries)
  - Not deterministic without calendar data

**Recommendation**: Start with Monday 00:00 UTC for MVP simplicity. Can add "first trading day" option later if needed.

**Implementation Notes**:
- Use `pandas.resample('W-MON', closed='left', label='left')` for weekly aggregation
- Ensure timestamps are UTC before resampling
- Document timestamp policy in output schema/metadata

## Trading Calendar Library

### Choice: **pandas_market_calendars**

**Rationale**:
- Actively maintained (commits within 23 days)
- MIT License (permissive)
- Contains hardcoded calendar definitions (no external API dependencies)
- As of v2.0, includes all calendars from exchange_calendars package (50+ calendars)
- Lightweight and easy to use
- Good integration with pandas

**Alternative Considered**: `exchange_calendars`
- **Why not**: Less clear maintenance status, pandas_market_calendars now includes its calendars
- **When to reconsider**: If pandas_market_calendars stops being maintained

**Dependency**: `pandas_market_calendars>=4.3.0`

**Usage**:
- Use `pandas_market_calendars.get_calendar('NYSE')` for US equity trading calendar
- Check `calendar.valid_days(start_date, end_date)` to get expected trading days
- Compare against retrieved bars to identify missing days
- Report missing days separately (holidays vs data gaps)

**Licensing**: MIT License (no concerns)

## Minimal Dependency List

```toml
[project]
dependencies = [
    "httpx>=0.27.0",
    "pandas>=2.2.0",
    "pyarrow>=15.0.0",
    "typer>=0.12.0",
    "python-dateutil>=2.8.0",
    "pandas_market_calendars>=4.3.0",
]
```

**Total Dependencies**: 6 (excluding transitive dependencies)

**Python Version**: 3.9+ (for `zoneinfo` support)

## Schema Mapping Summary

### Alpaca API → Internal DataFrame → Parquet

**Input (Alpaca API)**:
```json
{
  "t": "2022-01-03T09:00:00Z",
  "o": 178.26,
  "h": 178.34,
  "l": 177.76,
  "c": 178.08,
  "v": 60937,
  "n": 1727,
  "vw": 177.954244
}
```

**Internal DataFrame (pandas)**:
```python
timestamp: datetime64[ns, UTC]  # parsed from "t"
open: float64                    # from "o"
high: float64                    # from "h"
low: float64                     # from "l"
close: float64                   # from "c"
volume: int64                     # from "v"
trade_count: int64               # from "n" (optional)
vwap: float64                    # from "vw" (optional)
symbol: string                   # added from response key
```

**Parquet Output**:
- Partitioned by `symbol` and `year/month` (or date range)
- Schema: same as DataFrame columns
- Compression: `snappy`
- Row groups: ~10,000 rows per group (good for query performance)

## Deterministic Weekly Resample Approach

**Policy**: Monday 00:00 UTC

**Implementation**:
1. Ensure all timestamps are UTC (`datetime` with `timezone.utc`)
2. Set DataFrame index to timestamp column
3. Group by symbol
4. For each symbol, resample: `df.resample('W-MON', closed='left', label='left')`
5. Aggregate OHLCV:
   - `open`: first value of `open`
   - `high`: max of `high`
   - `low`: min of `low`
   - `close`: last value of `close`
   - `volume`: sum of `volume`
   - `trade_count`: sum of `trade_count` (if present)
   - `vwap`: volume-weighted average of `vwap` (if present)
6. Timestamp of weekly bar = Monday 00:00 UTC of that week

**Edge Cases**:
- Weeks with no trading days: Skip (don't create empty weekly bar)
- Partial weeks: Include all available daily bars in the week
- DST transitions: No impact (UTC is timezone-independent)

## Missing Days Report Approach

**Using pandas_market_calendars**:

1. Get NYSE calendar: `cal = pandas_market_calendars.get_calendar('NYSE')`
2. Generate expected trading days: `expected_days = cal.valid_days(start_date, end_date)`
3. Compare with retrieved bars:
   - Missing days = `expected_days - set(retrieved_bar_dates)`
4. Categorize missing days:
   - **Holidays**: Days in calendar that are not trading days (already excluded from `valid_days`)
   - **Data gaps**: Trading days in `expected_days` but not in retrieved bars
   - **Delisted**: Symbol stopped trading mid-period (no bars after delisting date)
5. Report separately:
   - List of missing trading days per symbol
   - Delisted symbols with last trading date
   - Data quality metrics (coverage %)

**Output Format** (suggested):
- JSON report: `missing_days_report.json`
- CSV report: `missing_days_report.csv`
- Include: symbol, date, reason (holiday/data_gap/delisted), expected vs actual

## Summary

| Category | Choice | Key Reason |
|----------|--------|------------|
| HTTP Client | httpx | Modern, async-ready, type-annotated |
| Dataframe | pandas | Mature, familiar, sufficient for MVP |
| Parquet | pyarrow | Native pandas integration |
| CLI | typer | Type-hint based, less boilerplate |
| Time Parsing | python-dateutil | Robust RFC-3339 parsing |
| Timezone | zoneinfo | Built-in Python 3.9+ |
| Trading Calendar | pandas_market_calendars | Active, MIT license, comprehensive |
| Weekly Resample | Monday 00:00 UTC | Deterministic, simple |
| Python Version | 3.9+ | For zoneinfo support |

**Total Dependencies**: 6 external packages (plus Python stdlib)
