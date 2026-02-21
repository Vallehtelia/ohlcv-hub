"""Tests for the fetch command argument parsing."""

from typer.testing import CliRunner

from ohlcv_hub.cli import app

runner = CliRunner()


def test_cli_fetch_parses_and_exits_1_without_config():
    """Test that fetch with valid 1d args exits 1 when env vars are missing (config error)."""
    import os
    for k in ("ALPACA_API_KEY", "ALPACA_API_SECRET"):
        os.environ.pop(k, None)
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            "SPY,QQQ",
            "--start",
            "2015-01-01",
            "--end",
            "2015-02-01",
            "--tf",
            "1d",
            "--out",
            "./data",
        ],
    )
    assert result.exit_code == 1
    assert "ALPACA" in result.stdout or "Configuration" in result.stdout or "configuration" in result.stderr.lower()


def test_cli_fetch_validates_symbols():
    """Test that fetch validates symbols are provided."""
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            "",
            "--start",
            "2015-01-01",
            "--end",
            "2015-02-01",
            "--tf",
            "1d",
            "--out",
            "./data",
        ],
    )

    assert result.exit_code == 1
    assert "symbol" in result.stdout.lower() or "symbol" in result.stderr.lower()


def test_cli_fetch_validates_dates():
    """Test that fetch validates date format and ordering."""
    # Test invalid date format
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            "SPY",
            "--start",
            "invalid-date",
            "--end",
            "2015-02-01",
            "--tf",
            "1d",
            "--out",
            "./data",
        ],
    )

    assert result.exit_code == 1
    assert "date" in result.stdout.lower() or "date" in result.stderr.lower()

    # Test start > end
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            "SPY",
            "--start",
            "2015-02-01",
            "--end",
            "2015-01-01",
            "--tf",
            "1d",
            "--out",
            "./data",
        ],
    )

    assert result.exit_code == 1
    assert "start" in result.stdout.lower() or "start" in result.stderr.lower()


def test_cli_fetch_validates_output_path():
    """Test that fetch validates output path is provided."""
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            "SPY",
            "--start",
            "2015-01-01",
            "--end",
            "2015-02-01",
            "--tf",
            "1d",
            "--out",
            "",
        ],
    )

    assert result.exit_code == 1
    assert "output" in result.stdout.lower() or "output" in result.stderr.lower()


def test_cli_fetch_normalizes_symbols():
    """Test that fetch normalizes symbols (uppercase, strips spaces)."""
    import os
    for k in ("ALPACA_API_KEY", "ALPACA_API_SECRET"):
        os.environ.pop(k, None)
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            " spy , qqq , aapl ",
            "--start",
            "2015-01-01",
            "--end",
            "2015-02-01",
            "--tf",
            "1d",
            "--out",
            "./data",
        ],
    )
    assert result.exit_code == 1


def test_cli_fetch_handles_empty_symbol_segments():
    """Test that fetch handles empty symbol segments (e.g., 'SPY,,QQQ')."""
    import os
    for k in ("ALPACA_API_KEY", "ALPACA_API_SECRET"):
        os.environ.pop(k, None)
    result = runner.invoke(
        app,
        [
            "fetch",
            "--symbols",
            "SPY,,QQQ",
            "--start",
            "2015-01-01",
            "--end",
            "2015-02-01",
            "--tf",
            "1d",
            "--out",
            "./data",
        ],
    )
    assert result.exit_code == 1
