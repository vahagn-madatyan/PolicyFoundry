"""Configuration loader with source priority chain.

Provides load_config() as the primary entry point for loading PolicyFoundry
configuration. Most merge logic lives in PolicyFoundryConfig.settings_customise_sources;
this module adds error handling that wraps Pydantic ValidationError into
ConfigValidationError for user-friendly error messages.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from policyfoundry.config.models import PolicyFoundryConfig
from policyfoundry.config.validation import warn_unknown_keys
from policyfoundry.exceptions import ConfigValidationError

logger = logging.getLogger(__name__)


def load_config(**overrides: Any) -> PolicyFoundryConfig:
    """Load config with merge order: global YAML < local YAML < env vars < overrides.

    Args:
        **overrides: Key-value pairs to override config values.

    Returns:
        Fully resolved PolicyFoundryConfig instance.

    Raises:
        ConfigValidationError: If config values fail Pydantic validation.
            Wraps the original ValidationError with structured details
            including the failing field, error type, and message.
    """
    _warn_yaml_files()

    try:
        return PolicyFoundryConfig(**overrides)
    except ValidationError as exc:
        errors = exc.errors()
        details: dict[str, Any] = {"raw_error": str(exc)}
        if errors:
            first_error = errors[0]
            field_loc = first_error.get("loc", ())
            if field_loc:
                details["field"] = ".".join(str(part) for part in field_loc)
            details["error_type"] = first_error.get("type", "unknown")
            details["message"] = first_error.get("msg", "")
        raise ConfigValidationError(
            str(exc),
            error_code="CONFIG_INVALID",
            details=details,
        ) from exc


def _warn_yaml_files() -> None:
    """Check known YAML config file paths for unknown keys."""
    local_yaml = Path.cwd() / ".policyfoundry.yaml"
    global_yaml = Path.home() / ".policyfoundry" / "config.yaml"

    for yaml_path in (local_yaml, global_yaml):
        warn_unknown_keys(yaml_path)
