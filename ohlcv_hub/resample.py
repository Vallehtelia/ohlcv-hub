"""Resample daily bars to weekly bars."""

import pandas as pd


def to_weekly(df_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily bars to weekly bars (Monday 00:00 UTC, W-MON, label left, closed left).

    Input DataFrame must be in stable schema with timeframe == "1d".
    Aggregation: open=first, high=max, low=min, close=last, volume=sum.
    Drops weeks with no data. Preserves source, currency, adjustment from first row per symbol.
    """
    if df_daily.empty:
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

    # Ensure ts is tz-aware UTC and we only have daily data
    df = df_daily.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)

    weekly_parts = []
    for symbol in df["symbol"].unique():
        sym_df = df[df["symbol"] == symbol].copy()
        sym_df = sym_df.set_index("ts").sort_index()

        resampled = sym_df.resample("W-MON", label="left", closed="left").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )

        # Drop weeks with no data (NaN open after resample)
        resampled = resampled.dropna(subset=["open"])

        if resampled.empty:
            continue

        # Restore symbol and metadata from first daily row of each week (we take first of symbol)
        first_row = sym_df.reset_index().iloc[0]
        resampled = resampled.reset_index()
        resampled["symbol"] = symbol
        resampled["timeframe"] = "1w"
        resampled["source"] = first_row["source"]
        resampled["currency"] = first_row["currency"]
        resampled["adjustment"] = first_row["adjustment"]

        weekly_parts.append(resampled)

    if not weekly_parts:
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

    out = pd.concat(weekly_parts, ignore_index=True)

    # Column order and dtypes
    out = out[
        [
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
    ]
    out["symbol"] = out["symbol"].astype("string")
    out["timeframe"] = out["timeframe"].astype("string")
    out["ts"] = pd.to_datetime(out["ts"], utc=True)
    out["open"] = out["open"].astype("float64")
    out["high"] = out["high"].astype("float64")
    out["low"] = out["low"].astype("float64")
    out["close"] = out["close"].astype("float64")
    out["volume"] = out["volume"].astype("int64")
    out["source"] = out["source"].astype("string")
    out["currency"] = out["currency"].astype("string")
    out["adjustment"] = out["adjustment"].astype("string")

    out = out.sort_values(["symbol", "ts"], ascending=[True, True]).reset_index(drop=True)
    return out
