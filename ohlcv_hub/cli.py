"""CLI interface for ohlcv-hub."""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
import typer
from dateutil.parser import parse as parse_date

from ohlcv_hub.config import Config, load_config_from_env
from ohlcv_hub.dataset import build_daily_dataset, build_weekly_dataset
from ohlcv_hub.errors import CliUsageError, ConfigError, ProviderError
from ohlcv_hub.export import export_dataframe
from ohlcv_hub.providers.alpaca import AlpacaClient
from ohlcv_hub.types import Adjustment, Feed, OutputFormat, Provider, Timeframe

app = typer.Typer(
    name="ohlcv-hub",
    help="OHLCV data fetching and processing tool",
    add_completion=False,
)


@app.command()
def doctor(
    ping: bool = typer.Option(
        False, "--ping/--no-ping", help="Perform a test API request to verify connectivity"
    ),
) -> None:
    """
    Check configuration and optionally test API connectivity.

    Verifies that required environment variables are set and optionally
    performs a test request to the Alpaca Market Data API.
    """
    try:
        config = load_config_from_env(require_keys=True)
    except ConfigError as e:
        typer.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)

    # Print configuration summary (without secrets)
    typer.echo("✓ Configuration OK")
    typer.echo(f"  API Key: {'*' * min(len(config.alpaca_api_key), 8)}...")
    typer.echo(f"  API Secret: {'*' * min(len(config.alpaca_api_secret), 8)}...")
    typer.echo(f"  Base URL: {config.alpaca_data_base_url}")

    if not ping:
        typer.echo("\nUse --ping to test API connectivity")
        return

    # Perform ping test
    typer.echo("\nTesting API connectivity...")
    try:
        _perform_ping_test(config)
        typer.echo("✓ API connectivity test passed")
    except Exception as e:
        typer.echo(f"❌ API connectivity test failed: {e}", err=True)
        sys.exit(1)


def _perform_ping_test(config) -> None:
    """Perform a test API request to verify connectivity."""
    # Calculate date range (today - 10 days to today)
    end_date = date.today()
    start_date = end_date - timedelta(days=10)

    # Build request URL
    url = f"{config.alpaca_data_base_url}/v2/stocks/bars"
    params = {
        "symbols": "SPY",
        "timeframe": "1Day",
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "limit": 1,
        "adjustment": "raw",
        "feed": "iex",  # Use IEX to reduce subscription issues
        "sort": "asc",
    }
    headers = {
        "APCA-API-KEY-ID": config.alpaca_api_key,
        "APCA-API-SECRET-KEY": config.alpaca_api_secret,
    }

    # Make request with timeout
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, params=params, headers=headers)

    if response.status_code != 200:
        error_text = response.text[:200] if response.text else "(no response body)"
        raise CliUsageError(
            f"API request failed with status {response.status_code}: {error_text}"
        )


def _make_alpaca_client(
    config: Config,
    logger: Optional[logging.Logger] = None,
) -> AlpacaClient:
    """
    Create AlpacaClient instance from config.

    This function exists to enable test injection via monkeypatching.

    Args:
        config: Config instance
        logger: Optional logger for rate-limit/retry debug (e.g. when --verbose)

    Returns:
        AlpacaClient instance
    """
    return AlpacaClient(
        api_key=config.alpaca_api_key,
        api_secret=config.alpaca_api_secret,
        base_url=config.alpaca_data_base_url,
        logger=logger,
    )


@app.command()
def fetch(
    symbols: str = typer.Option(..., "--symbols", help="Comma-separated list of stock symbols"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    tf: Timeframe = typer.Option(..., "--tf", help="Timeframe: 1d (daily) or 1w (weekly)"),
    out: str = typer.Option(..., "--out", help="Output directory path"),
    format: OutputFormat = typer.Option(
        OutputFormat.PARQUET, "--format", help="Output format: parquet or csv"
    ),
    adjustment: Adjustment = typer.Option(
        Adjustment.RAW, "--adjustment", help="Stock adjustment: raw or all"
    ),
    provider: Provider = typer.Option(
        Provider.ALPACA, "--provider", help="Data provider (only 'alpaca' supported)"
    ),
    report: bool = typer.Option(
        True, "--report/--no-report", help="Generate missing days report"
    ),
    feed: Feed = typer.Option(
        Feed.IEX,
        "--feed",
        help="Alpaca data feed: iex, sip, boats, or otc",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose/--no-verbose",
        help="Enable debug logging for rate-limit throttling and 429 retries",
    ),
) -> None:
    """
    Fetch historical OHLCV data.

    For daily bars (--tf 1d), fetches data, validates, and exports to parquet/csv.
    For weekly bars (--tf 1w), fetches daily bars, resamples to weekly, then validates and exports.
    """
    # Validate and normalize symbols
    symbol_list = _parse_symbols(symbols)
    if not symbol_list:
        typer.echo("❌ Error: At least one symbol is required", err=True)
        raise typer.Exit(1)

    # Validate and parse dates
    try:
        start_date = _parse_date(start)
        end_date = _parse_date(end)
    except ValueError as e:
        typer.echo(f"❌ Error: Invalid date format: {e}", err=True)
        raise typer.Exit(1)

    if start_date > end_date:
        typer.echo("❌ Error: Start date must be <= end date", err=True)
        raise typer.Exit(1)

    # Validate output path
    if not out or not out.strip():
        typer.echo("❌ Error: Output path is required", err=True)
        raise typer.Exit(1)

    try:
        config = load_config_from_env(require_keys=True)
    except ConfigError as e:
        typer.echo(f"❌ Configuration error: {e}", err=True)
        raise typer.Exit(1)

    try:
        verbose_logger: Optional[logging.Logger] = None
        if verbose:
            verbose_logger = logging.getLogger("ohlcv_hub.providers.alpaca")
            verbose_logger.setLevel(logging.INFO)
            if not verbose_logger.handlers:
                handler = logging.StreamHandler(sys.stderr)
                handler.setFormatter(logging.Formatter("%(message)s"))
                verbose_logger.addHandler(handler)
        client = _make_alpaca_client(config, logger=verbose_logger)
        typer.echo("Fetching data from Alpaca...")

        if tf == Timeframe.DAILY:
            df, validation_report = build_daily_dataset(
                client=client,
                symbols=symbol_list,
                start=start_date,
                end=end_date,
                adjustment=adjustment.value,
                feed=feed.value,
            )
            filename_prefix = "ohlcv_1d"
        else:
            # tf == Timeframe.WEEKLY
            df, validation_report = build_weekly_dataset(
                client=client,
                symbols=symbol_list,
                start=start_date,
                end=end_date,
                adjustment=adjustment.value,
                feed=feed.value,
            )
            filename_prefix = "ohlcv_1w"

        issues = validation_report.get("issues", {})
        has_errors = (
            len(issues.get("duplicates", [])) > 0
            or len(issues.get("non_monotonic", [])) > 0
            or issues.get("ohlc_violations", {}).get("count", 0) > 0
            or issues.get("volume_violations", {}).get("count", 0) > 0
        )

        if has_errors:
            typer.echo("⚠️  Validation errors detected:", err=True)
            if issues.get("duplicates"):
                typer.echo(f"  - {len(issues['duplicates'])} duplicate entries", err=True)
            if issues.get("non_monotonic"):
                typer.echo(
                    f"  - {len(issues['non_monotonic'])} non-monotonic timestamp issues",
                    err=True,
                )
            if issues.get("ohlc_violations", {}).get("count", 0) > 0:
                typer.echo(
                    f"  - {issues['ohlc_violations']['count']} OHLC violations",
                    err=True,
                )
            if issues.get("volume_violations", {}).get("count", 0) > 0:
                typer.echo(
                    f"  - {issues['volume_violations']['count']} volume violations",
                    err=True,
                )
            typer.echo("  Exporting data anyway (with errors)...", err=True)

        filename = f"{filename_prefix}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        typer.echo("Exporting data...")
        file_path = export_dataframe(
            df=df,
            out_dir=out,
            format=format.value,
            filename=filename,
        )

        if report:
            report_path = Path(out) / "validation_report.json"
            with open(report_path, "w") as f:
                json.dump(validation_report, f, indent=2, default=str)
            typer.echo(f"Validation report written to: {report_path}")

        bars_count = validation_report.get("summary", {}).get("bars_count", 0)
        symbols_count = validation_report.get("summary", {}).get("symbols_count", 0)
        missing_days_total = (
            validation_report.get("missing_days", {})
            .get("totals", {})
            .get("missing_days_count_total", 0)
        )

        typer.echo("\n✓ Fetch completed successfully")
        typer.echo(f"  Bars: {bars_count}")
        typer.echo(f"  Symbols: {symbols_count}")
        typer.echo(f"  Output file: {file_path}")
        if missing_days_total > 0:
            typer.echo(f"  Missing trading days: {missing_days_total} (see validation_report.json)")

        if has_errors:
            raise typer.Exit(1)
        raise typer.Exit(0)

    except ProviderError as e:
        typer.echo(f"❌ Provider error: {e}", err=True)
        if e.status_code:
            typer.echo(f"  Status code: {e.status_code}", err=True)
        raise typer.Exit(1)
    except typer.Exit:
        raise  # Let success/failure exit codes propagate
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1)


def _parse_symbols(symbols_str: str) -> list[str]:
    """
    Parse and normalize comma-separated symbols.

    Args:
        symbols_str: Comma-separated string of symbols

    Returns:
        List of normalized (uppercase, stripped) symbols, excluding empty strings
    """
    symbols = [s.strip().upper() for s in symbols_str.split(",")]
    return [s for s in symbols if s]  # Remove empty strings


def _parse_date(date_str: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to parse

    Returns:
        date object

    Raises:
        ValueError: If date string is invalid
    """
    try:
        # Try parsing as YYYY-MM-DD first
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        # Fall back to dateutil parser for more flexible parsing
        try:
            parsed = parse_date(date_str)
            return parsed.date()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_str}") from e


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
