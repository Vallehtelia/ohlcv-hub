# Feature 3 Plan - Fetch 1d End-to-End Implementation

## Current State Summary

### CLI Contract (`ohlcv_hub/cli.py`)

**Exit Codes**:
- `0`: Success
- `1`: Configuration/validation/user errors
- `2`: Feature not implemented (currently used for all fetch commands)

**Current `fetch` Command Behavior**:
- Validates arguments (symbols, dates, output path)
- Normalizes symbols (uppercase, strip spaces)
- Parses dates (YYYY-MM-DD format)
- Prints parsed configuration
- Exits with code 2 (not implemented)

**Arguments**:
- `--symbols`: Comma-separated list (required)
- `--start`: YYYY-MM-DD (required)
- `--end`: YYYY-MM-DD (required)
- `--tf`: `1d` or `1w` (required)
- `--out`: Output directory path (required)
- `--format`: `parquet` or `csv` (default: `parquet`)
- `--adjustment`: `raw` or `all` (default: `raw`)
- `--provider`: `alpaca` (default, only supported)
- `--report/--no-report`: Generate validation report (default: `--report`)

### AlpacaClient API (`ohlcv_hub/providers/alpaca.py`)

**Class**: `AlpacaClient`

**Initialization**:
```python
AlpacaClient(
    api_key: str,
    api_secret: str,
    base_url: str = "https://data.alpaca.markets",
    timeout_seconds: float = 10.0,
    http: Optional[httpx.Client] = None  # For testing injection
)
```

**Method**: `fetch_stock_bars(...)`

**Signature**:
```python
def fetch_stock_bars(
    symbols: list[str],
    timeframe: str,
    start: date | datetime | str,
    end: date | datetime | str,
    limit: int = 10000,
    adjustment: str = "raw",
    feed: str | None = None,
    asof: str | None = None,
    sort: str = "asc",
) -> BarsResponse
```

**Return Type**: `BarsResponse` dataclass
```python
@dataclass
class BarsResponse:
    bars: dict[str, list[dict[str, Any]]]  # symbol -> list of bar objects
    currency: str | None = None
```

**Bar Object Structure** (from Alpaca API):
- `t`: timestamp (RFC-3339 string, e.g., "2024-01-01T04:00:00Z")
- `o`: open (float)
- `h`: high (float)
- `l`: low (float)
- `c`: close (float)
- `v`: volume (int)
- `n`: trade_count (int, optional)
- `vw`: VWAP (float, optional)

**Behavior**:
- Normalizes symbols to uppercase
- Handles pagination automatically (loops until `next_page_token` is null/empty)
- Merges bars by symbol across pages
- Raises `ProviderError` on API errors (with status_code)

### Error Types (`ohlcv_hub/errors.py`)

- `OhlcvHubError`: Base exception
- `ConfigError(OhlcvHubError)`: Configuration errors
- `CliUsageError(OhlcvHubError)`: CLI usage errors
- `ProviderError(OhlcvHubError)`: Provider API errors (has `status_code` attribute)

### Type Definitions (`ohlcv_hub/types.py`)

- `Timeframe`: `DAILY = "1d"`, `WEEKLY = "1w"`
- `OutputFormat`: `PARQUET = "parquet"`, `CSV = "csv"`
- `Adjustment`: `RAW = "raw"`, `ALL = "all"`
- `Provider`: `ALPACA = "alpaca"`

### Test Strategy

**Current Tests**:
- `test_cli_doctor.py`: Tests doctor command (env vars, secret masking)
- `test_cli_fetch_parsing.py`: Tests fetch argument parsing and validation
- `test_alpaca_client_pagination.py`: Tests AlpacaClient with MockTransport

**Testing Approach for Feature 3**:
- Use `httpx.MockTransport` to mock API responses
- Inject `httpx.Client` with MockTransport into `AlpacaClient` via `http` parameter
- For CLI integration tests, add injection point: `_make_alpaca_client(config)` function in `cli.py`
- Monkeypatch `ohlcv_hub.cli._make_alpaca_client` in tests to return client with MockTransport
- Test end-to-end flow: CLI → AlpacaClient → normalize → validate → export

## What We Need to Add

### New Modules

1. **`ohlcv_hub/normalize.py`**
   - `bars_dict_to_dataframe()` function
   - Convert `BarsResponse.bars` dict to pandas DataFrame
   - Schema: symbol, timeframe, ts (UTC datetime), open, high, low, close, volume, source, currency, adjustment
   - Parse RFC-3339 timestamps to UTC datetime
   - Sort by symbol, then ts (ascending)

2. **`ohlcv_hub/validate.py`**
   - `validate_daily_bars()` function
   - Check duplicates (symbol, ts)
   - Check monotonic timestamps within symbol
   - Check OHLC sanity (high >= max(open,close), low <= min(open,close), high >= low)
   - Check volume >= 0
   - Missing trading days detection using `pandas_market_calendars` NYSE calendar
   - Return `(ok: bool, report_dict: dict)`
   - Report structure: summary, issues, missing_days

3. **`ohlcv_hub/export.py`**
   - `export_dataframe()` function
   - Write parquet (pyarrow) or CSV
   - Create output directory if needed
   - Return full file path

4. **`ohlcv_hub/dataset.py`**
   - `build_daily_dataset()` function
   - Orchestrate: fetch → normalize → validate
   - Return `(df: DataFrame, report_dict: dict)`

### CLI Modifications (`ohlcv_hub/cli.py`)

**Changes**:
- Add `_make_alpaca_client(config: Config) -> AlpacaClient` function (for test injection)
- Modify `fetch` command:
  - If `tf == 1w`: Keep current behavior (exit 2, "not implemented")
  - If `tf == 1d`:
    - Load config
    - Create AlpacaClient via `_make_alpaca_client()`
    - Call `build_daily_dataset()`
    - Export via `export_dataframe()`
    - Write `validation_report.json` if `--report`
    - Print summary (bars count, symbols, file path, missing days)
    - Exit 0 on success (even with missing days warnings)
    - Exit 1 on hard validation errors (but still export - document this policy)
    - Handle `ProviderError` with friendly message

**Exit Code Policy**:
- `0`: Success (export completed, report written if enabled)
- `1`: User/config/validation/provider errors
- `2`: Unimplemented (weekly path)

**Export-on-Validation-Error Policy**:
- For MVP safety: Export even if validation errors exist, but exit with code 1
- Print error summary before exporting
- Document this in change notes

### Error Handling

- Handle `ProviderError` in CLI with friendly message
- Handle validation errors (print summary, but continue export)
- Missing days are warnings only (don't fail the run)

### File Naming

- Daily bars: `<out>/ohlcv_1d_<YYYYMMDD>_<YYYYMMDD>.parquet` (or `.csv`)
- Report: `<out>/validation_report.json`

### Missing Days Detection

- Use `pandas_market_calendars.get_calendar('NYSE')`
- Get expected trading days: `calendar.valid_days(start, end)` (inclusive)
- Convert bar timestamps to NY timezone: `ts.dt.tz_convert('America/New_York').dt.date`
- Compare expected dates vs present dates per symbol
- Report missing dates per symbol + total count

### Test Strategy

**New Test File**: `tests/test_fetch_1d_integration_mocked.py`

**Test Cases**:
1. `test_fetch_1d_writes_parquet_and_report(tmp_path, monkeypatch)`
   - Mock 1-page bars response (2 symbols, next_page_token=None)
   - Run CLI fetch command
   - Assert exit code 0
   - Assert parquet file exists
   - Assert validation_report.json exists
   - Load parquet and verify columns and symbol count

2. `test_fetch_1d_handles_provider_error(tmp_path, monkeypatch)`
   - Mock 401 response
   - Assert exit code 1
   - Assert error message mentions provider error

**MockTransport Setup**:
- Create `httpx.MockTransport` with handler function
- Create `httpx.Client(transport=mock_transport)`
- Monkeypatch `ohlcv_hub.cli._make_alpaca_client` to return `AlpacaClient(..., http=mock_client)`

## Implementation Order

1. Create `normalize.py` with `bars_dict_to_dataframe()`
2. Create `validate.py` with `validate_daily_bars()`
3. Create `export.py` with `export_dataframe()`
4. Create `dataset.py` with `build_daily_dataset()`
5. Modify `cli.py` to wire everything together
6. Add integration tests
7. Update README.md

## Key Decisions

1. **Date Extraction for Missing Days**: Convert timestamps to NY timezone, then extract date
   - Rationale: Alpaca daily bars use 04:00Z (midnight ET), need NY date for trading calendar
   - Policy: `ts.dt.tz_convert('America/New_York').dt.date`

2. **Export-on-Validation-Error**: Export even with validation errors, but exit 1
   - Rationale: MVP safety - don't lose data, but signal issues
   - Document in change notes

3. **Sorting**: Sort DataFrame by symbol, then ts (ascending) in normalize step
   - Rationale: Required for monotonic validation, deterministic output

4. **Missing Days as Warnings**: Don't fail run for missing days
   - Rationale: Data gaps are informational, not errors

5. **Single File Output**: One file per run (not partitioned)
   - Rationale: Simpler MVP, can add partitioning later

6. **Test Injection Point**: Add `_make_alpaca_client()` function
   - Rationale: Enables CLI integration tests without real network

## Dependencies

- `pandas`: DataFrame operations, datetime parsing
- `pyarrow`: Parquet export
- `pandas_market_calendars`: Trading calendar for missing days detection
- `zoneinfo`: Timezone handling (built-in Python 3.9+)

## Acceptance Criteria

- `ohlcv-hub fetch --tf 1d ...` works end-to-end
- Writes parquet/csv file with correct schema
- Writes validation_report.json when `--report`
- Weekly path still exits 2
- All tests pass (no real network calls)
- Schema matches mini-spec exactly
