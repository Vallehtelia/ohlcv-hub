# 2026-02-20: Bootstrap - Project Scaffolding and CLI Skeleton

## What Changed

- **Initial project structure**: Created Python package with setuptools-based packaging
- **CLI framework**: Implemented Typer-based CLI with two commands (`doctor` and `fetch`)
- **Configuration management**: Environment variable loading with validation
- **Error handling**: Custom exception hierarchy for better error categorization
- **Test suite**: Comprehensive tests for CLI commands using Typer's CliRunner
- **Project metadata**: README, LICENSE, .gitignore files

## Files Created

### Packaging / Metadata
- `pyproject.toml` - Setuptools configuration with dependencies and entry points
- `README.md` - Basic usage and installation instructions
- `LICENSE` - MIT license
- `.gitignore` - Python, IDE, and data file exclusions

### Package Structure
- `ohlcv_hub/__init__.py` - Package metadata and version
- `ohlcv_hub/__main__.py` - Module entry point (`python -m ohlcv_hub`)
- `ohlcv_hub/cli.py` - Main CLI implementation with Typer
- `ohlcv_hub/config.py` - Configuration management (`load_config_from_env()`)
- `ohlcv_hub/errors.py` - Custom exception classes
- `ohlcv_hub/types.py` - Type definitions (enums for Timeframe, OutputFormat, etc.)

### Tests
- `tests/__init__.py` - Test package marker
- `tests/test_cli_doctor.py` - Tests for doctor command
- `tests/test_cli_fetch_parsing.py` - Tests for fetch command argument parsing

### Documentation
- `docs/changes/2026-02-20-bootstrap.md` - This file
- Updated `docs/process.md` - Added bootstrap entry

## Key Decisions / Tradeoffs

### 1. Error Handling Strategy
- **Decision**: Custom exception hierarchy (`OhlcvHubError` → `ConfigError`, `CliUsageError`)
- **Rationale**: Better error categorization and handling at different levels
- **Tradeoff**: More code, but clearer error semantics

### 2. Symbol Normalization
- **Decision**: Uppercase, strip spaces, filter empty segments
- **Rationale**: Handles user input variations gracefully ("SPY,,QQQ" → ["SPY", "QQQ"])
- **Tradeoff**: May mask some user errors, but improves UX

### 3. Date Parsing
- **Decision**: Primary YYYY-MM-DD format, fallback to dateutil parser
- **Rationale**: Strict format preferred, but flexible parsing for edge cases
- **Tradeoff**: Slightly more complex, but handles various input formats

### 4. Secret Masking
- **Decision**: Never print actual secrets, only masked versions
- **Rationale**: Security best practice, prevents accidental exposure
- **Tradeoff**: Less debugging info, but safer

### 5. Exit Codes
- **Decision**: 
  - 0 = success
  - 1 = configuration/validation error
  - 2 = feature not implemented
- **Rationale**: Clear distinction between error types
- **Tradeoff**: Non-standard exit code 2, but clearly indicates incomplete feature

### 6. Testing Approach
- **Decision**: Use Typer's CliRunner, no network tests for now
- **Rationale**: Fast, reliable tests without external dependencies
- **Tradeoff**: Doesn't test actual API connectivity, but tests are deterministic

## How to Test

### Manual Smoke Test

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package in development mode
pip install -e ".[dev]"

# Test doctor command (should fail without env vars)
ohlcv-hub doctor
# Expected: Exit code 1, error message about missing env vars

# Set environment variables
export ALPACA_API_KEY=test_key_12345
export ALPACA_API_SECRET=test_secret_67890

# Test doctor command (should succeed)
ohlcv-hub doctor
# Expected: Exit code 0, "Configuration OK" message, masked secrets

# Test doctor with ping (requires valid API keys)
ohlcv-hub doctor --ping
# Expected: Exit code 0, API connectivity test passed (if keys are valid)

# Test fetch command (should exit with code 2)
ohlcv-hub fetch --symbols SPY,QQQ --start 2015-01-01 --end 2015-02-01 --tf 1d --out ./data
# Expected: Exit code 2, "not implemented" message, parsed configuration printed

# Test fetch with invalid arguments
ohlcv-hub fetch --symbols "" --start 2015-01-01 --end 2015-02-01 --tf 1d --out ./data
# Expected: Exit code 1, error about missing symbols

ohlcv-hub fetch --symbols SPY --start 2015-02-01 --end 2015-01-01 --tf 1d --out ./data
# Expected: Exit code 1, error about start > end

# Run tests
pytest -q
# Expected: All tests pass
```

### Automated Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli_doctor.py

# Run with coverage (if pytest-cov installed)
pytest --cov=ohlcv_hub --cov-report=html
```

## Follow-ups / TODOs

### Immediate Next Steps
1. **Implement Alpaca API Client** (`ohlcv_hub/providers/alpaca.py`):
   - HTTP client wrapper with authentication
   - Request building with query parameters
   - Response parsing and pagination handling
   - Error handling (rate limits, auth failures)

2. **Implement Fetch Command Logic**:
   - Call Alpaca API client
   - Handle pagination across multiple symbols
   - Parse timestamps (RFC-3339 → UTC datetime)
   - Store data in pandas DataFrame

3. **Implement Weekly Resampling**:
   - Group by symbol
   - Resample with `W-MON` frequency
   - Aggregate OHLCV fields correctly

4. **Implement Missing Days Detection**:
   - Load NYSE calendar using `pandas_market_calendars`
   - Compare expected vs retrieved trading days
   - Generate report (JSON/CSV)

5. **Implement Export Functionality**:
   - Parquet export with schema definition
   - CSV export option
   - Partitioning strategy (by symbol and date range)

### Future Enhancements
- Add verbose/debug logging flags
- Add progress bars for long-running operations
- Add retry logic for API requests
- Add caching for API responses
- Add integration tests with mocked API responses
- Add CI/CD workflows (GitHub Actions)
- Add more comprehensive error messages
- Add configuration file support (in addition to env vars)

## Notes

- Package is fully installable and functional for CLI skeleton
- All tests pass with `pytest -q`
- CLI entrypoint works: `ohlcv-hub doctor` and `ohlcv-hub fetch ...`
- No actual data fetching implemented yet (exits with code 2)
- Doctor command's `--ping` flag requires valid API keys to work
