# 2026-02-21: Test fix — assert verbose logs via caplog only (no result.stderr)

## What changed

The two integration tests that assert on rate-limit/verbose log output now use pytest’s `caplog` only. They no longer read `result.stderr` from the Typer CliRunner.

## Why stderr wasn’t captured reliably

Typer (and Click) CliRunner runs the app in-process. When the CLI adds a `StreamHandler(sys.stderr)` to the logger only when `--verbose`, log records are written to the same process’s stderr. The test runner does not necessarily redirect or capture that stderr into `result.stderr`; capture behavior can differ by environment (local vs CI) and Python version. So assertions on `result.stderr` were flaky or failing in CI. Pytest’s `caplog` fixture captures log records from the logging framework regardless of handlers, so asserting on `caplog.text` is deterministic.

## Files touched

- **tests/test_fetch_1d_integration_mocked.py**  
  - Added `import logging`.  
  - **test_fetch_verbose_logs_rate_limit_line_when_proactive_throttle**: `caplog.set_level(logging.INFO, logger="ohlcv_hub.providers.alpaca")` at start; after invoke, assert `result.exit_code == 0`, then `"Proactive throttle" in caplog.text` and `"remaining=0" in caplog.text`; removed any use of `result.stderr`.  
  - **test_fetch_no_verbose_omits_rate_limit_log**: added `caplog` to signature; same `caplog.set_level(...)`; set `logging.getLogger("ohlcv_hub.providers.alpaca").setLevel(logging.WARNING)` before invoke so the client (which uses the module logger when `logger=None`) does not emit INFO and caplog stays empty of throttle lines; after invoke, assert `"Proactive throttle" not in caplog.text` and `"remaining=0" not in caplog.text`; removed `result.stderr` assertions.
