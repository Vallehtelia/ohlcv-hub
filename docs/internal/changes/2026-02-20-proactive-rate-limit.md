# 2026-02-20: Proactive rate-limit throttling (X-RateLimit-*)

## What changed

- **AlpacaClient** now uses Alpaca’s `X-RateLimit-*` response headers to throttle **before** the next request when the previous response indicated the limit is nearly exhausted.
- **Parsed headers** (on any response, including 200 and 429): `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (unix epoch seconds). Stored in a simple in-client rate state updated after each response.
- **Pre-request gate**: Before each pagination request, if we have both `remaining` and `reset` and `remaining <= 1`, we sleep `max(0, reset - now + 0.25)` seconds, capped at 10.0s. Uses the injected `sleeper` (and optional `now`) so tests do not actually sleep.
- **No double-sleep**: Proactive sleep runs only at the start of a loop iteration using state from the **prior** response. The existing 429 retry/backoff path is unchanged and runs only when a response is 429.
- **Optional `now`**: `AlpacaClient.__init__` now accepts optional `now: Callable[[], float]` (default `time.time`) for deterministic tests.

## Files touched

- `ohlcv_hub/providers/alpaca.py` — constants `SAFETY_BUFFER_SECONDS`, `MAX_PROACTIVE_SLEEP_SECONDS`; `_parse_rate_limit_headers`; `now` injection; pre-request gate and rate-state update in `fetch_stock_bars`.
- `tests/test_alpaca_client_pagination.py` — `test_proactive_sleep_when_remaining_exhausted_then_succeeds`, `test_no_sleep_when_headers_missing`.
- `docs/llm-handoff/feature5c-proactive-throttle-plan-2026-02-20.md` — plan.
- `docs/changes/2026-02-20-proactive-rate-limit.md` — this file.

## How to test

- **Automated**: `pytest -q` (all tests pass; no real sleep in tests).
- **Manual**: Call Alpaca with enough requests to see rate-limit headers; confirm client waits before the next request when remaining is low.

## Notes on why headers are preferred

- Alpaca’s numeric limits can change; `X-RateLimit-Limit` and `X-RateLimit-Remaining` are the source of truth per response.
- Using headers avoids hardcoding a fixed delay or request count and keeps behavior correct if Alpaca adjusts limits or adds new products.
