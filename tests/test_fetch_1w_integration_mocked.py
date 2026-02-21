"""Integration tests for fetch 1w command with mocked API."""

import json
import os

import httpx
import pandas as pd
from typer.testing import CliRunner

from ohlcv_hub.cli import app
from ohlcv_hub.providers.alpaca import AlpacaClient

runner = CliRunner()


def _make_daily_bars_fixture_two_weeks():
    """Daily bars for SPY and QQQ spanning two calendar weeks (Mon 2024-01-01 week + Mon 2024-01-08 week)."""
    return {
        "bars": {
            "SPY": [
                {"t": "2024-01-02T04:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1000000, "n": 5000, "vw": 100.25},
                {"t": "2024-01-03T04:00:00Z", "o": 100.5, "h": 102.0, "l": 100.0, "c": 101.0, "v": 1100000, "n": 5500, "vw": 101.0},
                {"t": "2024-01-04T04:00:00Z", "o": 101.0, "h": 103.0, "l": 100.5, "c": 102.0, "v": 1200000, "n": 6000, "vw": 101.5},
                {"t": "2024-01-08T04:00:00Z", "o": 102.0, "h": 104.0, "l": 101.0, "c": 103.0, "v": 1300000, "n": 6500, "vw": 102.5},
                {"t": "2024-01-09T04:00:00Z", "o": 103.0, "h": 105.0, "l": 102.0, "c": 104.0, "v": 1400000, "n": 7000, "vw": 103.5},
            ],
            "QQQ": [
                {"t": "2024-01-02T04:00:00Z", "o": 200.0, "h": 205.0, "l": 198.0, "c": 203.0, "v": 2000000, "n": 10000, "vw": 201.5},
                {"t": "2024-01-03T04:00:00Z", "o": 203.0, "h": 208.0, "l": 202.0, "c": 206.0, "v": 2100000, "n": 10500, "vw": 205.0},
                {"t": "2024-01-08T04:00:00Z", "o": 206.0, "h": 210.0, "l": 205.0, "c": 209.0, "v": 2200000, "n": 11000, "vw": 207.5},
                {"t": "2024-01-09T04:00:00Z", "o": 209.0, "h": 212.0, "l": 208.0, "c": 211.0, "v": 2300000, "n": 11500, "vw": 210.0},
            ],
        },
        "next_page_token": None,
        "currency": "USD",
    }


def test_fetch_1w_writes_parquet_and_report(tmp_path, monkeypatch):
    """Test that fetch 1w writes weekly parquet and validation report; ts are Mondays 00:00 UTC."""
    payload = _make_daily_bars_fixture_two_weeks()
    captured_params = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_params.append(dict(request.url.params))
        return httpx.Response(200, json=payload, request=request)

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
    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols",
                "SPY,QQQ",
                "--start",
                "2024-01-01",
                "--end",
                "2024-01-15",
                "--tf",
                "1w",
                "--out",
                str(tmp_path),
                "--format",
                "parquet",
                "--report",
            ],
        )

        # Success: exit 0; export-on-validation-error can yield exit 1
        assert result.exit_code in (0, 1), f"Exit code was {result.exit_code}, output: {result.stdout}"

        parquet_files = list(tmp_path.glob("ohlcv_1w_*.parquet"))
        assert len(parquet_files) == 1
        df = pd.read_parquet(parquet_files[0])

        assert (df["timeframe"] == "1w").all()
        assert set(df["symbol"].unique()) == {"SPY", "QQQ"}
        # SPY: week 2024-01-01 (Mon), week 2024-01-08 (Mon) -> 2 rows. QQQ: same 2 weeks -> 2 rows. Total 4.
        assert len(df) == 4

        # All ts must be Monday 00:00:00+00:00
        for ts in df["ts"]:
            assert ts.tzinfo is not None
            assert ts.hour == 0 and ts.minute == 0 and ts.second == 0
            # Monday weekday is 0 in Python
            assert ts.weekday() == 0

        report_path = tmp_path / "validation_report.json"
        assert report_path.exists()
        with open(report_path) as f:
            report = json.load(f)
        assert "summary" in report
        assert "issues" in report
        assert "missing_days" in report
        assert report["missing_days"]["totals"]["missing_days_count_total"] == 0

        # Default feed is iex
        assert len(captured_params) >= 1
        assert captured_params[0].get("feed") == "iex"

    finally:
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)


def test_fetch_1w_handles_provider_error(tmp_path, monkeypatch):
    """Test that fetch 1w returns exit 1 on provider error."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"}, request=request)

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
    os.environ["ALPACA_API_KEY"] = "test_key"
    os.environ["ALPACA_API_SECRET"] = "test_secret"

    try:
        result = runner.invoke(
            app,
            [
                "fetch",
                "--symbols",
                "SPY",
                "--start",
                "2024-01-01",
                "--end",
                "2024-01-15",
                "--tf",
                "1w",
                "--out",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        assert "provider" in result.stdout.lower() or "provider" in result.stderr.lower()
    finally:
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_API_SECRET", None)
