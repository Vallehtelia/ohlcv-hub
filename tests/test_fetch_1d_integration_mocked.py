"""Integration tests for fetch 1d command with mocked API."""

import json
import os
from pathlib import Path

import httpx
import pandas as pd
import pytest
from typer.testing import CliRunner

from ohlcv_hub.cli import app
from ohlcv_hub.providers.alpaca import AlpacaClient

runner = CliRunner()


def test_fetch_1d_writes_parquet_and_report(tmp_path, monkeypatch):
    """Test that fetch 1d writes parquet file and validation report."""
    captured_params = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Return mock bars response; capture request params for feed assertion."""
        captured_params.append(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "bars": {
                    "SPY": [
                        {
                            "t": "2024-01-02T04:00:00Z",
                            "o": 100.0,
                            "h": 101.0,
                            "l": 99.0,
                            "c": 100.5,
                            "v": 1000000,
                            "n": 5000,
                            "vw": 100.25,
                        },
                        {
                            "t": "2024-01-03T04:00:00Z",
                            "o": 100.5,
                            "h": 102.0,
                            "l": 100.0,
                            "c": 101.0,
                            "v": 1100000,
                            "n": 5500,
                            "vw": 101.0,
                        },
                    ],
                    "QQQ": [
                        {
                            "t": "2024-01-02T04:00:00Z",
                            "o": 200.0,
                            "h": 205.0,
                            "l": 198.0,
                            "c": 203.0,
                            "v": 2000000,
                            "n": 10000,
                            "vw": 201.5,
                        }
                    ],
                },
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=transport)

    # Monkeypatch _make_alpaca_client to return client with MockTransport
    def make_mock_client(config, logger=None):
        return AlpacaClient(
            api_key=config.alpaca_api_key,
            api_secret=config.alpaca_api_secret,
            base_url=config.alpaca_data_base_url,
            http=mock_client,
            logger=logger,
        )

    monkeypatch.setattr("ohlcv_hub.cli._make_alpaca_client", make_mock_client)

    # Set env vars
    import os

    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        # Run CLI command
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols",
                "SPY,QQQ",
                "--start",
                "2024-01-01",
                "--end",
                "2024-01-05",
                "--tf",
                "1d",
                "--out",
                str(tmp_path),
                "--format",
                "parquet",
                "--report",
            ],
        )

        assert result.exit_code == 0, f"Exit code was {result.exit_code}, output: {result.stdout}"

        # Assert parquet file exists
        parquet_files = list(tmp_path.glob("ohlcv_1d_*.parquet"))
        assert len(parquet_files) == 1, f"Expected 1 parquet file, found {len(parquet_files)}"
        parquet_path = parquet_files[0]

        # Load and verify parquet contents
        df = pd.read_parquet(parquet_path)
        assert len(df) == 3  # 2 SPY bars + 1 QQQ bar
        assert set(df["symbol"].unique()) == {"SPY", "QQQ"}
        assert "symbol" in df.columns
        assert "timeframe" in df.columns
        assert "ts" in df.columns
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        assert "source" in df.columns
        assert "currency" in df.columns
        assert "adjustment" in df.columns

        # Assert validation report exists
        report_path = tmp_path / "validation_report.json"
        assert report_path.exists(), "validation_report.json should exist"

        # Load and verify report structure
        with open(report_path) as f:
            report = json.load(f)

        assert "summary" in report
        assert "issues" in report
        assert "missing_days" in report
        assert report["summary"]["bars_count"] == 3
        assert report["summary"]["symbols_count"] == 2
        # No hard validation errors (missing days are warnings only)
        assert len(report["issues"]["duplicates"]) == 0
        assert report["issues"]["ohlc_violations"]["count"] == 0
        assert report["issues"]["volume_violations"]["count"] == 0

        # Default feed is iex
        assert len(captured_params) >= 1
        assert captured_params[0].get("feed") == "iex"

    finally:
        # Clean up env vars
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)


def test_fetch_1d_with_feed_sip_passes_feed_to_client(tmp_path, monkeypatch):
    """Test that --feed sip is passed through to Alpaca request."""
    captured_params = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_params.append(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-02T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=transport)

    def make_mock_client(config, logger=None):
        return AlpacaClient(
            api_key=config.alpaca_api_key,
            api_secret=config.alpaca_api_secret,
            base_url=config.alpaca_data_base_url,
            http=mock_client,
            logger=logger,
        )

    monkeypatch.setattr("ohlcv_hub.cli._make_alpaca_client", make_mock_client)
    import os
    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols", "SPY",
                "--start", "2024-01-01",
                "--end", "2024-01-05",
                "--tf", "1d",
                "--out", str(tmp_path),
                "--feed", "sip",
            ],
        )
        assert result.exit_code == 0
        assert len(captured_params) >= 1
        assert captured_params[0].get("feed") == "sip"
    finally:
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)


def test_fetch_1d_handles_provider_error(tmp_path, monkeypatch):
    """Test that fetch 1d handles provider errors gracefully."""
    # Mock 401 response
    def mock_handler(request: httpx.Request) -> httpx.Response:
        """Return 401 Unauthorized."""
        return httpx.Response(
            401,
            json={"message": "Unauthorized", "code": 401},
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=transport)

    # Monkeypatch _make_alpaca_client
    def make_mock_client(config, logger=None):
        return AlpacaClient(
            api_key=config.alpaca_api_key,
            api_secret=config.alpaca_api_secret,
            base_url=config.alpaca_data_base_url,
            http=mock_client,
            logger=logger,
        )

    monkeypatch.setattr("ohlcv_hub.cli._make_alpaca_client", make_mock_client)

    # Set env vars
    import os

    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        # Run CLI command
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols",
                "SPY",
                "--start",
                "2024-01-01",
                "--end",
                "2024-01-05",
                "--tf",
                "1d",
                "--out",
                str(tmp_path),
            ],
        )

        # Assert exit code 1
        assert result.exit_code == 1, f"Exit code was {result.exit_code}, output: {result.stdout}"

        # Assert error message mentions provider error
        assert "provider" in result.stdout.lower() or "provider" in result.stderr.lower()

    finally:
        # Clean up env vars
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)


def test_fetch_verbose_logs_rate_limit_line_when_proactive_throttle(tmp_path, monkeypatch, caplog):
    """With --verbose, a proactive throttle (remaining=0, reset) produces a log line; no real sleep."""
    request_count = 0
    fixed_now = 1000.0
    reset_ts = 1001  # now+1 -> proactive sleep ~1.25s (capped)

    def sleeper_spy(seconds: float) -> None:
        pass  # no real sleep

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
                    "bars": {"SPY": [{"t": "2024-01-02T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                    "next_page_token": "tok1",
                    "currency": "USD",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-03T04:00:00Z", "o": 101.0, "h": 102.0, "l": 100.0, "c": 101.5, "v": 1100, "n": 11, "vw": 101.0}]},
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=transport)

    def make_mock_client(config, logger=None):
        return AlpacaClient(
            api_key=config.alpaca_api_key,
            api_secret=config.alpaca_api_secret,
            base_url=config.alpaca_data_base_url,
            http=mock_client,
            sleeper=sleeper_spy,
            now=now_fixed,
            logger=logger,
        )

    monkeypatch.setattr("ohlcv_hub.cli._make_alpaca_client", make_mock_client)
    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols", "SPY",
                "--start", "2024-01-01",
                "--end", "2024-01-05",
                "--tf", "1d",
                "--out", str(tmp_path),
                "--verbose",
            ],
        )
        assert result.exit_code == 0, f"Exit code was {result.exit_code}, stderr: {result.stderr}"
        # Verbose log is emitted (may appear in stderr or in pytest's caplog)
        assert "remaining=0" in result.stderr or "Proactive throttle" in result.stderr or "remaining=0" in caplog.text or "Proactive throttle" in caplog.text
    finally:
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)


def test_fetch_no_verbose_omits_rate_limit_log(tmp_path, monkeypatch):
    """Without --verbose, no rate-limit debug line in output."""
    request_count = 0
    fixed_now = 1000.0
    reset_ts = 1001

    def sleeper_spy(seconds: float) -> None:
        pass

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
                    "bars": {"SPY": [{"t": "2024-01-02T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000, "n": 10, "vw": 100.25}]},
                    "next_page_token": "tok1",
                    "currency": "USD",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "bars": {"SPY": [{"t": "2024-01-03T04:00:00Z", "o": 101.0, "h": 102.0, "l": 100.0, "c": 101.5, "v": 1100, "n": 11, "vw": 101.0}]},
                "next_page_token": None,
                "currency": "USD",
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=transport)

    def make_mock_client(config, logger=None):
        return AlpacaClient(
            api_key=config.alpaca_api_key,
            api_secret=config.alpaca_api_secret,
            base_url=config.alpaca_data_base_url,
            http=mock_client,
            sleeper=sleeper_spy,
            now=now_fixed,
            logger=logger,
        )

    monkeypatch.setattr("ohlcv_hub.cli._make_alpaca_client", make_mock_client)
    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols", "SPY",
                "--start", "2024-01-01",
                "--end", "2024-01-05",
                "--tf", "1d",
                "--out", str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "remaining=0" not in result.stderr
        assert "Proactive throttle" not in result.stderr
    finally:
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)


# Weekly path is implemented; see test_fetch_1w_integration_mocked.py
