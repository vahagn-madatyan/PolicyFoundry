---
id: T08
parent: S09
milestone: M001
provides:
  - Root conftest with valid_flow_log_data and valid_universal_rule_data fixtures
  - 11 model test functions across 4 files (NormalizedFlowLog, UniversalRule, PipelineState, pipeline schema)
  - 29 config test functions across 3 files + conftest (loader, models, validation)
  - 10 exception test functions covering hierarchy, error_code, details, str, catch-by-parent
  - 10 test package __init__.py files for pytest discovery
key_files:
  - tests/conftest.py
  - tests/test_models/test_flow_log.py
  - tests/test_models/test_universal_rule.py
  - tests/test_models/test_pipeline_state.py
  - tests/test_models/test_pipeline_schema.py
  - tests/test_config/conftest.py
  - tests/test_config/test_loader.py
  - tests/test_config/test_models.py
  - tests/test_config/test_validation.py
  - tests/test_exceptions/test_exceptions.py
key_decisions:
  - D035: Fixed TrafficAnalysis field types — anomalies/bandwidth_outliers are list[dict] not list[str]; unique_sources/unique_destinations need Field(ge=0)
patterns_established:
  - Config test pattern: monkeypatch Path.home and Path.cwd to isolate YAML loading; autouse clean_env fixture strips POLICYFOUNDRY_ env vars
  - Model test pattern: class-based Valid/Invalid grouping with shared fixture from root conftest
observability_surfaces:
  - Run `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -v` to verify reconstruction fidelity for foundational modules
duration: 25min
verification_result: passed
completed_at: 2026-03-11T22:48:00-07:00
blocker_discovered: false
---

# T08: Reconstruct test files — root, models, config, exceptions

**Reconstructed 14 test files from CPython 3.13 bytecode covering domain models, config system, and exception hierarchy — all 75 tests pass; fixed T06 schema error (D035) discovered by test fidelity check.**

## What Happened

Extracted test structure, assertion patterns, and literal constants from 14 .pyc files using `dis`/`marshal` bytecode disassembly. Reconstructed:

1. **Root conftest** (2 fixtures): `valid_flow_log_data` (12-field dict with datetime, IPs, ports, enums) and `valid_universal_rule_data` (9-field dict with nested NetworkEndpoint dicts and PortRange).

2. **Model tests** (4 files, 36 tests): NormalizedFlowLog valid/invalid creation, enum validation, port boundaries, defaults; UniversalRule actions, directions, PortRange boundaries, optional field defaults; PipelineState TypedDict construction and dict-ness; Pipeline schema models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision) with confidence ranges and risk levels.

3. **Config tests** (conftest + 3 files, 29 tests): Loader tests covering default config, global/local YAML loading, env var overrides, nested delimiter, comma-separated list parsing, merge priority order (global < local < env < kwargs), and ConfigValidationError with error_code. Model tests for LLMConfig, SourcesConfig, TargetsConfig, OutputConfig, and root PolicyFoundryConfig defaults/env_prefix/extra. Validation tests for warn_unknown_keys with fuzzy match suggestions, nested unknown keys, and graceful loading continuation.

4. **Exception tests** (1 file, 10 tests): All 9 exception classes importable, hierarchy checks, error_code/details attributes, defaults (None/{}), str() returns message, catch-by-parent, structured ConfigFileNotFound.

5. **10 `__init__.py` files** for all test packages (models, config, exceptions, ingestion, storage, adapters, output, pipeline, safety, root).

During test execution, discovered T06 incorrectly typed `TrafficAnalysis.anomalies` and `bandwidth_outliers` as `list[str]` and omitted `ge=0` on `unique_sources`/`unique_destinations`. The original test bytecode proves dicts were expected (BUILD_CONST_KEY_MAP opcodes) and -1 must be rejected (pytest.raises(ValidationError)). Fixed in `src/policyfoundry/pipeline/schema.py` and recorded as D035.

## Verification

```
uv run pytest tests/test_models/ -x -v → 36 passed
uv run pytest tests/test_config/ -x -v → 29 passed
uv run pytest tests/test_exceptions/ -x -v → 10 passed
uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -x -v → 75 passed
```

### Slice-level verification (partial — T08 is intermediate):
- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -x` → ✅ PASS (75 tests)
- Remaining slice checks (ingestion, storage, adapters, output, pipeline, safety, CLI) → pending T09–T13

## Diagnostics

- Run `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -v` to see per-test results
- If a model test fails, it localizes whether the issue is in the src model (field type/constraint) or the test fixture data
- Config tests use isolated tmp directories and monkeypatched Path.home/cwd — no real filesystem side effects

## Deviations

- Fixed `src/policyfoundry/pipeline/schema.py` to correct 4 field type errors from T06 reconstruction (D035): `anomalies: list[dict]`, `bandwidth_outliers: list[dict]`, `unique_sources: int = Field(ge=0)`, `unique_destinations: int = Field(ge=0)`. This is a src fix, not a test-only change — the tests are faithful to the original bytecode.

## Known Issues

None.

## Files Created/Modified

- `tests/__init__.py` — empty package marker
- `tests/conftest.py` — root fixtures: valid_flow_log_data, valid_universal_rule_data
- `tests/test_models/__init__.py` — empty package marker
- `tests/test_models/test_flow_log.py` — 11 tests for NormalizedFlowLog valid/invalid
- `tests/test_models/test_universal_rule.py` — 9 tests for UniversalRule valid/invalid
- `tests/test_models/test_pipeline_state.py` — 6 tests for PipelineState TypedDict
- `tests/test_models/test_pipeline_schema.py` — 10 tests for pipeline schema models
- `tests/test_config/__init__.py` — empty package marker
- `tests/test_config/conftest.py` — config fixtures: clean_env, tmp_config_dir, sample_yaml_content/dict
- `tests/test_config/test_loader.py` — 10 tests for config loader priority chain
- `tests/test_config/test_models.py` — 12 tests for config Pydantic models
- `tests/test_config/test_validation.py` — 7 tests for unknown key detection + fuzzy matching
- `tests/test_exceptions/__init__.py` — empty package marker
- `tests/test_exceptions/test_exceptions.py` — 10 tests for exception hierarchy
- `tests/test_ingestion/__init__.py` — empty package marker (for future T09)
- `tests/test_storage/__init__.py` — empty package marker (for future T09)
- `tests/test_adapters/__init__.py` — empty package marker (for future T10)
- `tests/test_output/__init__.py` — empty package marker (for future T10)
- `tests/test_pipeline/__init__.py` — empty package marker (for future T11)
- `tests/test_safety/__init__.py` — empty package marker (for future T11)
- `src/policyfoundry/pipeline/schema.py` — fixed 4 field types per D035
- `.gsd/DECISIONS.md` — added D035
