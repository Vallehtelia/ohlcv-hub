# Process Log

This document tracks the development process, decisions, and learnings in an append-only format.

## Log

### 2025-02-20: Verification Spike - Alpaca Market Data API Research

**What I Did**:
- Researched Alpaca Market Data API v2 historical stock bars endpoint documentation
- Documented exact API contract including:
  - Base URLs (production: `data.alpaca.markets`, sandbox: `data.sandbox.alpaca.markets`)
  - Endpoint path: `GET /v2/stocks/bars`
  - Authentication headers: `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`
  - Query parameters: `symbols` (comma-separated), `timeframe` (1Day for daily), `start`/`end` (RFC-3339 or YYYY-MM-DD), `limit` (1-10000, global not per-symbol), `adjustment` (raw/split/dividend/spin-off/all), `feed` (sip/iex/boats/otc), `asof` (for symbol name changes), `page_token` (for pagination)
  - Response structure: `bars` object (symbol → array of bars), `next_page_token`, `currency`
  - Bar fields: `t` (timestamp RFC-3339), `o`/`h`/`l`/`c` (prices), `v` (volume), `n` (trade_count), `vw` (VWAP)
  - Pagination semantics: sorted by symbol first, then timestamp; limit is global across all symbols
- Researched and selected MVP tech stack:
  - HTTP client: **httpx** (modern, async-ready, type-annotated)
  - Dataframe: **pandas + pyarrow** (mature, sufficient for MVP, can migrate to Polars later)
  - CLI: **typer** (type-hint based, less boilerplate than Click)
  - Time handling: **zoneinfo** (built-in) + **python-dateutil** (parsing)
  - Trading calendar: **pandas_market_calendars** (active, MIT license)
  - Weekly resample policy: **Monday 00:00 UTC** (deterministic, simple)
- Created three documentation files:
  - `docs/llm-handoff/alpaca-market-data-bars.md` - Complete API contract with edge cases
  - `docs/llm-handoff/mvp-tech-choices.md` - Tech stack decisions with justifications
  - `docs/process.md` - This process log

**Key Decisions**:
1. **Pagination Strategy**: Must handle symbol-first sorting - when querying multiple symbols, pagination may return only one symbol per page if it hits the limit. Need to track which symbols are complete.
2. **Weekly Resample**: Chose Monday 00:00 UTC over "first trading day" for MVP simplicity. Can add trading-day-based option later if needed.
3. **Dataframe Choice**: pandas over Polars for MVP - performance not critical for daily/weekly bars, better ecosystem, easier migration path later.
4. **Missing Days Detection**: Use `pandas_market_calendars` to get expected trading days, compare against retrieved bars to identify gaps.

**Open Questions**:
1. **Rate Limits**: Exact rate limit per minute not confirmed - need to check `X-RateLimit-Limit` header with actual API calls. Default appears to be ~100/min.
2. **Daily Bar Timestamps**: Documentation shows `04:00:00Z` for daily bars (midnight ET). Need to verify this is consistent.
3. **Adjustment Semantics**: `adjustment="all"` behavior - need to test to confirm how prices/volumes are adjusted for splits vs dividends.
4. **Symbol Mapping Timing**: `asof` parameter works "the day after" a rename. Need to verify this delay doesn't cause issues.
5. **Parquet Partitioning Strategy**: Need to decide on partition granularity (by symbol? by date range? both?) for optimal query performance.

**Next Steps for Implementation**:
1. Set up Python project structure (`pyproject.toml`, virtual environment)
2. Install dependencies (httpx, pandas, pyarrow, typer, python-dateutil, pandas_market_calendars)
3. Implement Alpaca API client:
   - Authentication header handling
   - Request building with query parameters
   - Response parsing (handle pagination)
   - Error handling (rate limits, auth failures)
4. Implement data fetching:
   - Multi-symbol request handling
   - Pagination loop (track symbols, handle `next_page_token`)
   - Timestamp parsing (RFC-3339 → UTC datetime)
5. Implement weekly resampling:
   - Group by symbol
   - Resample with `W-MON` frequency
   - Aggregate OHLCV fields correctly
6. Implement missing days detection:
   - Load NYSE calendar
   - Compare expected vs retrieved trading days
   - Generate report
7. Implement Parquet export:
   - Schema definition
   - Partitioning strategy
   - Compression settings
8. Implement CLI:
   - Commands: fetch, resample, validate, export
   - Options: symbols, date range, adjustment, feed
9. Add tests:
   - Mock Alpaca API responses
   - Test pagination logic
   - Test resampling correctness
   - Test missing days detection

**Notes**:
- All API contract details are documented in `alpaca-market-data-bars.md` with citations
- Tech choices are justified in `mvp-tech-choices.md` with tradeoffs
- Process log will be updated as implementation progresses

---

### 2026-02-20: Bootstrap - Project Scaffolding and CLI Skeleton

**What I Did**:
- Created initial project structure with setuptools-based packaging
- Implemented `pyproject.toml` with all required dependencies (httpx, pandas, pyarrow, typer, python-dateutil, pandas_market_calendars)
- Created package structure:
  - `ohlcv_hub/__init__.py` - Package metadata
  - `ohlcv_hub/errors.py` - Custom exception hierarchy (OhlcvHubError, ConfigError, CliUsageError)
  - `ohlcv_hub/config.py` - Configuration management with `load_config_from_env()`
  - `ohlcv_hub/types.py` - Type definitions (Timeframe, OutputFormat, Adjustment, Provider enums)
  - `ohlcv_hub/cli.py` - Main CLI implementation with Typer
  - `ohlcv_hub/__main__.py` - Module entry point
- Implemented `doctor` command:
  - Validates environment variables (ALPACA_API_KEY, ALPACA_API_SECRET)
  - Optional `--ping` flag to test API connectivity
  - Performs authenticated test request to Alpaca bars endpoint with 10s timeout
  - Masks secrets in output (never prints actual keys)
- Implemented `fetch` command skeleton:
  - Parses and validates all arguments (symbols, dates, timeframe, output path, etc.)
  - Normalizes symbols (uppercase, strips spaces, handles empty segments)
  - Validates date format and ordering (start <= end)
  - Prints parsed configuration and exits with code 2 (not implemented)
- Created comprehensive test suite:
  - `test_cli_doctor.py` - Tests for doctor command (missing env, present env, secret masking)
  - `test_cli_fetch_parsing.py` - Tests for fetch argument parsing and validation
- Added project metadata files:
  - `README.md` - Basic usage and installation instructions
  - `LICENSE` - MIT license
  - `.gitignore` - Python, IDE, and data file exclusions

**Key Decisions**:
1. **Error Handling**: Custom exception hierarchy for better error categorization (ConfigError, CliUsageError)
2. **Symbol Normalization**: Uppercase and strip spaces, filter empty segments (handles "SPY,,QQQ" gracefully)
3. **Date Parsing**: Support YYYY-MM-DD format primarily, fallback to dateutil for flexibility
4. **Secret Masking**: Doctor command never prints actual secrets, only masked versions
5. **Exit Codes**: 
   - 0 = success
   - 1 = configuration/validation error
   - 2 = feature not implemented (fetch command)
6. **Testing Strategy**: Use Typer's CliRunner for CLI testing, mock-free for now (no network tests)

**Open Questions**:
1. Should we add more detailed error messages for invalid date formats?
2. Should fetch command create output directory if it doesn't exist, or require it to exist?
3. Should we add verbose/debug logging flags?

**Next Steps**:
1. Implement actual Alpaca API client (fetching with pagination)
2. Implement weekly resampling logic
3. Implement missing days detection and reporting
4. Implement Parquet/CSV export functionality
5. Add integration tests with mocked API responses
6. Add CI/CD workflows

**Notes**:
- Package is installable with `pip install -e ".[dev]"`
- CLI entrypoint works: `ohlcv-hub doctor` and `ohlcv-hub fetch ...`
- All tests pass with `pytest -q`

---

### 2026-02-20: Security baseline, CI, and PyPI publish workflow

**What I Did**:
- Added security tooling to dev extras: `bandit>=1.7.0`, `pip-audit>=2.7.0`.
- Switched setuptools to package discovery via `[tool.setuptools.packages.find]` so `ohlcv_hub` and subpackages are included.
- Created `SECURITY.md` with vulnerability reporting and a note to never share API secrets in issues/logs.
- Added GitHub Actions: `ci.yml` (tests + bandit + pip-audit on push/PR to main; matrix Python 3.9–3.12); `publish.yml` (on tag `v*`, build sdist/wheel and publish to PyPI via Trusted Publishing).
- Documented in `docs/changes/2026-02-20-security-ci-publish.md` how to run checks locally and how to release (version bump, changelog, tag, push, Trusted Publishing on PyPI).

**Key Decisions**:
- CI fails on pip-audit findings (strict) to keep dependency hygiene.
- Publish uses PyPI Trusted Publishing (OIDC, no API token in repo); README/docs describe configuring it on the PyPI project.

**Notes**:
- No product code or runtime behavior changed.
- `.github/` did not exist before; workflows are new.
