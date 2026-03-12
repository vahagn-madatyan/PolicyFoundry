"""Unknown key detection with fuzzy match suggestions.

Pre-parses YAML config files to detect unknown keys before Pydantic
processes them. Uses difflib.get_close_matches for "did you mean?"
suggestions. Unknown keys produce warnings but do NOT block loading.
"""

from __future__ import annotations

import difflib
import logging
from pathlib import Path
from typing import cast

import yaml

logger = logging.getLogger(__name__)

KNOWN_KEYS: dict[str, set[str]] = {
    "root": {"llm", "sources", "targets", "output"},
    "llm": {"provider", "model", "temperature", "max_tokens", "base_url", "api_key", "timeout"},
    "sources": {"log_paths", "s3_bucket", "s3_prefix", "aws_profile"},
    "targets": {"security_group_ids"},
    "output": {"format"},
}


def warn_unknown_keys(yaml_path: str | Path) -> list[str]:
    """Load YAML and warn about unknown keys with 'did you mean?' suggestions.

    Args:
        yaml_path: Path to the YAML config file.

    Returns:
        List of warning messages for unknown keys.
    """
    path = Path(yaml_path)
    if not path.exists():
        return []

    with path.open() as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return []

    typed_data = cast("dict[str, object]", data)

    warnings: list[str] = []

    # Check root-level keys
    for key in typed_data:
        if key not in KNOWN_KEYS["root"]:
            msg = _build_warning(
                key, KNOWN_KEYS["root"], path.name
            )
            warnings.append(msg)
            logger.warning(msg)

    # Check section-level keys
    for section in ("llm", "sources", "targets", "output"):
        section_data = typed_data.get(section)
        if not isinstance(section_data, dict):
            continue
        if section not in KNOWN_KEYS:
            continue
        section_dict = cast("dict[str, object]", section_data)

        for key in section_dict:
            if key not in KNOWN_KEYS[section]:
                msg = _build_warning(
                    key, KNOWN_KEYS[section], section
                )
                warnings.append(msg)
                logger.warning(msg)

    return warnings


def _build_warning(key: str, known: set[str], context: str) -> str:
    """Build a warning message for an unknown key."""
    matches = difflib.get_close_matches(
        key, list(known), n=1, cutoff=0.6
    )
    if matches:
        return (
            f"Unknown config key '{key}' in {context}. "
            f"Did you mean '{matches[0]}'?"
        )
    return f"Unknown config key '{key}' in {context}. Ignoring."
