"""Tests for Alpaca client pagination and contract."""

import json
from datetime import date

import httpx
import pytest

from ohlcv_hub.errors import ProviderError
from ohlcv_hub.providers.alpaca import AlpacaClient, BarsResponse


def test_sets_auth_headers():
    """Test that AlpacaClient sets correct authentication headers."""
    api_key = "test_key_12345"
    api_secret = "test_secret_67890"

    def check_headers(request: httpx.Request) -> httpx.Response:
        """Check that headers are set correctly."""
        assert "APCA-API-KEY-ID" in request.headers
        assert "APCA-API-SECRET-KEY" in request.headers
        assert request.headers["APCA-API-KEY-ID"] == api_key
        assert request.headers["APCA-API-SECRET-KEY"] == api_secret

        # Return empty response
        return httpx.Response(
            200,
            json={"bars": {}, "next_page_token": None},
            request=request,
        )

    transport = httpx.MockTransport(check_headers)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Make a request (will trigger header check)
    alpaca_client.fetch_stock_bars(
        symbols=["SPY"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-02",
        limit=1,
    )


def test_paginates_until_token_exhausted_and_merges_symbols():
    """Test pagination loop continues until next_page_token is null and merges symbols correctly."""
    api_key = "test_key"
    api_secret = "test_secret"

    # Track request count and page_token usage
    request_count = 0
    received_page_tokens = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Handle pagination requests."""
        nonlocal request_count, received_page_tokens

        request_count += 1
        params = dict(request.url.params)

        # Track page_token usage
        if "page_token" in params:
            received_page_tokens.append(params["page_token"])

        # First request: return only AAPL bars with next_page_token
        if request_count == 1:
            assert "page_token" not in params
            return httpx.Response(
                200,
                json={
                    "bars": {
                        "AAPL": [
                            {
                                "t": "2024-01-01T04:00:00Z",
                                "o": 100.0,
                                "h": 101.0,
                                "l": 99.0,
                                "c": 100.5,
                                "v": 1000000,
                                "n": 5000,
                                "vw": 100.25,
                            },
                            {
                                "t": "2024-01-02T04:00:00Z",
                                "o": 100.5,
                                "h": 102.0,
                                "l": 100.0,
                                "c": 101.0,
                                "v": 1100000,
                                "n": 5500,
                                "vw": 101.0,
                            },
                        ]
                    },
                    "next_page_token": "tok1",
                    "currency": "USD",
                },
                request=request,
            )

        # Second request: return AAPL and TSLA bars with no next_page_token
        elif request_count == 2:
            assert params.get("page_token") == "tok1"
            return httpx.Response(
                200,
                json={
                    "bars": {
                        "AAPL": [
                            {
                                "t": "2024-01-03T04:00:00Z",
                                "o": 101.0,
                                "h": 103.0,
                                "l": 100.5,
                                "c": 102.0,
                                "v": 1200000,
                                "n": 6000,
                                "vw": 101.75,
                            }
                        ],
                        "TSLA": [
                            {
                                "t": "2024-01-01T04:00:00Z",
                                "o": 200.0,
                                "h": 205.0,
                                "l": 198.0,
                                "c": 203.0,
                                "v": 2000000,
                                "n": 10000,
                                "vw": 201.5,
                            },
                            {
                                "t": "2024-01-02T04:00:00Z",
                                "o": 203.0,
                                "h": 208.0,
                                "l": 202.0,
                                "c": 206.0,
                                "v": 2100000,
                                "n": 10500,
                                "vw": 205.0,
                            },
                        ],
                    },
                    "next_page_token": None,
                    "currency": "USD",
                },
                request=request,
            )

        # Should not reach here
        return httpx.Response(500, json={"error": "Unexpected request"}, request=request)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Fetch bars for multiple symbols
    result = alpaca_client.fetch_stock_bars(
        symbols=["AAPL", "TSLA"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-03",
        limit=2,  # Small limit to force pagination
    )

    # Verify pagination occurred
    assert request_count == 2
    assert received_page_tokens == ["tok1"]

    # Verify merged results
    assert isinstance(result, BarsResponse)
    assert "AAPL" in result.bars
    assert "TSLA" in result.bars

    # AAPL should have 3 bars (2 from first page, 1 from second page)
    assert len(result.bars["AAPL"]) == 3
    assert result.bars["AAPL"][0]["t"] == "2024-01-01T04:00:00Z"
    assert result.bars["AAPL"][1]["t"] == "2024-01-02T04:00:00Z"
    assert result.bars["AAPL"][2]["t"] == "2024-01-03T04:00:00Z"

    # TSLA should have 2 bars (from second page)
    assert len(result.bars["TSLA"]) == 2
    assert result.bars["TSLA"][0]["t"] == "2024-01-01T04:00:00Z"
    assert result.bars["TSLA"][1]["t"] == "2024-01-02T04:00:00Z"

    # Verify currency
    assert result.currency == "USD"


def test_raises_provider_error_on_non_200():
    """Test that ProviderError is raised on non-200 status codes."""
    api_key = "test_key"
    api_secret = "test_secret"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Return 401 Unauthorized."""
        return httpx.Response(
            401,
            json={"message": "Unauthorized", "code": 401},
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Should raise ProviderError
    with pytest.raises(ProviderError) as exc_info:
        alpaca_client.fetch_stock_bars(
            symbols=["SPY"],
            timeframe="1Day",
            start="2024-01-01",
            end="2024-01-02",
        )

    # Verify error details
    assert exc_info.value.status_code == 401
    assert "401" in str(exc_info.value)
    assert "Unauthorized" in str(exc_info.value) or "failed" in str(exc_info.value).lower()


def test_raises_provider_error_on_json_parse_error():
    """Test that ProviderError is raised on JSON parse errors."""
    api_key = "test_key"
    api_secret = "test_secret"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Return invalid JSON."""
        return httpx.Response(
            200,
            content=b"not valid json {",
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Should raise ProviderError
    with pytest.raises(ProviderError) as exc_info:
        alpaca_client.fetch_stock_bars(
            symbols=["SPY"],
            timeframe="1Day",
            start="2024-01-01",
            end="2024-01-02",
        )

    # Verify error details
    assert exc_info.value.status_code == 200  # Status was 200, but JSON parse failed
    assert "parse" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()


def test_validates_limit_range():
    """Test that limit validation works."""
    api_key = "test_key"
    api_secret = "test_secret"

    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"bars": {}}, request=r))
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Test limit too low
    with pytest.raises(ValueError, match="limit must be between"):
        alpaca_client.fetch_stock_bars(
            symbols=["SPY"],
            timeframe="1Day",
            start="2024-01-01",
            end="2024-01-02",
            limit=0,
        )

    # Test limit too high
    with pytest.raises(ValueError, match="limit must be between"):
        alpaca_client.fetch_stock_bars(
            symbols=["SPY"],
            timeframe="1Day",
            start="2024-01-01",
            end="2024-01-02",
            limit=10001,
        )


def test_normalizes_symbols():
    """Test that symbols are normalized to uppercase."""
    api_key = "test_key"
    api_secret = "test_secret"

    received_symbols = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Capture symbols parameter."""
        params = dict(request.url.params)
        received_symbols.append(params.get("symbols", ""))
        return httpx.Response(
            200,
            json={"bars": {}, "next_page_token": None},
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Pass lowercase symbols with spaces
    alpaca_client.fetch_stock_bars(
        symbols=[" spy ", " qqq ", "aapl"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-02",
    )

    # Verify symbols were normalized
    assert len(received_symbols) == 1
    assert received_symbols[0] == "SPY,QQQ,AAPL"


def test_handles_empty_next_page_token_string():
    """Test that empty string next_page_token stops pagination."""
    api_key = "test_key"
    api_secret = "test_secret"

    request_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Return empty string for next_page_token."""
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-01T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                "next_page_token": "",  # Empty string should stop pagination
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    result = alpaca_client.fetch_stock_bars(
        symbols=["SPY"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-02",
    )

    # Should only make one request
    assert request_count == 1
    assert "SPY" in result.bars


def test_serializes_date_objects():
    """Test that date and datetime objects are serialized correctly."""
    api_key = "test_key"
    api_secret = "test_secret"

    received_params = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Capture request parameters."""
        params = dict(request.url.params)
        received_params.append(params)
        return httpx.Response(
            200,
            json={"bars": {}, "next_page_token": None},
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://data.alpaca.markets",
        http=client,
    )

    # Pass date objects
    alpaca_client.fetch_stock_bars(
        symbols=["SPY"],
        timeframe="1Day",
        start=date(2024, 1, 1),
        end=date(2024, 1, 2),
    )

    # Verify dates were serialized
    assert len(received_params) == 1
    assert received_params[0]["start"] == "2024-01-01"
    assert received_params[0]["end"] == "2024-01-02"


def test_retries_on_429_then_succeeds_without_sleeping_real_time():
    """On 429 with Retry-After, retry same request; sleeper spy used so no real sleep."""
    request_count = 0
    sleep_calls = []

    def sleeper_spy(seconds: float) -> None:
        sleep_calls.append(seconds)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "1"},
                json={"message": "rate limited"},
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-01T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key="key",
        api_secret="secret",
        base_url="https://data.alpaca.markets",
        http=client,
        sleeper=sleeper_spy,
    )

    result = alpaca_client.fetch_stock_bars(
        symbols=["SPY"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-02",
    )

    assert request_count == 2
    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 1.0  # Retry-After: "1" -> 1 second (capped at 5)
    assert "SPY" in result.bars
    assert len(result.bars["SPY"]) == 1


def test_exhausts_retries_and_raises_provider_error_429():
    """When all 429 retries are exhausted, raise ProviderError with status_code 429."""
    request_count = 0
    sleep_calls = []

    def sleeper_spy(seconds: float) -> None:
        sleep_calls.append(seconds)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"message": "rate limited"},
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key="key",
        api_secret="secret",
        base_url="https://data.alpaca.markets",
        http=client,
        sleeper=sleeper_spy,
    )

    with pytest.raises(ProviderError) as exc_info:
        alpaca_client.fetch_stock_bars(
            symbols=["SPY"],
            timeframe="1Day",
            start="2024-01-01",
            end="2024-01-02",
        )

    assert exc_info.value.status_code == 429
    assert "retries exhausted" in str(exc_info.value).lower()
    # 1 initial + 5 retries = 6 total requests
    assert request_count == 1 + 5
    # Sleeper called 5 times (after each 429 before retry)
    assert len(sleep_calls) == 5


def test_proactive_sleep_when_remaining_exhausted_then_succeeds():
    """When first response has X-RateLimit-Remaining<=1 and Reset, sleep before next request then succeed."""
    request_count = 0
    sleep_calls = []
    fixed_now = 1000.0
    reset_ts = 1001  # now+1 -> wait 1 + 0.25 = 1.25s

    def sleeper_spy(seconds: float) -> None:
        sleep_calls.append(seconds)

    def now_fixed() -> float:
        return fixed_now

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(
                200,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_ts),
                },
                json={
                    "bars": {"SPY": [{"t": "2024-01-01T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                    "next_page_token": "tok1",
                    "currency": "USD",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-02T04:00:00Z", "o": 101.0, "h": 102.0, "l": 100.0, "c": 101.5, "v": 1100, "n": 11, "vw": 101.0}]},
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key="key",
        api_secret="secret",
        base_url="https://data.alpaca.markets",
        http=client,
        sleeper=sleeper_spy,
        now=now_fixed,
    )

    result = alpaca_client.fetch_stock_bars(
        symbols=["SPY"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-03",
    )

    assert request_count == 2
    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(1.25, abs=0.01)  # reset - now + 0.25 = 1.25
    assert "SPY" in result.bars
    assert len(result.bars["SPY"]) == 2


def test_no_sleep_when_headers_missing():
    """When responses have no X-RateLimit-* headers, proactive sleeper is never called."""
    request_count = 0
    sleep_calls = []

    def sleeper_spy(seconds: float) -> None:
        sleep_calls.append(seconds)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        # Two pages, no rate limit headers
        if request_count == 1:
            return httpx.Response(
                200,
                json={
                    "bars": {"SPY": [{"t": "2024-01-01T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                    "next_page_token": "tok1",
                    "currency": "USD",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-02T04:00:00Z", "o": 101.0, "h": 102.0, "l": 100.0, "c": 101.5, "v": 1100, "n": 11, "vw": 101.0}]},
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    alpaca_client = AlpacaClient(
        api_key="key",
        api_secret="secret",
        base_url="https://data.alpaca.markets",
        http=client,
        sleeper=sleeper_spy,
    )

    result = alpaca_client.fetch_stock_bars(
        symbols=["SPY"],
        timeframe="1Day",
        start="2024-01-01",
        end="2024-01-03",
    )

    assert request_count == 2
    assert len(sleep_calls) == 0
    assert "SPY" in result.bars
    assert len(result.bars["SPY"]) == 2
