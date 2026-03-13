# S02: Configuration System

**Goal:** Create the core configuration system: Pydantic Settings models with YAML file loading and environment variable overrides, following TDD.
**Demo:** Create the core configuration system: Pydantic Settings models with YAML file loading and environment variable overrides, following TDD.

## Must-Haves


## Tasks

- [x] **T01: 02-configuration-system 01** `est:3min`
  - Create the core configuration system: Pydantic Settings models with YAML file loading and environment variable overrides, following TDD.

Purpose: This is the foundation of CONF-01 and CONF-02 -- users need a working config system that reads YAML, merges env vars, and validates values before any downstream phase can use configuration.

Output: Config models (models.py), config loader (loader.py), test fixtures (conftest.py), and passing tests for model validation and loader behavior.
- [x] **T02: 02-configuration-system 02** `est:4min`
  - Add unknown key detection with "did you mean?" suggestions, config template generation for `policyfoundry init`, and source annotation utilities for `policyfoundry config show`.

Purpose: Completes CONF-01 by adding user-friendly warnings for typos in config files and enabling the init/show CLI commands (wired in Phase 9). Enhances CONF-02 by making config discoverable through the generated template.

Output: validation.py (unknown key detection), defaults.py (template + source annotations), updated loader.py (integrates unknown key warnings), and tests.

## Files Likely Touched

- `pyproject.toml`
- `src/policyfoundry/config/__init__.py`
- `src/policyfoundry/config/models.py`
- `src/policyfoundry/config/loader.py`
- `tests/test_config/__init__.py`
- `tests/test_config/conftest.py`
- `tests/test_config/test_models.py`
- `tests/test_config/test_loader.py`
- `src/policyfoundry/config/validation.py`
- `src/policyfoundry/config/defaults.py`
- `src/policyfoundry/config/__init__.py`
- `tests/test_config/test_validation.py`
