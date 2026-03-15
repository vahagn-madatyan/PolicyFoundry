"""PolicyFoundry exception hierarchy.

All domain-specific exceptions inherit from PolicyFoundryError, which
provides structured error context via optional error_code and details.
"""

from typing import Any


class PolicyFoundryError(Exception):
    """Base exception for all PolicyFoundry errors.

    Provides structured error context with optional error_code and details.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.details = details if details is not None else {}


class ConfigError(PolicyFoundryError):
    """Configuration-related errors."""


class ConfigFileNotFound(ConfigError):
    """Config file does not exist at expected path."""


class ConfigValidationError(ConfigError):
    """Config file exists but contains invalid values."""


class IngestionError(PolicyFoundryError):
    """Log ingestion and parsing errors."""


class ParseError(IngestionError):
    """Line parsing failures during log ingestion."""


class ExcelParseError(IngestionError):
    """Excel file parsing and column detection errors."""


class S3AccessError(IngestionError):
    """S3 access issues during log ingestion."""


class StorageError(PolicyFoundryError):
    """Storage layer errors (Parquet, DuckDB)."""


class AdapterError(PolicyFoundryError):
    """Firewall adapter errors."""


class AdapterAuthenticationError(AdapterError):
    """Authentication failure when connecting to firewall service."""


class AdapterValidationError(AdapterError):
    """Validation failure for adapter rule or configuration."""


class AdapterNotFoundError(AdapterError):
    """Requested adapter name not found in registry."""


class PipelineError(PolicyFoundryError):
    """AI pipeline execution errors."""


class SafetyError(PolicyFoundryError):
    """Safety constraint violations (e.g. write attempts in read-only mode)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = "SAFETY_VIOLATION",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class OutputError(PolicyFoundryError):
    """Output formatting and rendering errors."""
