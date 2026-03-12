---
estimated_steps: 5
estimated_files: 10
---

# T08: Reconstruct test files — root, models, config, exceptions

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Begins test file reconstruction with the foundational tests: root conftest (shared fixtures), domain model tests, config tests, and exception tests. These test the modules reconstructed in T02 (exceptions, config) and T04 (adapter schema — since model tests cover UniversalRule). Running these tests is the first real fidelity check for the source reconstruction.

**Note:** File count includes empty `__init__.py` files which are literally zero-content. Meaningful files: root conftest (1), model tests (4), config conftest + tests (4), exception tests (1) = 10 meaningful files.

## Steps

1. **Create all test `__init__.py` files** — Empty files for: `tests/__init__.py`, `tests/test_models/__init__.py`, `tests/test_config/__init__.py`, `tests/test_exceptions/__init__.py`. These are needed for pytest discovery. Also create any remaining test package `__init__.py` files for modules that will be reconstructed in T09–T11 (`test_ingestion`, `test_storage`, `test_adapters`, `test_output`, `test_pipeline`, `test_safety`) to avoid import issues.

2. **Reconstruct `tests/conftest.py`** — Root conftest with shared fixtures used across test modules. Extract fixture names and return types from bytecode (1.7KB pyc — relatively small).

3. **Reconstruct model tests** — `test_models/test_flow_log.py`, `test_universal_rule.py`, `test_pipeline_state.py`, `test_pipeline_schema.py`. These test Pydantic model validation, field defaults, serialization. Extract test function names and assertion patterns from bytecode.

4. **Reconstruct config + exception tests** — `test_config/conftest.py` (config test fixtures), `test_config/test_loader.py`, `test_config/test_models.py`, `test_config/test_validation.py`, `test_exceptions/test_exceptions.py`. Config tests verify YAML loading, env var overrides, validation logic. Exception tests verify the hierarchy, error_code, and details attributes.

5. **Run tests and fix reconstruction issues** — `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -x -v`. Fix any failures caused by reconstruction inaccuracies in either test or src files.

## Must-Haves

- [ ] All test `__init__.py` files exist (10 packages)
- [ ] Root `conftest.py` fixtures are available to all test modules
- [ ] Model tests cover NormalizedFlowLog, UniversalRule, PipelineState, pipeline schema models
- [ ] Config tests cover loader, models, validation with YAML + env var scenarios
- [ ] Exception tests verify hierarchy, error_code, details attributes
- [ ] All tests in these modules pass

## Verification

- `uv run pytest tests/test_models/ -x -v 2>&1 | tail -5` → all pass
- `uv run pytest tests/test_config/ -x -v 2>&1 | tail -5` → all pass
- `uv run pytest tests/test_exceptions/ -x -v 2>&1 | tail -5` → all pass

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: Run `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -v` to see individual test results
- Failure state exposed: Pytest output shows exactly which test failed and why, localizing reconstruction errors

## Inputs

- `tests/__pycache__/conftest.cpython-313-pytest-9.0.2.pyc` (1677 bytes)
- `tests/test_models/__pycache__/*.pyc` (4 test files, 10–27KB)
- `tests/test_config/__pycache__/*.pyc` (conftest + 3 test files, 2.8–29KB)
- `tests/test_exceptions/__pycache__/*.pyc` (1 test file, 21KB)
- Reconstructed src files from T02–T07
- `tools/inspect_pyc.py` from T01

## Expected Output

- `tests/__init__.py`, `tests/conftest.py`
- `tests/test_models/__init__.py`, `test_flow_log.py`, `test_universal_rule.py`, `test_pipeline_state.py`, `test_pipeline_schema.py`
- `tests/test_config/__init__.py`, `conftest.py`, `test_loader.py`, `test_models.py`, `test_validation.py`
- `tests/test_exceptions/__init__.py`, `test_exceptions.py`
- All `__init__.py` files for remaining test packages (test_ingestion, test_storage, test_adapters, test_output, test_pipeline, test_safety)
- Test results: all pass in these 3 modules
