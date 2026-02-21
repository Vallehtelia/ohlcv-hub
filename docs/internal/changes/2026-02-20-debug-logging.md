# 2026-02-20: Optional debug logging for rate-limit and 429 retries

## What changed

- **AlpacaClient** accepts an optional `logger: logging.Logger | None`. When set and enabled for INFO, it logs one-line messages for:
  - **Proactive throttle**: remaining, reset, computed sleep seconds (capped), and reason.
  - **429 retry**: attempt number, computed sleep seconds (capped), and strategy (Retry-After, X-RateLimit-Reset, or backoff).
- Module logger uses a NullHandler and default level WARNING so no output when no logger is configured.
- **CLI** `fetch` has `--verbose` / `--no-verbose` (default off). When `--verbose`, the CLI sets the `ohlcv_hub.providers.alpaca` logger to INFO and adds a StreamHandler to stderr, then passes that logger into `_make_alpaca_client`. Behavior is unchanged when verbose is not enabled.

## Files touched

- `ohlcv_hub/providers/alpaca.py` — logging import, module logger, optional `logger` in `__init__`, `_compute_sleep_seconds_for_429` returns `(secs, strategy)`, INFO logs in proactive gate and 429 loop.
- `ohlcv_hub/cli.py` — `--verbose` option, `_make_alpaca_client(config, logger=None)`, verbose logger setup and pass-through.
- `tests/test_fetch_1d_integration_mocked.py` — `make_mock_client` accepts `logger=None` in all tests; new tests `test_fetch_verbose_logs_rate_limit_line_when_proactive_throttle`, `test_fetch_no_verbose_omits_rate_limit_log`.
- `tests/test_fetch_1w_integration_mocked.py` — `make_mock_client` accepts `logger=None`.
- `docs/llm-handoff/feature5d-debug-logging-plan-2026-02-20.md` — plan.
- `docs/changes/2026-02-20-debug-logging.md` — this file.

## How to test

- **Automated**: `pytest -q` (all tests pass).
- **Manual**: `ohlcv-hub fetch --symbols SPY --start 2024-01-01 --end 2024-01-10 --tf 1d --out ./data --verbose` and confirm rate-limit/retry lines when they occur; without `--verbose` no such lines.

## TODOs

- **Structured logging**: Use structured fields (e.g. JSON or key=value) for easier parsing.
- **Log levels**: Different levels for throttle vs retry (e.g. DEBUG for backoff details).
- **--quiet**: Add a `--quiet` flag to suppress normal progress messages (distinct from verbose).
