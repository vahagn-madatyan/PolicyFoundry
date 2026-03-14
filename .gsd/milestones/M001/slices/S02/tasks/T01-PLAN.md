# T01: 02-configuration-system 01

**Slice:** S02 — **Milestone:** M001

## Description

Create the core configuration system: Pydantic Settings models with YAML file loading and environment variable overrides, following TDD.

Purpose: This is the foundation of CONF-01 and CONF-02 -- users need a working config system that reads YAML, merges env vars, and validates values before any downstream phase can use configuration.

Output: Config models (models.py), config loader (loader.py), test fixtures (conftest.py), and passing tests for model validation and loader behavior.

## Must-Haves

- [ ] "PolicyFoundryConfig loads with sensible defaults when no config file exists"
- [ ] "YAML config file values are read and applied to the config object"
- [ ] "Environment variables override YAML values using POLICYFOUNDRY_ prefix and __ nesting"
- [ ] "Merge order is honored: global YAML < local YAML < env vars < init kwargs"
- [ ] "LLM provider, model, temperature, max_tokens, base_url, api_key, timeout are configurable"
- [ ] "Log source paths and S3 settings are configurable"
- [ ] "Security group IDs are configurable via YAML list or comma-separated env var"
- [ ] "Invalid config values raise ConfigValidationError with field name and expected format"

## Files

- `pyproject.toml`
- `src/policyfoundry/config/__init__.py`
- `src/policyfoundry/config/models.py`
- `src/policyfoundry/config/loader.py`
- `tests/test_config/__init__.py`
- `tests/test_config/conftest.py`
- `tests/test_config/test_models.py`
- `tests/test_config/test_loader.py`
