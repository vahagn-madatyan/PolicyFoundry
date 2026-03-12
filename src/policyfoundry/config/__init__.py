"""PolicyFoundry configuration system.

Public API for loading and accessing configuration with YAML file support,
environment variable overrides, and sensible defaults.
"""

from policyfoundry.config.defaults import (
    CONFIG_TEMPLATE,
    AnnotatedValue,
    ConfigSource,
    resolve_with_annotations,
)
from policyfoundry.config.loader import load_config
from policyfoundry.config.models import (
    LLMConfig,
    OutputConfig,
    PolicyFoundryConfig,
    SourcesConfig,
    TargetsConfig,
)
from policyfoundry.config.validation import warn_unknown_keys

__all__ = [
    "CONFIG_TEMPLATE",
    "AnnotatedValue",
    "ConfigSource",
    "LLMConfig",
    "OutputConfig",
    "PolicyFoundryConfig",
    "SourcesConfig",
    "TargetsConfig",
    "load_config",
    "resolve_with_annotations",
    "warn_unknown_keys",
]
