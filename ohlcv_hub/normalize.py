"""Normalize raw bar data to stable schema."""

from typing import Any

import pandas as pd


def bars_dict_to_dataframe(
    bars: dict[str, list[dict[str, Any]]],
    *,
    timeframe: str,
    source: str,
    currency: str | None,
    adjustment: str,
) -> pd.DataFrame:
    """
    Convert bars dict to pandas DataFrame with stable schema.

    Args:
        bars: Dictionary mapping symbol to list of bar objects
        timeframe: Timeframe string (e.g., "1d" for daily)
        source: Source identifier (e.g., "alpaca")
        currency: Currency code (defaults to "USD" if None)
        adjustment: Adjustment type (e.g., "raw", "all")

    Returns:
        DataFrame with columns: symbol, timeframe, ts, open, high, low, close, volume,
        source, currency, adjustment. Sorted by symbol, then ts (ascending).
    """
    if not bars:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(
            columns=[
                "symbol",
                "timeframe",
                "ts",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "source",
                "currency",
                "adjustment",
            ]
        )

    rows = []
    currency_value = currency if currency is not None else "USD"

    for symbol, bar_list in bars.items():
        for bar in bar_list:
            # Parse timestamp (RFC-3339 format)
            ts_str = bar.get("t")
            if ts_str is None:
                continue  # Skip bars without timestamp

            # Parse to UTC datetime
            ts = pd.to_datetime(ts_str, utc=True)

            # Extract OHLCV
            open_price = float(bar.get("o", 0.0))
            high_price = float(bar.get("h", 0.0))
            low_price = float(bar.get("l", 0.0))
            close_price = float(bar.get("c", 0.0))
            volume = int(bar.get("v", 0))

            rows.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ts": ts,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "source": source,
                    "currency": currency_value,
                    "adjustment": adjustment,
                }
            )

    if not rows:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(
            columns=[
                "symbol",
                "timeframe",
                "ts",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "source",
                "currency",
                "adjustment",
            ]
        )

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Ensure correct dtypes
    df["symbol"] = df["symbol"].astype("string")
    df["timeframe"] = df["timeframe"].astype("string")
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["open"] = df["open"].astype("float64")
    df["high"] = df["high"].astype("float64")
    df["low"] = df["low"].astype("float64")
    df["close"] = df["close"].astype("float64")
    df["volume"] = df["volume"].astype("int64")
    df["source"] = df["source"].astype("string")
    df["currency"] = df["currency"].astype("string")
    df["adjustment"] = df["adjustment"].astype("string")

    # Sort by symbol, then ts (ascending) for downstream validation
    df = df.sort_values(["symbol", "ts"], ascending=[True, True]).reset_index(drop=True)

    return df
