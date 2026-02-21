# Current State Summary - 2026-02-20

## Overview

This document summarizes the current state of the ohlcv-hub repository as of 2026-02-20, after the initial bootstrap phase.

## CLI Commands

### `ohlcv-hub doctor`
- **Purpose**: Check configuration and optionally test API connectivity
- **Exit Codes**:
  - `0`: Success (configuration OK, optional ping test passed)
  - `1`: Configuration error (missing env vars or ping test failed)
- **Behavior**:
  - Validates `ALPACA_API_KEY` and `ALPACA_API_SECRET` environment variables
  - Prints masked secrets (never prints actual keys)
  - Optional `--ping` flag performs authenticated test request to Alpaca API
  - Ping test uses `SPY` symbol, `1Day` timeframe, last 10 days, `feed=iex`, `limit=1`
  - Uses 10-second timeout for API requests

### `ohlcv-hub fetch`
- **Purpose**: Fetch historical OHLCV data (skeleton implementation)
- **Exit Codes**:
  - `1`: Validation error (invalid arguments)
  - `2`: Feature not implemented (valid arguments parsed but fetch not implemented)
- **Arguments**:
  - `--symbols`: Comma-separated list of stock symbols (required)
  - `--start`: Start date in YYYY-MM-DD format (required)
  - `--end`: End date in YYYY-MM-DD format (required)
  - `--tf`: Timeframe - `1d` (daily) or `1w` (weekly) (required)
  - `--out`: Output directory path (required)
  - `--format`: Output format - `parquet` or `csv` (default: `parquet`)
  - `--adjustment`: Stock adjustment - `raw` or `all` (default: `raw`)
  - `--provider`: Data provider - only `alpaca` supported (default: `alpaca`)
  - `--report/--no-report`: Generate missing days report (default: `--report`)
- **Behavior**:
  - Validates and normalizes symbols (uppercase, strips spaces, filters empty segments)
  - Validates date format and ordering (start <= end)
  - Validates output path is non-empty
  - Prints parsed configuration and exits with code 2
  - **Not implemented**: Actual data fetching, resampling, validation, or export

## Configuration

### Environment Variables
- `ALPACA_API_KEY`: Alpaca API key identifier (required)
- `ALPACA_API_SECRET`: Alpaca API secret key (required)
- `ALPACA_DATA_BASE_URL`: Base URL for Alpaca Market Data API (optional, default: `https://data.alpaca.markets`)

### Config Module (`ohlcv_hub/config.py`)
- `Config` dataclass with `alpaca_api_key`, `alpaca_api_secret`, `alpaca_data_base_url`
- `load_config_from_env(require_keys: bool)` function to load from environment
- Raises `ConfigError` if `require_keys=True` and keys are missing

## Error Handling

### Exception Hierarchy (`ohlcv_hub/errors.py`)
- `OhlcvHubError`: Base exception for all ohlcv-hub errors
- `ConfigError(OhlcvHubError)`: Configuration errors (missing env vars)
- `CliUsageError(OhlcvHubError)`: CLI usage errors (invalid arguments)

## Type Definitions (`ohlcv_hub/types.py`)

### Enums
- `Timeframe`: `DAILY = "1d"`, `WEEKLY = "1w"`
- `OutputFormat`: `PARQUET = "parquet"`, `CSV = "csv"`
- `Adjustment`: `RAW = "raw"`, `ALL = "all"`
- `Provider`: `ALPACA = "alpaca"`

## Package Structure

```
ohlcv_hub/
├── __init__.py          # Package metadata, version
├── __main__.py          # Module entry point
├── cli.py               # CLI implementation (Typer)
├── config.py            # Configuration management
├── errors.py            # Custom exceptions
└── types.py             # Type definitions (enums)
```

## Tests

### Test Files
- `tests/test_cli_doctor.py`: Tests for `doctor` command
  - `test_cli_doctor_missing_env_exits_1`: Validates exit code 1 when env vars missing
  - `test_cli_doctor_present_env_exits_0_no_ping`: Validates exit code 0 and secret masking
- `tests/test_cli_fetch_parsing.py`: Tests for `fetch` command argument parsing
  - `test_cli_fetch_parses_and_exits_2`: Validates argument parsing and exit code 2
  - `test_cli_fetch_validates_symbols`: Tests symbol validation
  - `test_cli_fetch_validates_dates`: Tests date format and ordering validation
  - `test_cli_fetch_validates_output_path`: Tests output path validation
  - `test_cli_fetch_normalizes_symbols`: Tests symbol normalization (uppercase, strip spaces)
  - `test_cli_fetch_handles_empty_symbol_segments`: Tests handling of empty segments ("SPY,,QQQ")

### Testing Framework
- Uses `typer.testing.CliRunner` for CLI testing
- No network calls in tests (no `--ping` tests)
- Tests validate exit codes, output content, and error messages

## Dependencies

### Runtime Dependencies
- `httpx>=0.27.0`: HTTP client (used in `doctor --ping`)
- `pandas>=2.2.0`: Dataframe library (not yet used)
- `pyarrow>=15.0.0`: Parquet support (not yet used)
- `typer>=0.12.0`: CLI framework
- `python-dateutil>=2.8.0`: Date parsing
- `pandas_market_calendars>=4.3.0`: Trading calendar (not yet used)

### Dev Dependencies
- `pytest>=8.0.0`: Testing framework

## Key Implementation Details

### Symbol Normalization
- Input: `" spy , qqq , aapl "` → Output: `["SPY", "QQQ", "AAPL"]`
- Handles empty segments: `"SPY,,QQQ"` → `["SPY", "QQQ"]`
- Implemented in `_parse_symbols()` in `cli.py`

### Date Parsing
- Primary format: `YYYY-MM-DD` (strict)
- Fallback: `dateutil.parser.parse()` for flexibility
- Validates start <= end
- Implemented in `_parse_date()` in `cli.py`

### Secret Masking
- Doctor command never prints actual API keys/secrets
- Shows masked version: `"********..."` (8 asterisks minimum)
- Implemented in `doctor` command in `cli.py`

## Not Yet Implemented

- Alpaca API client module (providers)
- Actual data fetching logic
- Pagination handling
- Weekly resampling
- Missing days detection
- Parquet/CSV export
- Data validation

## Next Steps

1. Implement Alpaca client module with pagination support
2. Integrate client into `fetch` command
3. Implement weekly resampling
4. Implement missing days detection
5. Implement export functionality (Parquet/CSV)
