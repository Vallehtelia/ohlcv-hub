"""Tests for the doctor command."""

import os
from typer.testing import CliRunner

from ohlcv_hub.cli import app

runner = CliRunner()


def test_cli_doctor_missing_env_exits_1():
    """Test that doctor exits with code 1 when env vars are missing."""
    # Clear env vars
    env_backup = {}
    for key in ["ALPACA_API_KEY", "ALPACA_API_SECRET", "ALPACA_DATA_BASE_URL"]:
        env_backup[key] = os.environ.get(key)
        os.environ.pop(key, None)

    try:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "Configuration error" in result.stdout or "Configuration error" in result.stderr
        assert "ALPACA_API_KEY" in result.stdout or "ALPACA_API_KEY" in result.stderr
    finally:
        # Restore env vars
        for key, value in env_backup.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


def test_cli_doctor_present_env_exits_0_no_ping():
    """Test that doctor exits with code 0 when env vars are present (no ping)."""
    # Set dummy env vars
    env_backup = {}
    for key in ["ALPACA_API_KEY", "ALPACA_API_SECRET", "ALPACA_DATA_BASE_URL"]:
        env_backup[key] = os.environ.get(key)

    try:
        os.environ["ALPACA_API_KEY"] = "test_key_12345"
        os.environ["ALPACA_API_SECRET"] = "test_secret_67890"
        # Don't set ALPACA_DATA_BASE_URL to test default

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "Configuration OK" in result.stdout
        assert "test_key_12345" not in result.stdout  # Secret should not be printed
        assert "test_secret_67890" not in result.stdout  # Secret should not be printed
        assert "*" in result.stdout  # Should show masked secrets
    finally:
        # Restore env vars
        for key, value in env_backup.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
