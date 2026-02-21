"""Custom exception classes for ohlcv-hub."""


class OhlcvHubError(Exception):
    """Base exception for all ohlcv-hub errors."""

    pass


class ConfigError(OhlcvHubError):
    """Raised when configuration is invalid or missing."""

    pass


class CliUsageError(OhlcvHubError):
    """Raised when CLI usage is incorrect."""

    pass


class ProviderError(OhlcvHubError):
    """Raised when a data provider API call fails."""

    def __init__(self, message: str, status_code: int | None = None):
        """
        Initialize ProviderError.

        Args:
            message: Error message
            status_code: HTTP status code if available
        """
        super().__init__(message)
        self.status_code = status_code
