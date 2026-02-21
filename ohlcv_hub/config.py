"""Configuration management for ohlcv-hub."""

import os
from dataclasses import dataclass

from ohlcv_hub.errors import ConfigError


@dataclass
class Config:
    """Configuration for ohlcv-hub."""

    alpaca_api_key: str
    alpaca_api_secret: str
    alpaca_data_base_url: str = "https://data.alpaca.markets"


def load_config_from_env(require_keys: bool = True) -> Config:
    """
    Load configuration from environment variables.

    Args:
        require_keys: If True, raise ConfigError if API keys are missing.

    Returns:
        Config instance with loaded values.

    Raises:
        ConfigError: If require_keys=True and keys are missing.
    """
    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    base_url = os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")

    if require_keys:
        if not api_key:
            raise ConfigError(
                "ALPACA_API_KEY environment variable is required but not set."
            )
        if not api_secret:
            raise ConfigError(
                "ALPACA_API_SECRET environment variable is required but not set."
            )

    return Config(
        alpaca_api_key=api_key,
        alpaca_api_secret=api_secret,
        alpaca_data_base_url=base_url,
    )
