---
id: T02
parent: S09
milestone: M001
provides:
  - policyfoundry.__init__.py with __version__ = "0.1.0"
  - 14-class exception hierarchy in policyfoundry.exceptions
  - config module (5 files): models, loader, defaults, validation, __init__
key_files:
  - src/policyfoundry/__init__.py
  - src/policyfoundry/exceptions.py
  - src/policyfoundry/config/__init__.py
  - src/policyfoundry/config/models.py
  - src/policyfoundry/config/loader.py
  - src/policyfoundry/config/defaults.py
  - src/policyfoundry/config/validation.py
key_decisions:
  - D004 confirmed: PolicyFoundryError.details defaults to {} (empty dict, not None)
  - D005 confirmed: NoDecode + field_validator("before") for comma-separated env var lists
  - D006 confirmed: Only PolicyFoundryConfig is BaseSettings; nested LLMConfig/SourcesConfig/TargetsConfig/OutputConfig are BaseModel
  - D007 confirmed: YAML sources only added to pydantic-settings chain if file exists on disk
patterns_established:
  - Exception __init__ uses keyword-only args: __init__(self, message, *, error_code=None, details=None)
  - Config model_config uses SettingsConfigDict(env_prefix="POLICYFOUNDRY_", env_nested_delimiter="__", extra="ignore")
  - ConfigValidationError wraps pydantic ValidationError with error_code="CONFIG_INVALID" and structured details dict
observability_surfaces:
  - PolicyFoundryError.error_code (str|None) and PolicyFoundryError.details (dict) carry structured error context
  - ConfigValidationError includes field, error_type, message, raw_error in details dict
duration: 20m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T02: Reconstruct src root and config module from bytecode

**Reconstructed 7 source files from CPython 3.13 bytecode: package root, 14-class exception hierarchy, and full config module (models, loader, defaults, validation).**

## What Happened

Used `dis` module disassembly on all 7 `.pyc` files to extract exact class names, field names, default values, type annotations, import chains, and function bodies. Reconstructed each file preserving the original structure:

1. **`__init__.py`** — Simple: docstring + `__version__ = "0.1.0"`
2. **`exceptions.py`** — 14 exception classes with correct inheritance tree. `PolicyFoundryError(Exception)` base with `error_code` (str|None) and `details` (dict[str, Any]|None → defaults to `{}`). Hierarchy: ConfigError/ConfigFileNotFound/ConfigValidationError, IngestionError/ParseError/S3AccessError, StorageError, AdapterError/AdapterAuthenticationError/AdapterValidationError/AdapterNotFoundError, PipelineError, OutputError.
3. **`config/models.py`** — 5 Pydantic models. `PolicyFoundryConfig(BaseSettings)` with `SettingsConfigDict`, `settings_customise_sources` classmethod implementing YAML-aware merge chain. Nested `LLMConfig`, `SourcesConfig`, `TargetsConfig`, `OutputConfig` all `BaseModel`. `NoDecode` + `field_validator(mode="before")` for comma-separated list fields.
4. **`config/loader.py`** — `load_config(**overrides)` wraps `PolicyFoundryConfig` construction, catches `ValidationError` → raises `ConfigValidationError` with structured details.
5. **`config/defaults.py`** — `ConfigSource` enum, `AnnotatedValue` dataclass, `CONFIG_TEMPLATE` string, `_flatten_config`, `_load_yaml_flat`, `resolve_with_annotations` functions.
6. **`config/validation.py`** — `KNOWN_KEYS` dict, `warn_unknown_keys` with YAML parsing and fuzzy-match suggestions via `difflib.get_close_matches`.
7. **`config/__init__.py`** — Re-exports all public names with `__all__`.

## Verification

All 5 must-haves passed:

- ✅ `PolicyFoundryError` has `error_code` and `details` attributes with correct defaults (D004): `e.details == {}`
- ✅ All 14 exception classes exist with correct inheritance hierarchy (verified programmatically)
- ✅ `PolicyFoundryConfig` is `BaseSettings`; nested models are `BaseModel` (D006)
- ✅ `load_config(**overrides)` callable, returns `PolicyFoundryConfig` with correct defaults
- ✅ All 7 files import without error

Verification commands run:
```
uv run python -c "from policyfoundry.exceptions import PolicyFoundryError, ConfigError, IngestionError, StorageError, AdapterError, PipelineError, OutputError; e = PolicyFoundryError('test'); assert e.details == {}; print('OK')"  # → OK
uv run python -c "from policyfoundry.config.models import PolicyFoundryConfig; from policyfoundry.config.loader import load_config; print('OK')"  # → OK
```

Slice-level verification (intermediate — partial expected):
- `uv run pytest tests/test_exceptions/ -x` → 0 collected (test .py files not yet reconstructed, only .pyc)
- `uv run pytest tests/test_config/ -x` → 0 collected (same — test reconstruction is later tasks)
- `uv run pytest tests/test_cli/ -x` → 22 collected, 1 failed (expected: stubs from T01 with `pytest.fail`)

## Diagnostics

- Import any exception: `uv run python -c "from policyfoundry.exceptions import PolicyFoundryError; e = PolicyFoundryError('x', error_code='E1', details={'k':'v'}); print(e.error_code, e.details)"`
- Check config defaults: `uv run python -c "from policyfoundry.config.loader import load_config; c = load_config(); print(c.model_dump())"`
- Inspect config annotation sources: `from policyfoundry.config.defaults import resolve_with_annotations`

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/__init__.py` — package root with version string
- `src/policyfoundry/exceptions.py` — 14-class exception hierarchy
- `src/policyfoundry/config/__init__.py` — config package re-exports with __all__
- `src/policyfoundry/config/models.py` — Pydantic config models (BaseSettings root + BaseModel nested)
- `src/policyfoundry/config/loader.py` — load_config() entry point with ValidationError wrapping
- `src/policyfoundry/config/defaults.py` — CONFIG_TEMPLATE, ConfigSource enum, annotation utilities
- `src/policyfoundry/config/validation.py` — unknown key detection with fuzzy match suggestions
