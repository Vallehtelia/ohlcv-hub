"""Dataset building orchestration."""

from datetime import date

import pandas as pd

from ohlcv_hub.normalize import bars_dict_to_dataframe
from ohlcv_hub.providers.alpaca import AlpacaClient
from ohlcv_hub.resample import to_weekly
from ohlcv_hub.validate import validate_daily_bars, validate_weekly_bars


def build_daily_dataset(
    *,
    client: AlpacaClient,
    symbols: list[str],
    start: date,
    end: date,
    adjustment: str,
    feed: str | None = "iex",
) -> tuple[pd.DataFrame, dict]:
    """
    Build daily dataset: fetch, normalize, and validate.

    Args:
        client: AlpacaClient instance
        symbols: List of stock symbols
        start: Start date (inclusive)
        end: End date (inclusive)
        adjustment: Adjustment type ("raw" or "all")
        feed: Data feed ("iex", "sip", etc.) or None for default

    Returns:
        Tuple of (DataFrame, validation_report_dict)
    """
    # Fetch bars from Alpaca
    response = client.fetch_stock_bars(
        symbols=symbols,
        timeframe="1Day",
        start=start,
        end=end,
        limit=10000,
        adjustment=adjustment,
        feed=feed,
        sort="asc",
    )

    # Normalize to DataFrame
    df = bars_dict_to_dataframe(
        bars=response.bars,
        timeframe="1d",
        source="alpaca",
        currency=response.currency,
        adjustment=adjustment,
    )

    # Validate
    ok, report = validate_daily_bars(df, start=start, end=end)

    return df, report


def build_weekly_dataset(
    *,
    client: AlpacaClient,
    symbols: list[str],
    start: date,
    end: date,
    adjustment: str,
    feed: str | None = "iex",
) -> tuple[pd.DataFrame, dict]:
    """
    Build weekly dataset: fetch daily bars, normalize, resample to weekly, validate.

    Returns:
        Tuple of (weekly_DataFrame, validation_report_dict)
    """
    # Fetch daily bars from Alpaca
    response = client.fetch_stock_bars(
        symbols=symbols,
        timeframe="1Day",
        start=start,
        end=end,
        limit=10000,
        adjustment=adjustment,
        feed=feed,
        sort="asc",
    )

    # Normalize to daily DataFrame
    df_daily = bars_dict_to_dataframe(
        bars=response.bars,
        timeframe="1d",
        source="alpaca",
        currency=response.currency,
        adjustment=adjustment,
    )

    # Resample to weekly
    df_weekly = to_weekly(df_daily)

    # Validate weekly (no missing-days report)
    ok, report = validate_weekly_bars(df_weekly, start=start, end=end)

    return df_weekly, report
