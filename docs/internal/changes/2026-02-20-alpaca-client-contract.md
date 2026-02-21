# 2026-02-20: Alpaca Client Contract & Pagination Behavior

## What Changed

- **Added Alpaca client module**: Implemented `AlpacaClient` class with pagination support
- **Added ProviderError**: New exception type for provider API errors
- **Added BarsResponse dataclass**: Response structure for bars data
- **Comprehensive pagination tests**: Tests using httpx MockTransport to verify contract

## Files Created

### Provider Module
- `ohlcv_hub/providers/__init__.py` - Module exports
- `ohlcv_hub/providers/alpaca.py` - AlpacaClient implementation with pagination

### Tests
- `tests/test_alpaca_client_pagination.py` - Contract tests for Alpaca client

### Documentation
- `docs/changes/2026-02-20-alpaca-client-contract.md` - This file
- `docs/llm-handoff/current-state-2026-02-20.md` - Current state summary

## Files Modified

- `ohlcv_hub/errors.py` - Added `ProviderError` exception class
- `pyproject.toml` - Added `ohlcv_hub.providers` to packages

## Key Decisions / Tradeoffs

### 1. Explicit Method Signature
- **Decision**: `fetch_stock_bars()` uses explicit parameters instead of `**kwargs`
- **Rationale**: Better type safety, clearer API contract, easier to validate
- **Tradeoff**: More verbose, but more maintainable

### 2. BarsResponse Dataclass
- **Decision**: Return `BarsResponse` dataclass instead of raw dict
- **Rationale**: Type safety, clear structure, easier to extend
- **Tradeoff**: Slight overhead, but better API design

### 3. Pagination Merging Strategy
- **Decision**: Merge bars by symbol across pages, preserve order within each symbol
- **Rationale**: Matches Alpaca API behavior (symbol-first sorting), maintains data integrity
- **Tradeoff**: Client-side merging required, but ensures complete data

### 4. Error Handling
- **Decision**: Raise `ProviderError` with status_code for all API errors
- **Rationale**: Clear error categorization, preserves HTTP status information
- **Tradeoff**: More exception types, but better error handling

### 5. HTTP Client Injection
- **Decision**: Allow optional `http` parameter for testing
- **Rationale**: Enables MockTransport in tests, no real network calls
- **Tradeoff**: Slightly more complex initialization, but essential for testing

### 6. Date Serialization
- **Decision**: Support `date`, `datetime`, and `str` inputs, serialize to ISO date format
- **Rationale**: Flexible input types, consistent output format
- **Tradeoff**: More code, but better UX

### 7. Symbol Normalization
- **Decision**: Normalize symbols to uppercase and strip spaces
- **Rationale**: Consistent with Alpaca API expectations, handles user input variations
- **Tradeoff**: May mask some errors, but improves usability

## Implementation Details

### AlpacaClient Class

**Initialization**:
- `api_key`: Alpaca API key (required)
- `api_secret`: Alpaca API secret (required)
- `base_url`: Base URL (default: `https://data.alpaca.markets`)
- `timeout_seconds`: Request timeout (default: 10.0)
- `http`: Optional httpx.Client for injection (testing)

**Methods**:
- `fetch_stock_bars()`: Main method for fetching bars with pagination
  - Parameters: symbols, timeframe, start, end, limit, adjustment, feed, asof, sort
  - Returns: `BarsResponse` with merged bars and currency
  - Raises: `ValueError` for invalid inputs, `ProviderError` for API errors

**Pagination Logic**:
1. Build initial request with query parameters
2. Loop until `next_page_token` is None or empty string
3. For each page:
   - Add `page_token` parameter if continuing pagination
   - Make HTTP GET request
   - Parse JSON response
   - Merge bars by symbol (extend lists)
   - Extract currency (from any page)
   - Check `next_page_token` to continue or stop

**Error Handling**:
- Non-200 status codes → `ProviderError` with status_code
- JSON parse errors → `ProviderError` with status_code=200 (if HTTP was 200)
- Invalid limit → `ValueError`
- Empty symbols → `ValueError`

### BarsResponse Dataclass

```python
@dataclass
class BarsResponse:
    bars: dict[str, list[dict[str, Any]]]  # symbol -> list of bar objects
    currency: str | None = None
```

### ProviderError Exception

```python
class ProviderError(OhlcvHubError):
    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
```

## Test Coverage

### Test Cases

1. **test_sets_auth_headers**: Verifies authentication headers are set correctly
2. **test_paginates_until_token_exhausted_and_merges_symbols**: 
   - Tests pagination loop with multiple pages
   - Verifies symbol merging across pages
   - Tests page_token parameter usage
   - Verifies currency extraction
3. **test_raises_provider_error_on_non_200**: Tests error handling for non-200 status codes
4. **test_raises_provider_error_on_json_parse_error**: Tests error handling for invalid JSON
5. **test_validates_limit_range**: Tests limit validation (1-10000)
6. **test_normalizes_symbols**: Tests symbol normalization (uppercase, strip spaces)
7. **test_handles_empty_next_page_token_string**: Tests that empty string stops pagination
8. **test_serializes_date_objects**: Tests date/datetime serialization

### Testing Strategy

- **MockTransport**: All tests use `httpx.MockTransport` to avoid real network calls
- **Deterministic**: Tests are deterministic and fast
- **Contract-focused**: Tests verify API contract (headers, params, pagination behavior)
- **Edge cases**: Tests cover error cases, empty tokens, date serialization

## How to Test

### Automated Tests

```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_alpaca_client_pagination.py -v

# Run with coverage
pytest --cov=ohlcv_hub.providers --cov-report=html
```

### Manual Smoke Test

```bash
# Verify module can be imported
python -c "from ohlcv_hub.providers.alpaca import AlpacaClient; print('ok')"

# Verify BarsResponse can be imported
python -c "from ohlcv_hub.providers.alpaca import BarsResponse; print('ok')"

# Verify ProviderError can be imported
python -c "from ohlcv_hub.errors import ProviderError; print('ok')"
```

### Integration Test (requires API keys)

```python
from ohlcv_hub.providers.alpaca import AlpacaClient
from ohlcv_hub.config import load_config_from_env

config = load_config_from_env()
client = AlpacaClient(
    api_key=config.alpaca_api_key,
    api_secret=config.alpaca_api_secret,
    base_url=config.alpaca_data_base_url,
)

# Fetch bars for a single symbol
result = client.fetch_stock_bars(
    symbols=["SPY"],
    timeframe="1Day",
    start="2024-01-01",
    end="2024-01-10",
    limit=5,
)

print(f"Fetched {len(result.bars.get('SPY', []))} bars for SPY")
print(f"Currency: {result.currency}")
```

## TODOs / Follow-ups

### Immediate Next Steps
1. **Integrate into fetch command**: Wire up `AlpacaClient` into `ohlcv_hub/cli.py` fetch command
2. **Timestamp parsing**: Parse RFC-3339 timestamps from Alpaca responses into datetime objects
3. **DataFrame conversion**: Convert raw bar dicts to pandas DataFrame
4. **Error handling in CLI**: Handle `ProviderError` gracefully in fetch command

### Future Enhancements
1. **Pagination limits**: Add configurable max pages limit to prevent infinite loops
2. **Retry logic**: Add retry logic for transient errors (429 rate limits, 500 errors)
3. **Rate limit handling**: Parse `X-RateLimit-*` headers and handle 429 responses
4. **Async support**: Consider async version for concurrent requests
5. **Caching**: Add optional caching for repeated requests
6. **Request logging**: Add optional request/response logging for debugging
7. **Progress tracking**: Add progress indicators for long-running fetches

### Integration Points
- **CLI fetch command**: Replace "not implemented" message with actual fetch logic
- **Weekly resampling**: Use fetched bars as input for resampling
- **Missing days detection**: Use fetched bars to compare against trading calendar
- **Export functionality**: Use fetched bars for Parquet/CSV export

## Notes

- **No network calls in tests**: All tests use MockTransport, no real API calls
- **CLI unchanged**: Fetch command still exits with code 2, no integration yet
- **Type hints**: Full type hints for better IDE support and type checking
- **Documentation**: API contract documented in code docstrings
- **Error messages**: Clear error messages with status codes for debugging

## Verification Checklist

- [x] AlpacaClient class implemented with pagination
- [x] ProviderError exception added
- [x] BarsResponse dataclass defined
- [x] Tests use MockTransport (no real network)
- [x] Tests verify auth headers
- [x] Tests verify pagination loop
- [x] Tests verify symbol merging
- [x] Tests verify error handling
- [x] Tests verify parameter validation
- [x] Module can be imported
- [x] All tests pass
