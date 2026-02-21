# Feature 5C — Proactive rate-limit throttling (verification spike)

## Where response objects are available

- In `fetch_stock_bars`, the pagination loop does:
  1. `response = http_client.get(url, params=current_params, headers=headers)`
  2. Then a 429 retry inner loop that may re-assign `response` from repeated GETs
  3. After that, `response.status_code`, `response.text`, `response.json()`, and thus `response.headers` are available for the last response
- So we can read `response.headers` (e.g. `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) on **any** response—200 or 429—after each GET (and after the 429 retry loop). We will update a small in-client "rate state" (e.g. remaining, reset) after every response, then use that state **before** the next request in the next loop iteration.

## Current sleeper injection

- `AlpacaClient.__init__` takes optional `sleeper: Optional[Callable[[float], None]] = None` and stores it as `self._sleep` (default `time.sleep`). Used in the 429 retry path only today.
- We will reuse the same `self._sleep` for proactive throttling so tests can inject a spy and avoid real sleep. Proactive sleep is capped at 10.0s (separate from the 429 retry cap of 5.0s).

## Current retry loop structure (to avoid double-sleep)

- Structure today:
  - **Top of loop:** build `current_params`, optionally add `page_token`.
  - **Then:** single `response = http_client.get(...)`.
  - **Then:** `while response.status_code == 429 and retries_used < MAX_RETRIES_PER_REQUEST`: compute sleep via `_compute_sleep_seconds_for_429`, `self._sleep(sleep_secs)`, retries_used += 1, `response = http_client.get(...)` again.
  - **Then:** if status != 200, raise ProviderError (including 429 exhausted).
  - **Then:** parse JSON, merge bars, read `next_page_token`; if present set `page_token` and continue loop; else break.
- To add proactive throttling without double-sleep:
  - **After** we have a response (after the 429 retry block), parse and update rate state from `response.headers` (for both 200 and 429).
  - **Before** the initial GET in each iteration (at the very start of the `while True` body, after building `current_params`): if we have stored "remaining" and "reset" and remaining <= 1, compute proactive sleep = max(0, reset - now + 0.25), cap 10s, then `self._sleep(proactive_sleep)`. This uses state from the **prior** response only. First iteration has no prior response, so no proactive sleep. When we do get a 429, we still run the existing 429 loop (its own sleep); we do not add an extra proactive sleep for the same attempt—proactive sleep only runs before the *next* request when the *previous* response said we're exhausted.

## Summary

- Response objects: available after each GET (and after 429 retry loop); read headers there and update rate state.
- Sleeper: reuse `self._sleep`; add optional `now` callable (default `time.time`) for deterministic tests.
- Retry loop: keep 429 retry block as-is; add rate-state update after every response; add pre-request gate at top of loop using prior response state so we never double-sleep for the same logical request.
