# Feature 5A Plan — `--feed` CLI Option

## Where feed is currently decided

- **cli.py**: Feed is hardcoded as `"iex"` in both branches:
  - `build_daily_dataset(..., feed="iex")` (around line 184)
  - `build_weekly_dataset(..., feed="iex")` (around line 196)
- **dataset.py**: Both `build_daily_dataset` and `build_weekly_dataset` accept `feed: str | None = "iex"` and pass it to `client.fetch_stock_bars(..., feed=feed)`.
- **providers/alpaca.py**: `fetch_stock_bars(..., feed: str | None = None)`. If `feed` is not None, it is added to request params (`params["feed"] = feed`); if None, no feed param is sent (Alpaca uses its default).
- **doctor --ping**: Uses hardcoded `"feed": "iex"` in `_perform_ping_test` params (line 79). Out of scope for this feature; leave as-is unless we thread feed there too (non-goal).

## How feed flows

1. **CLI** → calls `build_daily_dataset(..., feed="iex")` or `build_weekly_dataset(..., feed="iex")`.
2. **dataset.py** → calls `client.fetch_stock_bars(..., feed=feed)` (feed is always `"iex"` today).
3. **AlpacaClient** → adds `params["feed"] = feed` when `feed is not None`; request goes to Alpaca with `feed=iex`.

No other layers touch feed. Default behavior to preserve: effective feed is `iex` (explicit in CLI/dataset today).

## Test injection approach used now

- Tests **monkeypatch** `ohlcv_hub.cli._make_alpaca_client` to return an `AlpacaClient` built with an `httpx.Client(transport=httpx.MockTransport(mock_handler))`.
- The mock handler inspects the **request** (e.g. URL/params) only if we add that; currently it just returns a fixed JSON response.
- To assert that the client was called with a given feed, we can:
  - **Option A**: In the mock handler, assert `request.url.params.get("feed") == "iex"` (or capture params and assert later).
  - **Option B**: Wrap or spy on `AlpacaClient.fetch_stock_bars` to record the `feed` argument (e.g. a list that we append to in a patched function).
- Option A is simpler: in tests that already use MockTransport, have the handler capture the request and assert `feed` param (or add a test that invokes with `--feed sip` and asserts the request contained `feed=sip`).

## Implementation summary

- Add **Feed** enum in `types.py`: `iex`, `sip`, `boats`, `otc`.
- Add **`--feed`** to `fetch` in `cli.py` with `default=Feed.IEX` (or equivalent), type=Feed; pass `feed.value` (or the chosen default) into `build_daily_dataset` / `build_weekly_dataset`. Reject empty or invalid by using Typer choices (and optionally explicit check for empty string).
- **dataset.py**: Already has `feed` parameter; no signature change except we will pass the CLI-selected feed (string). Keep `feed: str | None = "iex"` for backward compatibility or switch to required str when called from CLI.
- **AlpacaClient**: No change; already accepts `feed: str | None`.
- **Tests**: Add assertion in mock handler that request params include expected `feed` (e.g. default `iex`). Add one test that runs with `--feed sip` and asserts request had `feed=sip`.
- **README**: Short note that `--feed` can be used (e.g. `iex`, `sip`), default `iex`.

## Edge cases

- `--feed ""`: Typer with Enum won’t accept empty string if we use `Feed`; if we allow a raw string, validate and exit 1 with a friendly message when empty or not in allowed set.
- Default: Use `default=Feed.IEX` so behavior is unchanged.
