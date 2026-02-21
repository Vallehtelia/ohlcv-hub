# Test stderr capture fix — use caplog only for verbose log assertions

## Location

- **File**: tests/test_fetch_1d_integration_mocked.py
- **Tests**: `test_fetch_verbose_logs_rate_limit_line_when_proactive_throttle`, `test_fetch_no_verbose_omits_rate_limit_log`

## Where result.stderr is used and why it fails

- **test_fetch_verbose_logs_rate_limit_line_when_proactive_throttle** (lines 351–353):
  - `assert result.exit_code == 0, f"Exit code was {result.exit_code}, stderr: {result.stderr}"`
  - `assert "remaining=0" in result.stderr or "Proactive throttle" in result.stderr or "remaining=0" in caplog.text or "Proactive throttle" in caplog.text`
  - Click/Typer CliRunner does not always capture stderr separately; the CLI adds a StreamHandler to the logger only when `--verbose`, so log output may go to the process stderr but not into `result.stderr` in the test process. That makes the assertion flaky or failing in CI.
- **test_fetch_no_verbose_omits_rate_limit_log** (lines 429–430):
  - `assert "remaining=0" not in result.stderr`
  - `assert "Proactive throttle" not in result.stderr`
  - Same issue: relying on result.stderr is unreliable.

## Logger name

Logs are emitted by `ohlcv_hub.providers.alpaca` (AlpacaClient uses that module logger or an injected one with the same name).

## Replacement assertions using caplog

1. **test_fetch_verbose_logs_rate_limit_line_when_proactive_throttle**
   - Add `import logging` if missing; use `caplog.set_level(logging.INFO, logger="ohlcv_hub.providers.alpaca")` at start so pytest captures INFO logs from that logger.
   - After invoke: `assert result.exit_code == 0` (no stderr in message).
   - Assert: `assert "Proactive throttle" in caplog.text` and `assert "remaining=0" in caplog.text` (stable substrings). Do not use result.stderr.

2. **test_fetch_no_verbose_omits_rate_limit_log**
   - Add `caplog` to test signature; call `caplog.set_level(logging.INFO, logger="ohlcv_hub.providers.alpaca")`.
   - After invoke: `assert result.exit_code == 0`.
   - Assert: `assert "Proactive throttle" not in caplog.text` and `assert "remaining=0" not in caplog.text`. Do not use result.stderr.
