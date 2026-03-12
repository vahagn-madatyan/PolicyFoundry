---
estimated_steps: 4
estimated_files: 7
---

# T02: Reconstruct src root and config module from bytecode

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the foundational source files: root `__init__.py`, the full exception hierarchy in `exceptions.py`, and the entire config module (5 files). The exception hierarchy is imported by every other module. The config module is the first call in the CLI pipeline (`load_config()`). Both must be correct before any downstream reconstruction.

Uses the T01 toolkit + `.venv/bin/python3 -m dis`-style disassembly to recover source. For Pydantic models in `config/models.py`, field names, types, and defaults are extractable from code object constants. For `exceptions.py`, the class hierarchy is clear from `LOAD_BUILD_CLASS` instructions.

## Steps

1. **Reconstruct `src/policyfoundry/__init__.py`** — Typically a version string and key re-exports. Extract from bytecode constants.

2. **Reconstruct `src/policyfoundry/exceptions.py`** — Full hierarchy: `PolicyFoundryError(Exception)` base with `__init__(self, message, error_code=None, details=None)` (details defaults to `{}` per D004), then `ConfigError`, `ConfigFileNotFound(ConfigError)`, `ConfigValidationError(ConfigError)`, `IngestionError`, `ParseError(IngestionError)`, `S3AccessError(IngestionError)`, `StorageError`, `AdapterError`, `AdapterAuthenticationError(AdapterError)`, `AdapterValidationError(AdapterError)`, `AdapterNotFoundError(AdapterError)`, `PipelineError`, `OutputError`. Each is a simple subclass with a docstring. Verify class hierarchy matches bytecode structure.

3. **Reconstruct config module** — 5 files:
   - `config/__init__.py` — re-exports from submodules
   - `config/defaults.py` — default configuration constants (6.2KB pyc — medium complexity)
   - `config/models.py` — Pydantic `PolicyFoundryConfig(BaseSettings)` with nested `LLMConfig`, `SourcesConfig`, `TargetsConfig`, `OutputConfig` (per D005 comma-separated env vars, D006 nested BaseModel not BaseSettings, D007 YAML source handling)
   - `config/validation.py` — config validation functions
   - `config/loader.py` — `load_config(**overrides) -> PolicyFoundryConfig` entry point

4. **Verify all imports** — Run import checks for every reconstructed module. Fix any import errors or missing attributes.

## Must-Haves

- [ ] `PolicyFoundryError` has `error_code` and `details` attributes with correct defaults (D004)
- [ ] All 14 exception classes exist with correct inheritance hierarchy
- [ ] `PolicyFoundryConfig` is a `BaseSettings` subclass; nested models are `BaseModel` (D006)
- [ ] `load_config(**overrides)` is callable and returns `PolicyFoundryConfig`
- [ ] All 7 files import without error

## Verification

- `uv run python -c "from policyfoundry.exceptions import PolicyFoundryError, ConfigError, IngestionError, StorageError, AdapterError, PipelineError, OutputError; e = PolicyFoundryError('test'); assert e.details == {}; print('OK')"`
- `uv run python -c "from policyfoundry.config.models import PolicyFoundryConfig; from policyfoundry.config.loader import load_config; print('OK')"`

## Observability Impact

- Signals added/changed: None (reconstruction only, no new runtime behavior)
- How a future agent inspects this: Import any exception class and check `error_code`/`details` attributes
- Failure state exposed: None

## Inputs

- `src/policyfoundry/__pycache__/__init__.cpython-313.pyc` (268 bytes)
- `src/policyfoundry/__pycache__/exceptions.cpython-313.pyc` (4154 bytes)
- `src/policyfoundry/config/__pycache__/*.cpython-313.pyc` (5 files, 920–6223 bytes)
- `tools/inspect_pyc.py` from T01
- Decisions D004, D005, D006, D007

## Expected Output

- `src/policyfoundry/__init__.py` — package root with version
- `src/policyfoundry/exceptions.py` — 14-class exception hierarchy
- `src/policyfoundry/config/__init__.py` — config package re-exports
- `src/policyfoundry/config/defaults.py` — default configuration constants
- `src/policyfoundry/config/models.py` — Pydantic config models
- `src/policyfoundry/config/validation.py` — config validation logic
- `src/policyfoundry/config/loader.py` — `load_config()` entry point
