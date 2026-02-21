# ohlcv-hub

A small dataset builder for US stocks and ETFs: fetch daily OHLCV bars from Alpaca, optionally resample to weekly, validate, and export to Parquet or CSV with a validation report (missing days, duplicates, OHLC sanity).

## Features

- **Daily bars (1d)**: Fetch historical daily bars from Alpaca Market Data API; normalize, validate, and export.
- **Weekly bars (1w)**: Resample daily bars to weekly (Monday 00:00 UTC); same validation and export.
- **Validation**: Duplicate detection, monotonic timestamps, OHLC sanity, volume checks; missing trading days (NYSE calendar).
- **Output**: Parquet (default) or CSV; optional `validation_report.json`.
- **Rate limiting**: Proactive throttling and 429 retry with backoff; optional `--verbose` debug logging.

## Quickstart

### Install

From PyPI (once published):

```bash
pip install ohlcv-hub
```

For local development:

```bash
pip install -e ".[dev]"
```

### Environment

Set your Alpaca credentials:

- `ALPACA_API_KEY` — required  
- `ALPACA_API_SECRET` — required  
- `ALPACA_DATA_BASE_URL` — optional (default: `https://data.alpaca.markets`)

### Example commands

```bash
# Check configuration
ohlcv-hub doctor

# Fetch daily bars (default feed: iex)
ohlcv-hub fetch --symbols SPY,QQQ --start 2024-01-01 --end 2024-02-01 --tf 1d --out ./data

# Fetch weekly bars (resampled from daily)
ohlcv-hub fetch --symbols SPY --start 2024-01-01 --end 2024-02-01 --tf 1w --out ./data

# Use a different feed: --feed iex | sip | boats | otc
ohlcv-hub fetch --symbols SPY --start 2024-01-01 --end 2024-01-10 --tf 1d --out ./data --feed sip
```

## Output

- **Daily**: `<out>/ohlcv_1d_<YYYYMMDD>_<YYYYMMDD>.parquet` (or `.csv`)  
- **Weekly**: `<out>/ohlcv_1w_<YYYYMMDD>_<YYYYMMDD>.parquet` (or `.csv`)  
- **Report** (if `--report`): `<out>/validation_report.json` (missing days, issues summary)

### Schema

| Column       | Description                    |
|-------------|---------------------------------|
| symbol      | Ticker (e.g. SPY)              |
| timeframe   | `1d` or `1w`                   |
| ts         | Bar timestamp (UTC)            |
| open, high, low, close | OHLC  |
| volume     | Volume                         |
| source     | Data source                    |
| currency   | Currency (e.g. USD)            |
| adjustment | Adjustment (e.g. raw)         |

## Notes / Limitations (MVP)

- **No intraday**: Daily and weekly bars only; no minute or realtime data.
- **No strategies**: Fetch, validate, and export only; no backtesting or signals.
- **Alpaca**: Requires an Alpaca account and data subscription. Free tier often includes IEX; SIP may require a paid plan. Use `--feed iex` (default) or `--feed sip` as appropriate.

## Development

```bash
pip install -e ".[dev]"
pytest -q
bandit -r ohlcv_hub -x tests -q
```

For dependency auditing (Python 3.10+): `pip install -e ".[audit]"` then `pip-audit`.

Internal release and security notes live under `docs/internal/`.

## License

MIT
