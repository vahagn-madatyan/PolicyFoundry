---
estimated_steps: 4
estimated_files: 10
---

# T10: Reconstruct test files — adapters, output

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs adapter and output test files. Adapter tests are the largest test module by total size (126KB of pyc across 5 test files + conftest) — they verify SG translation, rule validation, schema constraints, registry lookup, and the full AWS SG adapter with moto mocks. Output tests verify Rich formatting, JSON serialization, and the TokenUsage/PipelineResult models. The output conftest contains `sample_pipeline_state` fixtures that will be reused by CLI integration tests in T13.

## Steps

1. **Reconstruct adapter test fixtures + tests** — `test_adapters/conftest.py` (adapter test fixtures with mock SG data), `test_schema.py` (39KB — largest test file, validates UniversalRule, NetworkEndpoint D015, PortRange, RiskLevel), `test_validation.py` (30KB — validation error collection per D017), `test_aws_sg_translator.py` (26KB — translate to/from SG rules per D016), `test_aws_sg_adapter.py` (23KB — full adapter with moto), `test_registry.py` (8.6KB — registry lookup + entry_points).

2. **Reconstruct output test fixtures + tests** — `test_output/conftest.py` (CRITICAL: contains `sample_pipeline_state`, `sample_pipeline_state_no_tokens`, `sample_pipeline_state_empty` fixtures used for Rich/JSON testing and reusable for CLI tests), `test_models.py` (24KB — TokenUsage and PipelineResult), `test_rich_output.py` (14KB — Rich table rendering), `test_json_output.py` (26KB — JSON serialization).

3. **Run adapter tests** — `uv run pytest tests/test_adapters/ -x -v`. Fix any reconstruction issues.

4. **Run output tests** — `uv run pytest tests/test_output/ -x -v`. Fix any reconstruction issues. Pay special attention to `sample_pipeline_state` fixture completeness.

## Must-Haves

- [ ] Adapter schema tests cover NetworkEndpoint model_validator (D015)
- [ ] Translator tests verify static method pattern (D016)
- [ ] Validation tests verify collect-all-errors strategy (D017)
- [ ] Output conftest has `sample_pipeline_state`, `sample_pipeline_state_no_tokens`, `sample_pipeline_state_empty` fixtures
- [ ] TokenUsage model tests cover `add_call`, `to_dict`, `__add__`
- [ ] All tests in both modules pass

## Verification

- `uv run pytest tests/test_adapters/ -x -v 2>&1 | tail -5` → all pass
- `uv run pytest tests/test_output/ -x -v 2>&1 | tail -5` → all pass

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: Run individual test files to isolate failures; inspect `sample_pipeline_state` fixture for CLI test reuse
- Failure state exposed: Pytest verbose output

## Inputs

- `tests/test_adapters/__pycache__/*.pyc` (conftest + 5 tests, 3.8–39KB)
- `tests/test_output/__pycache__/*.pyc` (conftest + 3 tests, 6–26KB)
- Reconstructed src from T02–T07 (adapter + output modules)
- `tools/inspect_pyc.py` from T01

## Expected Output

- `tests/test_adapters/conftest.py`, `test_schema.py`, `test_validation.py`, `test_aws_sg_translator.py`, `test_aws_sg_adapter.py`, `test_registry.py`
- `tests/test_output/conftest.py`, `test_models.py`, `test_rich_output.py`, `test_json_output.py`
- Test results: all pass in both modules
