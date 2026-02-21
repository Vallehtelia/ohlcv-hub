# Feature 5D — Optional debug logging (verification spike)

## Where rate-limit sleeps happen and what context is available

1. **Proactive throttle** (in `fetch_stock_bars`, at top of pagination loop, before the GET):
   - Condition: `last_remaining` and `last_reset` are set and `last_remaining <= 1`.
   - We have: `last_remaining`, `last_reset`, computed `wait_secs` (after cap/floor).
   - We can log: remaining, reset, wait_secs (capped), and reason ("proactive throttle: remaining exhausted").

2. **429 retry** (inside the `while response.status_code == 429` loop):
   - We have: `response`, `retries_used` (0-based attempt index), and `sleep_secs` from `_compute_sleep_seconds_for_429(response, retries_used)`.
   - Strategy used is determined inside `_compute_sleep_seconds_for_429`: Retry-After, then X-RateLimit-Reset, then exponential backoff. To log which strategy was used we can either (a) return (secs, strategy_name) from that helper, or (b) log inside the helper when a logger is available. Option (a) keeps the helper pure and lets the caller log one line (attempt, sleep_secs, strategy).

## Current injection points

- **AlpacaClient.__init__**: `http`, `sleeper`, `now` are optional; no logger today.
- **CLI**: `_make_alpaca_client(config)` builds the client with only config-derived args (api_key, api_secret, base_url). No verbose or logger is passed.

## Best place to plumb verbose from CLI to AlpacaClient

- **Option A — Logger injection**: Add optional `logger: logging.Logger | None = None` to `AlpacaClient`. Default: use `logging.getLogger(__name__)` with a NullHandler and default level WARNING so no output when not configured. When CLI runs with `--verbose`, create a logger (or use the same module logger), set level to INFO, add a `StreamHandler(sys.stderr)`, and pass that logger into `_make_alpaca_client`; have `_make_alpaca_client` accept an optional `logger` and pass it to `AlpacaClient`. So we need to change `_make_alpaca_client(config, logger=None)` and the fetch command to pass a verbose logger when `--verbose` is True.
- **Option B — Configure module logger in CLI**: No logger argument to AlpacaClient. In alpaca.py use `logger = logging.getLogger(__name__)` and add `NullHandler()` and set level WARNING. When CLI runs with `--verbose`, get the logger for `ohlcv_hub.providers.alpaca`, set level to INFO, add a StreamHandler to stderr. Then AlpacaClient just uses the module logger; no signature change to _make_alpaca_client. Prefer Option B for minimal API surface; if we want tests to assert on log output without touching the global logger, we can inject a logger in tests (so Option A is more testable). The requirement says "Tests must remain offline and deterministic" and "Add a logger: ... OR debug: bool ... Prefer logger injection". So prefer **logger injection**: add optional `logger` to AlpacaClient; CLI when verbose creates a logger with StreamHandler and passes it to _make_alpaca_client(config, logger=verbose_logger). When not verbose, pass logger=None and AlpacaClient uses module logger with NullHandler/WARNING so no output.

Summary: Add `logger: Optional[logging.Logger] = None` to AlpacaClient. Default: module logger with NullHandler and setLevel(WARNING). CLI fetch: add `--verbose`; when True, create a logger for "ohlcv_hub.providers.alpaca" with INFO and StreamHandler(stderr), pass to _make_alpaca_client(config, logger=...). In tests, pass a custom logger with a MemoryHandler or capture log records to assert without real output.
