"""Validate daily and weekly bars data and generate validation report."""

from datetime import date
from typing import Any

import pandas as pd
import exchange_calendars as xcals
from zoneinfo import ZoneInfo

# NY timezone for trading calendar
NY_TZ = ZoneInfo("America/New_York")


def _validate_bars_issues(
    df: pd.DataFrame, *, start: date, end: date
) -> tuple[dict[str, Any], bool]:
    """
    Shared validation: duplicates, monotonic, OHLC sanity, volume.
    Returns (report with summary + issues filled, ok).
    """
    report: dict[str, Any] = {
        "summary": {
            "symbols_count": 0,
            "bars_count": 0,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        },
        "issues": {
            "duplicates": [],
            "non_monotonic": [],
            "ohlc_violations": {"count": 0, "samples": []},
            "volume_violations": {"count": 0, "samples": []},
        },
    }

    if df.empty:
        report["summary"]["symbols_count"] = 0
        report["summary"]["bars_count"] = 0
        return report, True

    report["summary"]["symbols_count"] = df["symbol"].nunique()
    report["summary"]["bars_count"] = len(df)

    # Duplicates
    duplicates = df[df.duplicated(subset=["symbol", "ts"], keep=False)]
    if not duplicates.empty:
        for (symbol, ts), group in duplicates.groupby(["symbol", "ts"]):
            report["issues"]["duplicates"].append(
                {"symbol": str(symbol), "ts": ts.isoformat(), "count": len(group)}
            )

    # Monotonic
    non_monotonic = []
    for symbol in df["symbol"].unique():
        symbol_df = df[df["symbol"] == symbol].sort_values("ts")
        if len(symbol_df) > 1:
            ts_diff = symbol_df["ts"].diff()
            violations = symbol_df[ts_diff <= pd.Timedelta(0)]
            if not violations.empty:
                idx = violations.index[0]
                if idx > 0:
                    prev_idx = symbol_df.index[symbol_df.index.get_loc(idx) - 1]
                    prev_ts = symbol_df.loc[prev_idx, "ts"]
                    curr_ts = symbol_df.loc[idx, "ts"]
                    non_monotonic.append(
                        {
                            "symbol": str(symbol),
                            "example_ts_prev": prev_ts.isoformat(),
                            "example_ts_next": curr_ts.isoformat(),
                        }
                    )
    report["issues"]["non_monotonic"] = non_monotonic

    # OHLC
    ohlc_violations = []
    for idx, row in df.iterrows():
        open_price = row["open"]
        high_price = row["high"]
        low_price = row["low"]
        close_price = row["close"]
        if high_price < max(open_price, close_price):
            ohlc_violations.append(
                {
                    "symbol": str(row["symbol"]),
                    "ts": row["ts"].isoformat(),
                    "open": float(open_price),
                    "high": float(high_price),
                    "low": float(low_price),
                    "close": float(close_price),
                    "issue": "high < max(open, close)",
                }
            )
        elif low_price > min(open_price, close_price):
            ohlc_violations.append(
                {
                    "symbol": str(row["symbol"]),
                    "ts": row["ts"].isoformat(),
                    "open": float(open_price),
                    "high": float(high_price),
                    "low": float(low_price),
                    "close": float(close_price),
                    "issue": "low > min(open, close)",
                }
            )
        elif high_price < low_price:
            ohlc_violations.append(
                {
                    "symbol": str(row["symbol"]),
                    "ts": row["ts"].isoformat(),
                    "open": float(open_price),
                    "high": float(high_price),
                    "low": float(low_price),
                    "close": float(close_price),
                    "issue": "high < low",
                }
            )
    report["issues"]["ohlc_violations"]["count"] = len(ohlc_violations)
    report["issues"]["ohlc_violations"]["samples"] = ohlc_violations[:20]

    # Volume
    volume_violations = []
    negative_volume = df[df["volume"] < 0]
    if not negative_volume.empty:
        for idx, row in negative_volume.iterrows():
            volume_violations.append(
                {
                    "symbol": str(row["symbol"]),
                    "ts": row["ts"].isoformat(),
                    "volume": int(row["volume"]),
                }
            )
    report["issues"]["volume_violations"]["count"] = len(volume_violations)
    report["issues"]["volume_violations"]["samples"] = volume_violations[:20]

    ok = (
        len(report["issues"]["duplicates"]) == 0
        and len(report["issues"]["non_monotonic"]) == 0
        and report["issues"]["ohlc_violations"]["count"] == 0
        and report["issues"]["volume_violations"]["count"] == 0
    )
    return report, ok


def validate_daily_bars(
    df: pd.DataFrame, *, start: date, end: date
) -> tuple[bool, dict[str, Any]]:
    """
    Validate daily bars and generate validation report (includes missing trading days).
    """
    report, ok = _validate_bars_issues(df, start=start, end=end)
    report["missing_days"] = {}

    if df.empty:
        report["missing_days"]["totals"] = {"missing_days_count_total": 0}
        return True, report

    try:
        cal = xcals.get_calendar("XNYS")
        sessions = cal.sessions_in_range(start, end)
        expected_dates = set(s.date() for s in sessions)
        missing_days_per_symbol: dict[str, list[str]] = {}
        for symbol in df["symbol"].unique():
            symbol_df = df[df["symbol"] == symbol]
            symbol_df_ny = symbol_df.copy()
            symbol_df_ny["bar_date"] = (
                symbol_df_ny["ts"].dt.tz_convert(NY_TZ).dt.date
            )
            present_dates = set(symbol_df_ny["bar_date"])
            missing_dates = sorted(expected_dates - present_dates)
            if missing_dates:
                missing_days_per_symbol[str(symbol)] = [
                    d.isoformat() for d in missing_dates
                ]
        report["missing_days"] = missing_days_per_symbol
        report["missing_days"]["totals"] = {
            "missing_days_count_total": sum(
                len(dates) for dates in missing_days_per_symbol.values()
            )
        }
    except Exception as e:
        report["missing_days"]["error"] = str(e)
        report["missing_days"]["totals"] = {"missing_days_count_total": 0}

    return ok, report


def validate_weekly_bars(
    df: pd.DataFrame, *, start: date, end: date
) -> tuple[bool, dict[str, Any]]:
    """
    Validate weekly bars. Same checks as daily except missing trading days (set to empty).
    Report schema matches daily for downstream consistency.
    """
    report, ok = _validate_bars_issues(df, start=start, end=end)
    report["missing_days"] = {"totals": {"missing_days_count_total": 0}}
    return ok, report
