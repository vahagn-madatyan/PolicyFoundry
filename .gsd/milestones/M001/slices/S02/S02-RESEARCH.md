# Phase 2: Configuration System - Research

**Researched:** 2026-03-08
**Domain:** Python configuration management (pydantic-settings + YAML)
**Confidence:** HIGH

## Summary

Phase 2 implements a YAML-based configuration system with environment variable overrides using pydantic-settings with its built-in `YamlConfigSettingsSource`. The stack is straightforward: pydantic-settings v2 handles the entire config lifecycle -- YAML loading, env var parsing, nested model validation, and source priority merging. PyYAML is pulled in automatically via the `pydantic-settings[yaml]` extra.

The merge order (global YAML -> local YAML -> env vars -> `--config` flag) maps directly to pydantic-settings' `settings_customise_sources` method, where the **first item in the returned tuple has highest priority**. Unknown YAML keys need custom handling via a YAML pre-validation hook, since pydantic-settings will reject unknown fields by default (or silently ignore them with `extra="ignore"`).

**Primary recommendation:** Use `pydantic-settings[yaml]>=2.13` with `YamlConfigSettingsSource` explicitly in `settings_customise_sources` (not via `SettingsConfigDict` yaml_file key). Handle comma-separated env var lists via `NoDecode` + `field_validator`. Use `difflib.get_close_matches` (stdlib) for "did you mean?" suggestions on unknown keys.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Config file structure: grouped by domain -- `llm:`, `sources:`, `targets:`, `output:` top-level sections
- No profiles -- single config file, single context
- Merge order (later wins): global (`~/.policyfoundry/config.yaml`) -> local (`.policyfoundry.yaml` in CWD) -> env vars -> `--config` flag
- Unknown keys: warn with "did you mean?" suggestions, but don't fail -- continue with valid config
- Run with sensible defaults when no config file exists (ollama, llama3.2, rich output)
- `policyfoundry init` command generates commented `~/.policyfoundry/config.yaml` with all defaults and explanations
- `policyfoundry config show` displays resolved config with source annotations (which value came from where)
- Validation is lazy -- only validate fields required by the current command
- Env var prefix: `POLICYFOUNDRY_`
- Nesting separator: double underscore (`llm.provider` -> `POLICYFOUNDRY_LLM__PROVIDER`)
- Lists: comma-separated strings parsed into lists (`POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS=sg-abc,sg-def`)
- Secrets: regular env vars only, no .env file loading, no secret references in YAML
- LLM provider fields: `provider` (ollama | bedrock | openai), `model`, `temperature` (0.1), `max_tokens` (4096), `base_url` (null), `api_key` (null), `timeout` (120s)
- Provider validation: known set with warning on unknown -- doesn't block
- Source fields: separate `log_paths` (list, glob), `s3_bucket`, `s3_prefix`, `aws_profile` -- not a unified URI scheme
- Error messages use `ConfigValidationError` from Phase 1 with field name and expected format in details

### Claude's Discretion
- Pydantic Settings model structure and nesting approach
- YAML loading library choice (PyYAML vs ruamel.yaml vs pydantic-settings YAML support)
- Config merge implementation details
- "Did you mean?" fuzzy matching algorithm for unknown keys
- Default values for sources and targets sections
- `config show` formatting and color scheme

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-01 | User can configure the tool via YAML file (~/.policyfoundry/config.yaml) with environment variable overrides | pydantic-settings `YamlConfigSettingsSource` + `env_prefix` + `env_nested_delimiter` provides this natively; `settings_customise_sources` controls merge priority |
| CONF-02 | User can set LLM provider, model, log sources, and target security groups in config | Nested Pydantic models (`LLMConfig`, `SourcesConfig`, `TargetsConfig`) map directly to YAML sections and env var nesting |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic-settings | >=2.13,<3 | Settings management with env vars + file sources | Official Pydantic companion; handles env parsing, nested models, source priority natively |
| PyYAML | >=6.0 (via pydantic-settings[yaml]) | YAML file parsing | Pulled in automatically by pydantic-settings yaml extra; most widely used Python YAML parser |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| difflib (stdlib) | N/A | Fuzzy string matching | "Did you mean?" suggestions for unknown config keys via `get_close_matches` |
| pathlib (stdlib) | N/A | Path handling | Config file path expansion (`~`, `.`) and existence checks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-settings[yaml] | Manual PyYAML + Pydantic BaseModel | Lose env var merging, source priority, nested delimiter support; must hand-roll everything |
| PyYAML (via pydantic-settings) | ruamel.yaml | ruamel preserves comments (useful for round-tripping), but pydantic-settings bundles PyYAML in its yaml extra; no benefit unless we edit YAML programmatically |
| difflib.get_close_matches | thefuzz / rapidfuzz | External dependency for a single call site; difflib is stdlib with 0.6 cutoff default that works well for config key matching |

**Recommendation (Claude's Discretion):** Use `pydantic-settings[yaml]` -- it pulls PyYAML automatically and provides the `YamlConfigSettingsSource` class. No need for a separate PyYAML dependency or ruamel.yaml.

**Installation:**
```bash
uv add "pydantic-settings[yaml]>=2.13"
```

## Architecture Patterns

### Recommended Project Structure
```
src/policyfoundry/config/
    __init__.py          # Public API: load_config(), get_config(), PolicyFoundryConfig
    models.py            # Pydantic Settings models (LLMConfig, SourcesConfig, etc.)
    loader.py            # Config loading logic, source priority, multi-file merge
    defaults.py          # Default values, template for `policyfoundry init`
    validation.py        # Unknown key warnings, lazy validation, "did you mean?"
```

### Pattern 1: Nested Pydantic Settings Models
**What:** Use nested `BaseModel` subclasses within a root `BaseSettings` class to represent YAML section hierarchy.
**When to use:** Always -- this is the canonical pydantic-settings approach for structured config.
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = "ollama"
    model: str = "llama3.2"
    temperature: float = 0.1
    max_tokens: int = 4096
    base_url: str | None = None
    api_key: str | None = None
    timeout: int = 120

class SourcesConfig(BaseModel):
    """Log source configuration."""
    log_paths: list[str] = Field(default_factory=list)
    s3_bucket: str | None = None
    s3_prefix: str | None = None
    aws_profile: str | None = None

class TargetsConfig(BaseModel):
    """Target security group configuration."""
    security_group_ids: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("security_group_ids", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

class OutputConfig(BaseModel):
    """Output formatting configuration."""
    format: str = "rich"  # rich | json

class PolicyFoundryConfig(BaseSettings):
    """Root configuration with env var and YAML support."""
    model_config = SettingsConfigDict(
        env_prefix="POLICYFOUNDRY_",
        env_nested_delimiter="__",
    )

    llm: LLMConfig = Field(default_factory=LLMConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    targets: TargetsConfig = Field(default_factory=TargetsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
```

### Pattern 2: Custom Source Priority Chain
**What:** Override `settings_customise_sources` to implement the locked merge order: global YAML -> local YAML -> env vars -> --config flag.
**When to use:** Always -- pydantic-settings' default source order doesn't match the project's requirements.
**Critical detail:** First item in the tuple has HIGHEST priority. So `--config` flag goes first, env vars second, local YAML third, global YAML last.
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)
from pathlib import Path

class PolicyFoundryConfig(BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources: list[PydanticBaseSettingsSource] = []

        # Highest priority: --config flag (passed via init_settings)
        sources.append(init_settings)

        # Second: environment variables
        sources.append(env_settings)

        # Third: local .policyfoundry.yaml in CWD
        local_yaml = Path.cwd() / ".policyfoundry.yaml"
        if local_yaml.exists():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=local_yaml)
            )

        # Lowest priority: global ~/.policyfoundry/config.yaml
        global_yaml = Path.home() / ".policyfoundry" / "config.yaml"
        if global_yaml.exists():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=global_yaml)
            )

        return tuple(sources)
```

### Pattern 3: Unknown Key Detection with "Did You Mean?"
**What:** Pre-parse YAML to detect unknown keys before passing to Pydantic, warn with fuzzy match suggestions.
**When to use:** Always -- the user decision requires warning on unknown keys without failing.
**Example:**
```python
import difflib
import yaml
from pathlib import Path

KNOWN_TOP_KEYS = {"llm", "sources", "targets", "output"}
KNOWN_LLM_KEYS = {"provider", "model", "temperature", "max_tokens", "base_url", "api_key", "timeout"}
# ... etc. for each section

def check_unknown_keys(
    yaml_data: dict[str, object],
    known_keys: set[str],
    section: str = "root",
) -> list[str]:
    """Return warning messages for unknown keys with suggestions."""
    warnings: list[str] = []
    for key in yaml_data:
        if key not in known_keys:
            matches = difflib.get_close_matches(key, list(known_keys), n=1, cutoff=0.6)
            if matches:
                warnings.append(
                    f"Unknown config key '{key}' in {section}. Did you mean '{matches[0]}'?"
                )
            else:
                warnings.append(f"Unknown config key '{key}' in {section}. Ignoring.")
    return warnings
```

### Pattern 4: Comma-Separated Env Var Lists via NoDecode
**What:** Use `NoDecode` annotation + `field_validator` to parse comma-separated strings from env vars into Python lists.
**When to use:** For list fields that users set via env vars (security_group_ids, log_paths).
**Why needed:** pydantic-settings defaults to JSON parsing for complex types from env vars (`'["a","b"]'`). The user decision specifies comma-separated (`sg-abc,sg-def`).
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from typing import Annotated
from pydantic import Field, field_validator
from pydantic_settings import NoDecode

class TargetsConfig(BaseModel):
    security_group_ids: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("security_group_ids", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
```

### Pattern 5: Source Annotation for `config show`
**What:** Track which source each config value came from (default, global YAML, local YAML, env var).
**When to use:** For the `policyfoundry config show` command.
**Implementation approach:** Load each source separately, compare values against defaults and each source layer to determine provenance.
**Example:**
```python
from dataclasses import dataclass
from enum import Enum

class ConfigSource(Enum):
    DEFAULT = "default"
    GLOBAL_YAML = "~/.policyfoundry/config.yaml"
    LOCAL_YAML = ".policyfoundry.yaml"
    ENV_VAR = "env"
    CLI_FLAG = "--config"

@dataclass
class AnnotatedValue:
    value: object
    source: ConfigSource
    key: str

def resolve_with_annotations(config: PolicyFoundryConfig) -> dict[str, AnnotatedValue]:
    """Resolve config and annotate each value with its source."""
    # Load each layer separately and compare
    # ...
```

### Anti-Patterns to Avoid
- **Using `yaml_file` in `SettingsConfigDict` alone:** As of pydantic-settings 2.13.x, the `yaml_file` key in `SettingsConfigDict` has had issues with not being used by the source. Always explicitly pass `yaml_file` to `YamlConfigSettingsSource` in `settings_customise_sources`.
- **Using `yaml.load()` without SafeLoader:** pydantic-settings handles this internally via PyYAML, but if loading YAML manually (e.g., for unknown key detection), always use `yaml.safe_load()`.
- **Building a custom config merge engine:** pydantic-settings' source priority system IS the merge engine. Don't manually merge dicts -- let the framework handle it.
- **Using `extra="forbid"` on the settings model:** This would reject unknown keys with an error. The user decision says warn and continue. Use `extra="ignore"` on the Pydantic model combined with a pre-validation YAML scan for unknown keys.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var to nested config parsing | Custom env var parser that splits on `__` | `pydantic-settings` `env_nested_delimiter="__"` | Handles all nesting depths, type coercion, prefix stripping |
| Config source priority/merging | Dict deep-merge utility | `settings_customise_sources` tuple ordering | Framework-native; handles edge cases (None vs missing, nested overrides) |
| YAML file loading | `yaml.safe_load()` + manual dict-to-model | `YamlConfigSettingsSource` | Handles encoding, missing files, nested models automatically |
| Config validation | Manual type checking | Pydantic v2 validators | Already the project standard; gives field-level error messages |
| Fuzzy string matching | Levenshtein distance implementation | `difflib.get_close_matches` (stdlib) | Battle-tested, configurable cutoff, zero dependencies |
| Comma-separated list parsing | Custom string splitter + env var detection | `NoDecode` + `field_validator` | pydantic-settings native pattern; works with all sources |

**Key insight:** pydantic-settings was designed precisely for this use case. The only custom code needed is: (1) unknown key detection/warnings, (2) config template generation for `init`, and (3) source annotation for `config show`.

## Common Pitfalls

### Pitfall 1: yaml_file in SettingsConfigDict Silently Ignored
**What goes wrong:** Setting `yaml_file='config.yaml'` in `SettingsConfigDict` without adding `YamlConfigSettingsSource` to `settings_customise_sources`. Config loads with only defaults and env vars -- no YAML values.
**Why it happens:** GitHub issue #660 -- the `yaml_file` config key is defined but was not wired to automatically create a YAML source. A warning was added in recent versions but the behavior remains: you must explicitly add the source.
**How to avoid:** Always use `settings_customise_sources` to explicitly create and return `YamlConfigSettingsSource` instances.
**Warning signs:** Config values always showing defaults despite having a valid YAML file.

### Pitfall 2: Source Priority Order Reversed
**What goes wrong:** Putting global YAML first in the tuple, making it highest priority instead of lowest.
**Why it happens:** Intuition says "list sources in order of loading" (global first, then local, then env). But pydantic-settings tuple order means **first = highest priority**.
**How to avoid:** Remember: first in tuple = wins. Order: `(init_settings, env_settings, local_yaml, global_yaml)`.
**Warning signs:** Env vars not overriding YAML values.

### Pitfall 3: Complex Types from Env Vars Require JSON by Default
**What goes wrong:** Setting `POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS=sg-abc,sg-def` and getting a validation error because pydantic-settings tries to parse it as JSON.
**Why it happens:** pydantic-settings defaults to JSON decoding for complex types (list, dict, sub-models) from environment variables.
**How to avoid:** Use `Annotated[list[str], NoDecode]` with a `field_validator(mode="before")` that splits on comma.
**Warning signs:** `json.JSONDecodeError` or Pydantic `ValidationError` when setting list fields via env vars.

### Pitfall 4: Path Expansion for Home Directory
**What goes wrong:** Using `"~/.policyfoundry/config.yaml"` as a string without expanding it, causing FileNotFoundError.
**Why it happens:** `~` is a shell convention; Python `Path` doesn't expand it automatically unless you call `.expanduser()`.
**How to avoid:** Always use `Path.home() / ".policyfoundry" / "config.yaml"` or `Path("~/.policyfoundry/config.yaml").expanduser()`.
**Warning signs:** "File not found" errors with `~` in the path.

### Pitfall 5: Env Var Prefix Case Sensitivity
**What goes wrong:** Setting `policyfoundry_llm__provider=openai` (lowercase) and it not being picked up.
**Why it happens:** By default, pydantic-settings is case-insensitive for env vars on most systems, but best practice is to document uppercase convention.
**How to avoid:** Document that env vars should be uppercase: `POLICYFOUNDRY_LLM__PROVIDER`. Consider setting `case_sensitive=False` explicitly in `SettingsConfigDict` (this is the default).
**Warning signs:** Inconsistent env var behavior across systems.

### Pitfall 6: Nested Model Defaults Not Merging Properly
**What goes wrong:** Setting one field in a YAML section (e.g., `llm.provider: bedrock`) and losing all other defaults in that section.
**Why it happens:** Without proper handling, setting a nested model from YAML might replace the entire sub-model rather than merging with defaults.
**How to avoid:** Use `Field(default_factory=LLMConfig)` for nested models, not `Field(default=LLMConfig())`. Pydantic-settings handles partial overrides correctly when defaults are set on individual fields within the nested model.
**Warning signs:** Setting `llm.provider` in YAML causes `llm.temperature` to become None instead of 0.1.

## Code Examples

Verified patterns from official sources:

### Complete Config Model Skeleton
```python
# Based on: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class LLMConfig(BaseModel):
    """LLM provider settings."""

    provider: str = "ollama"
    model: str = "llama3.2"
    temperature: float = 0.1
    max_tokens: int = 4096
    base_url: str | None = None
    api_key: str | None = None
    timeout: int = 120


class SourcesConfig(BaseModel):
    """Log source settings."""

    log_paths: Annotated[list[str], NoDecode] = Field(default_factory=list)
    s3_bucket: str | None = None
    s3_prefix: str | None = None
    aws_profile: str | None = None

    @field_validator("log_paths", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


class TargetsConfig(BaseModel):
    """Target security group settings."""

    security_group_ids: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("security_group_ids", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


class OutputConfig(BaseModel):
    """Output formatting settings."""

    format: str = "rich"


class PolicyFoundryConfig(BaseSettings):
    """Root configuration for PolicyFoundry."""

    model_config = SettingsConfigDict(
        env_prefix="POLICYFOUNDRY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    llm: LLMConfig = Field(default_factory=LLMConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    targets: TargetsConfig = Field(default_factory=TargetsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources: list[PydanticBaseSettingsSource] = []

        # Highest priority: init kwargs (--config flag values)
        sources.append(init_settings)

        # Second: environment variables
        sources.append(env_settings)

        # Third: local .policyfoundry.yaml
        local_yaml = Path.cwd() / ".policyfoundry.yaml"
        if local_yaml.exists():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=local_yaml)
            )

        # Lowest: global config
        global_yaml = Path.home() / ".policyfoundry" / "config.yaml"
        if global_yaml.exists():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=global_yaml)
            )

        return tuple(sources)
```

### Config Loading Function with Error Handling
```python
import logging
from policyfoundry.exceptions import ConfigValidationError

logger = logging.getLogger(__name__)

def load_config(**overrides: object) -> PolicyFoundryConfig:
    """Load config with merge order: global YAML < local YAML < env vars < overrides.

    Raises:
        ConfigValidationError: If config values fail validation.
    """
    try:
        config = PolicyFoundryConfig(**overrides)  # type: ignore[arg-type]
    except Exception as exc:
        raise ConfigValidationError(
            str(exc),
            error_code="CONFIG_INVALID",
            details={"raw_error": str(exc)},
        ) from exc
    return config
```

### YAML Template for `policyfoundry init`
```python
CONFIG_TEMPLATE = """\
# PolicyFoundry Configuration
# Generated by: policyfoundry init
# Docs: https://github.com/policyfoundry/policyfoundry

# LLM Provider Settings
llm:
  # Provider: ollama | bedrock | openai
  provider: ollama
  # Model name or ID
  model: llama3.2
  # Temperature for analysis consistency (lower = more deterministic)
  # temperature: 0.1
  # Max tokens per LLM call
  # max_tokens: 4096
  # Custom API endpoint (for self-hosted or proxy)
  # base_url: null
  # API key (prefer env var POLICYFOUNDRY_LLM__API_KEY instead)
  # api_key: null
  # Request timeout in seconds
  # timeout: 120

# Log Sources
sources:
  # Local log file paths (glob patterns supported)
  # log_paths:
  #   - /var/log/vpc-flow/*.log
  #   - ./logs/**/*.log.gz
  # S3 bucket for remote logs
  # s3_bucket: my-vpc-logs-bucket
  # S3 key prefix filter
  # s3_prefix: vpc-flow-logs/
  # AWS profile for S3 access
  # aws_profile: default

# Target Security Groups
targets:
  # Security Group IDs to analyze
  # security_group_ids:
  #   - sg-0123456789abcdef0

# Output Settings
output:
  # Output format: rich (terminal) | json (machine-readable)
  format: rich
"""
```

### Unknown Key Detection
```python
import difflib
import logging

import yaml

logger = logging.getLogger(__name__)

# Map of section -> known keys
KNOWN_KEYS: dict[str, set[str]] = {
    "root": {"llm", "sources", "targets", "output"},
    "llm": {"provider", "model", "temperature", "max_tokens", "base_url", "api_key", "timeout"},
    "sources": {"log_paths", "s3_bucket", "s3_prefix", "aws_profile"},
    "targets": {"security_group_ids"},
    "output": {"format"},
}

def warn_unknown_keys(yaml_path: str | Path) -> list[str]:
    """Load YAML and warn about unknown keys with 'did you mean?' suggestions."""
    path = Path(yaml_path)
    if not path.exists():
        return []

    with path.open() as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return []

    warnings: list[str] = []

    # Check top-level keys
    for key in data:
        if key not in KNOWN_KEYS["root"]:
            matches = difflib.get_close_matches(str(key), list(KNOWN_KEYS["root"]), n=1, cutoff=0.6)
            suggestion = f" Did you mean '{matches[0]}'?" if matches else ""
            msg = f"Unknown config key '{key}' in {path.name}.{suggestion} Ignoring."
            warnings.append(msg)
            logger.warning(msg)

    # Check section-level keys
    for section in ("llm", "sources", "targets", "output"):
        section_data = data.get(section)
        if isinstance(section_data, dict) and section in KNOWN_KEYS:
            for key in section_data:
                if key not in KNOWN_KEYS[section]:
                    matches = difflib.get_close_matches(
                        str(key), list(KNOWN_KEYS[section]), n=1, cutoff=0.6
                    )
                    suggestion = f" Did you mean '{matches[0]}'?" if matches else ""
                    msg = f"Unknown config key '{key}' in {section}.{suggestion} Ignoring."
                    warnings.append(msg)
                    logger.warning(msg)

    return warnings
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydantic-settings v1 (`env_file` only) | pydantic-settings v2 with file sources (YAML, TOML, JSON) | 2023 (v2.0) | Native multi-format config; no third-party wrappers needed |
| Custom `EnvSettingsSource` subclass for comma lists | `NoDecode` + `field_validator` | pydantic-settings ~2.5+ | Cleaner, declarative approach; no subclassing |
| Separate PyYAML dependency | `pydantic-settings[yaml]` extra | pydantic-settings ~2.1+ | Single install, automatic integration |
| `env_file=".env"` for all config | Explicit source priority via `settings_customise_sources` | pydantic-settings v2 | Full control over merge semantics |

**Deprecated/outdated:**
- `pydantic-settings-yaml` (third-party): Unnecessary now that pydantic-settings has native YAML support
- `yaml-settings-pydantic` (third-party): Same -- native support supersedes
- Manual `yaml.safe_load()` + `BaseModel(**data)`: Loses env var integration and source priority

## Open Questions

1. **NoDecode availability in strict pyright**
   - What we know: `NoDecode` is a `pydantic_settings` export used as a type annotation
   - What's unclear: Whether pyright strict mode handles the `Annotated[list[str], NoDecode]` pattern without type errors
   - Recommendation: Verify during implementation; if pyright complains, add targeted `type: ignore` comments (precedent from Phase 1)

2. **Lazy validation scope**
   - What we know: User decided "only validate fields required by the current command"
   - What's unclear: How to implement per-command lazy validation cleanly with pydantic-settings (Pydantic validates all fields by default on instantiation)
   - Recommendation: Use optional fields with `None` defaults for fields that are only required by specific commands; validate required fields in the command handler, not in the config model. Alternatively, use separate config models per command context with only required fields.

3. **Config show source annotation implementation**
   - What we know: User wants each value annotated with its source (default, env, global yaml, local yaml)
   - What's unclear: pydantic-settings doesn't natively expose which source provided each value
   - Recommendation: Load each source layer independently (just defaults, just global yaml, just env), compare against final resolved config to determine provenance. This is custom logic but straightforward.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_config/ -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-01 | Load config from ~/.policyfoundry/config.yaml | unit | `uv run pytest tests/test_config/test_loader.py::test_load_global_yaml -x` | Wave 0 |
| CONF-01 | Env var overrides YAML values | unit | `uv run pytest tests/test_config/test_loader.py::test_env_overrides_yaml -x` | Wave 0 |
| CONF-01 | Merge order: global < local < env < flag | unit | `uv run pytest tests/test_config/test_loader.py::test_merge_priority_order -x` | Wave 0 |
| CONF-01 | Missing config file uses defaults | unit | `uv run pytest tests/test_config/test_loader.py::test_defaults_when_no_config -x` | Wave 0 |
| CONF-01 | Env var nested delimiter (double underscore) | unit | `uv run pytest tests/test_config/test_loader.py::test_env_nested_delimiter -x` | Wave 0 |
| CONF-02 | LLM provider/model in config | unit | `uv run pytest tests/test_config/test_models.py::test_llm_config_fields -x` | Wave 0 |
| CONF-02 | Log source paths in config | unit | `uv run pytest tests/test_config/test_models.py::test_sources_config_fields -x` | Wave 0 |
| CONF-02 | Security group IDs in config | unit | `uv run pytest tests/test_config/test_models.py::test_targets_config_fields -x` | Wave 0 |
| CONF-02 | Comma-separated env var list parsing | unit | `uv run pytest tests/test_config/test_models.py::test_comma_separated_list -x` | Wave 0 |
| CONF-01 | Invalid config produces clear error with field name | unit | `uv run pytest tests/test_config/test_validation.py::test_invalid_config_error_message -x` | Wave 0 |
| CONF-01 | Unknown keys produce "did you mean?" warning | unit | `uv run pytest tests/test_config/test_validation.py::test_unknown_key_suggestion -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_config/ -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config/__init__.py` -- package init
- [ ] `tests/test_config/test_models.py` -- covers CONF-02 model validation
- [ ] `tests/test_config/test_loader.py` -- covers CONF-01 loading and merge
- [ ] `tests/test_config/test_validation.py` -- covers CONF-01 error messages and unknown keys
- [ ] `tests/test_config/conftest.py` -- shared fixtures (tmp config dirs, sample YAML)
- [ ] Dependency install: `uv add "pydantic-settings[yaml]>=2.13"` -- required before any tests run

## Sources

### Primary (HIGH confidence)
- [pydantic-settings official docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - settings_customise_sources, env_prefix, env_nested_delimiter, NoDecode + field_validator pattern, source priority order
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) - version 2.13.1, yaml extra dependency (PyYAML)
- [pydantic-settings API docs](https://docs.pydantic.dev/latest/api/pydantic_settings/) - YamlConfigSettingsSource, SettingsConfigDict, PydanticBaseSettingsSource

### Secondary (MEDIUM confidence)
- [pydantic-settings GitHub issue #660](https://github.com/pydantic/pydantic-settings/issues/660) - yaml_file in SettingsConfigDict not wired to source (fixed but pattern still recommended)
- [pydantic-settings GitHub issue #291](https://github.com/pydantic/pydantic-settings/issues/291) - comma-delimited string parsing approaches
- [deepwiki pydantic-settings configuration files](https://deepwiki.com/pydantic/pydantic-settings/3.2-configuration-files) - YAML source patterns, PyYAML dependency confirmation
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) - get_close_matches API

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pydantic-settings is the canonical choice; verified version, extras, API patterns against official docs
- Architecture: HIGH - patterns directly from official docs and verified GitHub issues; model structure follows existing Phase 1 conventions
- Pitfalls: HIGH - yaml_file SettingsConfigDict issue verified via GitHub issue #660; source priority order confirmed in multiple official sources
- Validation: HIGH - test framework already established in Phase 1; test patterns are straightforward unit tests with tmp_path fixtures

**Research date:** 2026-03-08
**Valid until:** 2026-04-07 (30 days -- pydantic-settings is stable, unlikely to change significantly)