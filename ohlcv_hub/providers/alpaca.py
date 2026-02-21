"""Alpaca Market Data API client."""

import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Optional, Union

import httpx

from ohlcv_hub.errors import ProviderError

# Module logger; default WARNING + NullHandler so no output unless configured
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
_logger.setLevel(logging.WARNING)

# Retry bounds for HTTP 429
MAX_RETRIES_PER_REQUEST = 5  # additional attempts after the first; total = 1 + MAX_RETRIES
MAX_SLEEP_SECONDS = 5.0
# Exponential backoff base seconds when no Retry-After / X-RateLimit-Reset: 0.5, 1, 2, 4 (capped at MAX_SLEEP)
BACKOFF_BASE_SECONDS = [0.5, 1.0, 2.0, 4.0]

# Proactive throttling (X-RateLimit-*)
SAFETY_BUFFER_SECONDS = 0.25
MAX_PROACTIVE_SLEEP_SECONDS = 10.0


@dataclass
class BarsResponse:
    """Response from Alpaca bars endpoint."""

    bars: dict[str, list[dict[str, Any]]]
    currency: Optional[str] = None


class AlpacaClient:
    """Client for Alpaca Market Data API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://data.alpaca.markets",
        timeout_seconds: float = 10.0,
        http: Optional[httpx.Client] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        now: Optional[Callable[[], float]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize Alpaca client.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Base URL for Alpaca Market Data API
            timeout_seconds: Request timeout in seconds
            http: Optional httpx.Client instance (for testing)
            sleeper: Optional callable(seconds) for sleep (default: time.sleep); use in tests to avoid real sleep
            now: Optional callable() -> current time in seconds (default: time.time); use in tests for deterministic timing
            logger: Optional logger for rate-limit/retry debug messages; when None uses module logger (no output by default)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._http = http
        self._sleep = sleeper if sleeper is not None else time.sleep
        self._now = now if now is not None else time.time
        self._logger = logger if logger is not None else _logger

    def _get_http_client(self) -> httpx.Client:
        """Get HTTP client instance."""
        if self._http is not None:
            return self._http
        return httpx.Client(timeout=self.timeout_seconds)

    def _build_auth_headers(self) -> dict[str, str]:
        """
        Build authentication headers.

        Returns:
            Dictionary with APCA-API-KEY-ID and APCA-API-SECRET-KEY headers
        """
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def _serialize_date(self, dt: Union[date, datetime, str]) -> str:
        """
        Serialize date/datetime to ISO format string.

        Args:
            dt: Date, datetime, or ISO string

        Returns:
            ISO format date string (YYYY-MM-DD)
        """
        if isinstance(dt, str):
            return dt
        if isinstance(dt, datetime):
            return dt.date().isoformat()
        if isinstance(dt, date):
            return dt.isoformat()
        raise ValueError(f"Unsupported date type: {type(dt)}")

    def _parse_rate_limit_headers(
        self, response: httpx.Response
    ) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Parse X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset from response.
        Returns (limit, remaining, reset) as ints or None if missing/unparsable.
        """
        limit_raw = response.headers.get("x-ratelimit-limit")
        remaining_raw = response.headers.get("x-ratelimit-remaining")
        reset_raw = response.headers.get("x-ratelimit-reset")
        limit = None
        remaining = None
        reset = None
        if limit_raw is not None:
            try:
                limit = int(limit_raw.strip())
            except (ValueError, TypeError):
                pass
        if remaining_raw is not None:
            try:
                remaining = int(remaining_raw.strip())
            except (ValueError, TypeError):
                pass
        if reset_raw is not None:
            try:
                reset = int(reset_raw.strip())
            except (ValueError, TypeError):
                pass
        return (limit, remaining, reset)

    def _compute_sleep_seconds_for_429(
        self, response: httpx.Response, attempt_index: int
    ) -> tuple[float, str]:
        """
        Compute sleep duration for 429 retry from headers or exponential backoff.
        attempt_index is 0-based (0 = first retry after initial 429).
        Returns (sleep_seconds, strategy) where strategy is "Retry-After", "X-RateLimit-Reset", or "backoff".
        """
        # Retry-After: seconds (or HTTP-date; we only parse integer seconds here)
        retry_after = response.headers.get("retry-after")
        if retry_after is not None:
            try:
                secs = float(retry_after.strip())
                return (min(max(0.0, secs), MAX_SLEEP_SECONDS), "Retry-After")
            except ValueError:
                pass

        # X-RateLimit-Reset: unix epoch seconds
        reset_header = response.headers.get("x-ratelimit-reset")
        if reset_header is not None:
            try:
                reset_ts = int(reset_header.strip())
                now_ts = int(self._now())
                wait = reset_ts - now_ts
                return (
                    min(max(0.0, float(wait)), MAX_SLEEP_SECONDS),
                    "X-RateLimit-Reset",
                )
            except (ValueError, TypeError):
                pass

        # Exponential backoff
        if attempt_index < len(BACKOFF_BASE_SECONDS):
            return (
                min(BACKOFF_BASE_SECONDS[attempt_index], MAX_SLEEP_SECONDS),
                "backoff",
            )
        return (MAX_SLEEP_SECONDS, "backoff")

    def fetch_stock_bars(
        self,
        symbols: list[str],
        timeframe: str,
        start: Union[date, datetime, str],
        end: Union[date, datetime, str],
        limit: int = 10000,
        adjustment: str = "raw",
        feed: Optional[str] = None,
        asof: Optional[str] = None,
        sort: str = "asc",
    ) -> BarsResponse:
        """
        Fetch historical stock bars with pagination.

        Args:
            symbols: List of stock symbols (will be normalized to uppercase)
            timeframe: Bar timeframe (e.g., "1Day", "1Min")
            start: Start date (inclusive)
            end: End date (inclusive)
            limit: Maximum number of bars per page (1-10000)
            adjustment: Stock adjustment ("raw", "split", "dividend", "spin-off", "all")
            feed: Data feed ("sip", "iex", "boats", "otc") or None for default
            asof: As-of date for symbol mapping (YYYY-MM-DD) or None
            sort: Sort order ("asc" or "desc")

        Returns:
            BarsResponse with merged bars from all pages

        Raises:
            ValueError: If limit is out of range
            ProviderError: If API request fails
        """
        if limit < 1 or limit > 10000:
            raise ValueError(f"limit must be between 1 and 10000, got {limit}")

        # Normalize symbols to uppercase
        normalized_symbols = [s.upper().strip() for s in symbols if s.strip()]
        if not normalized_symbols:
            raise ValueError("At least one symbol is required")

        # Serialize dates
        start_str = self._serialize_date(start)
        end_str = self._serialize_date(end)

        # Build base query parameters
        params: dict[str, Any] = {
            "symbols": ",".join(normalized_symbols),
            "timeframe": timeframe,
            "start": start_str,
            "end": end_str,
            "limit": limit,
            "adjustment": adjustment,
            "sort": sort,
        }

        # Add optional parameters
        if feed is not None:
            params["feed"] = feed
        if asof is not None:
            params["asof"] = asof

        # Initialize merged results
        merged_bars: dict[str, list[dict[str, Any]]] = {}
        currency: Optional[str] = None
        page_token: Optional[str] = None

        # Build URL
        url = f"{self.base_url}/v2/stocks/bars"
        headers = self._build_auth_headers()

        # Pagination loop; rate state from prior response for proactive throttle
        http_client = self._get_http_client()
        last_remaining: Optional[int] = None
        last_reset: Optional[int] = None
        try:
            while True:
                # Add page_token if we're continuing pagination
                current_params = params.copy()
                if page_token is not None:
                    current_params["page_token"] = page_token

                # Proactive gate: if prior response said we're exhausted (remaining <= 1), wait until reset
                if (
                    last_remaining is not None
                    and last_reset is not None
                    and last_remaining <= 1
                ):
                    wait_secs = last_reset - self._now() + SAFETY_BUFFER_SECONDS
                    wait_secs = max(0.0, min(float(wait_secs), MAX_PROACTIVE_SLEEP_SECONDS))
                    if wait_secs > 0:
                        if self._logger.isEnabledFor(logging.INFO):
                            self._logger.info(
                                "Proactive throttle: remaining=%s reset=%s sleep_secs=%.2f (capped)",
                                last_remaining,
                                last_reset,
                                wait_secs,
                            )
                        self._sleep(wait_secs)

                # Make request with retry on 429
                response = http_client.get(url, params=current_params, headers=headers)
                retries_used = 0

                while response.status_code == 429 and retries_used < MAX_RETRIES_PER_REQUEST:
                    sleep_secs, strategy = self._compute_sleep_seconds_for_429(
                        response, retries_used
                    )
                    if self._logger.isEnabledFor(logging.INFO):
                        self._logger.info(
                            "429 retry attempt %s sleep_secs=%.2f strategy=%s",
                            retries_used + 1,
                            sleep_secs,
                            strategy,
                        )
                    self._sleep(sleep_secs)
                    retries_used += 1
                    response = http_client.get(
                        url, params=current_params, headers=headers
                    )

                # Update rate state from this response (any status) for next iteration
                _, rem, res = self._parse_rate_limit_headers(response)
                if rem is not None:
                    last_remaining = rem
                if res is not None:
                    last_reset = res

                # After retries: 429 still or other error
                if response.status_code != 200:
                    error_text = response.text[:500] if response.text else "(no response body)"
                    if response.status_code == 429:
                        raise ProviderError(
                            f"API rate limited (429) after {MAX_RETRIES_PER_REQUEST} retries exhausted: {error_text}",
                            status_code=429,
                        )
                    raise ProviderError(
                        f"API request failed with status {response.status_code}: {error_text}",
                        status_code=response.status_code,
                    )

                # Parse JSON response
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    raise ProviderError(
                        f"Failed to parse JSON response: {e}",
                        status_code=response.status_code,
                    )

                # Extract bars and merge
                page_bars = data.get("bars", {})
                for symbol, bar_list in page_bars.items():
                    if symbol not in merged_bars:
                        merged_bars[symbol] = []
                    merged_bars[symbol].extend(bar_list)

                # Extract currency (from any page, typically same across pages)
                if currency is None and "currency" in data:
                    currency = data["currency"]

                # Check for next page
                next_token = data.get("next_page_token")
                if not next_token or next_token == "":  # nosec B105
                    break

                page_token = next_token

        finally:
            # Only close if we created the client
            if self._http is None and hasattr(http_client, "close"):
                http_client.close()

        return BarsResponse(bars=merged_bars, currency=currency)
