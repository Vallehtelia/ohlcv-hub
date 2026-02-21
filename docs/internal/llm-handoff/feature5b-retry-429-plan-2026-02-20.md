# Feature 5B Plan — Retry/backoff for HTTP 429

## Current AlpacaClient request loop structure

In `ohlcv_hub/providers/alpaca.py`, `fetch_stock_bars`:

1. Validates limit and symbols, builds base `params`, sets `page_token = None`.
2. **Pagination loop** (`while True`):
   - Builds `current_params = params.copy()`; if `page_token` set, adds `page_token`.
   - **Single request**: `response = http_client.get(url, params=current_params, headers=headers)`.
   - **If status_code != 200**: raises `ProviderError` immediately with `status_code` and truncated body (no retry).
   - Parses JSON; on failure raises `ProviderError`.
   - Merges `bars`, updates `currency`, reads `next_page_token`; if null/empty, `break`; else `page_token = next_token`.
3. `finally`: closes client if we created it.
4. Returns `BarsResponse`.

**Where to insert retry**: Only for the **single GET request** step when `response.status_code == 429`. So: after `response = http_client.get(...)`, if `response.status_code == 429`, enter a retry sub-loop (sleep using injectable sleeper, then re-do the same `http_client.get(url, params=current_params, headers=headers)`). Do not retry for 401/403/400/500 etc.; preserve current behavior (raise immediately). After retries exhausted for 429, raise `ProviderError(status_code=429, message=... retries exhausted)`.

## Current ProviderError usage

- **errors.py**: `ProviderError(message, status_code=None)`; `status_code` stored on the instance.
- **alpaca.py**: Raised when `response.status_code != 200` with message `f"API request failed with status {response.status_code}: {error_text}"`, and when JSON decode fails. No special case for 429 today.

## How tests currently assert request sequences

- **test_paginates_until_token_exhausted_and_merges_symbols**: Uses a **request_count** and **received_page_tokens** list; the mock handler increments count and appends `page_token` from params. Asserts `request_count == 2` and `received_page_tokens == ["tok1"]`.
- **test_raises_provider_error_on_non_200**: Single handler that always returns 401; asserts `ProviderError` with `status_code == 401`.
- **test_handles_empty_next_page_token_string**: Asserts `request_count == 1`.

So tests rely on **counters and lists** inside the mock handler (closure or nonlocal). For retry tests we will:
- Use a **request counter** to know how many times the transport was called.
- Use an **injected sleeper** (spy) that records `(seconds,)` in a list and does not call `time.sleep`, so tests run fast and we can assert sleeper was called with expected values.

## Implementation notes

- **Sleeper injection**: Add optional `sleeper: Callable[[float], None]` to `AlpacaClient.__init__` (default `time.sleep`). In tests pass a spy that appends to a list.
- **Backoff logic**: Prefer `Retry-After` (seconds, cap 5); else `X-RateLimit-Reset` (wait = reset - now, cap 5, floor 0); else exponential 0.5, 1, 2, 4 (cap 5). Use attempt index (0-based) for exponential.
- **Total attempts**: 1 initial + 5 retries = 6 total attempts per request before raising.
