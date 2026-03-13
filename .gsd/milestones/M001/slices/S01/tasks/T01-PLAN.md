# T01: 01-project-foundation 01

**Slice:** S01 — **Milestone:** M001

## Description

Bootstrap the PolicyFoundry Python project with uv, create the full src/ layout with all module directories, configure dev tooling (Ruff, Pyright, pre-commit, pytest via Makefile), and implement the NormalizedFlowLog and UniversalRule domain models with validation tests.

Purpose: Every subsequent phase needs a working, importable Python package with tooling guardrails. The ingestion and adapter schemas are the base types that pipeline models depend on.
Output: Installable policyfoundry package, passing lint/typecheck/tests, two domain models with full validation.

## Must-Haves

- [ ] "Running uv run python -c 'import policyfoundry' succeeds with no errors"
- [ ] "NormalizedFlowLog can be instantiated with valid 12-field data"
- [ ] "NormalizedFlowLog rejects invalid data (bad IPs, out-of-range ports, missing required fields)"
- [ ] "UniversalRule can be instantiated with valid vendor-neutral rule data"
- [ ] "UniversalRule rejects invalid data (bad port ranges, missing required fields)"
- [ ] "Project tooling works: make lint, make typecheck, make test all pass"

## Files

- `pyproject.toml`
- `Makefile`
- `.pre-commit-config.yaml`
- `.gitignore`
- `.python-version`
- `src/policyfoundry/__init__.py`
- `src/policyfoundry/__main__.py`
- `src/policyfoundry/py.typed`
- `src/policyfoundry/config/__init__.py`
- `src/policyfoundry/ingestion/__init__.py`
- `src/policyfoundry/ingestion/schema.py`
- `src/policyfoundry/storage/__init__.py`
- `src/policyfoundry/pipeline/__init__.py`
- `src/policyfoundry/pipeline/stages/__init__.py`
- `src/policyfoundry/pipeline/prompts/__init__.py`
- `src/policyfoundry/adapters/__init__.py`
- `src/policyfoundry/adapters/schema.py`
- `src/policyfoundry/output/__init__.py`
- `src/policyfoundry/utils/__init__.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_models/__init__.py`
- `tests/test_models/test_flow_log.py`
- `tests/test_models/test_universal_rule.py`
