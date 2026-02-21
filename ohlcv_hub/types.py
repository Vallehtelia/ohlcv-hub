"""Type definitions for ohlcv-hub."""

from enum import Enum


class Timeframe(str, Enum):
    """Supported timeframes for data fetching."""

    DAILY = "1d"
    WEEKLY = "1w"


class OutputFormat(str, Enum):
    """Supported output formats."""

    PARQUET = "parquet"
    CSV = "csv"


class Adjustment(str, Enum):
    """Stock adjustment options."""

    RAW = "raw"
    ALL = "all"


class Provider(str, Enum):
    """Data provider options."""

    ALPACA = "alpaca"


class Feed(str, Enum):
    """Alpaca market data feed options."""

    IEX = "iex"
    SIP = "sip"
    BOATS = "boats"
    OTC = "otc"
