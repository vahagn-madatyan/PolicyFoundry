# S01: Project Foundation

**Goal:** Bootstrap the PolicyFoundry Python project with uv, create the full src/ layout with all module directories, configure dev tooling (Ruff, Pyright, pre-commit, pytest via Makefile), and implement the NormalizedFlowLog and UniversalRule domain models with validation tests.
**Demo:** Bootstrap the PolicyFoundry Python project with uv, create the full src/ layout with all module directories, configure dev tooling (Ruff, Pyright, pre-commit, pytest via Makefile), and implement the NormalizedFlowLog and UniversalRule domain models with validation tests.

## Must-Haves


## Tasks

- [x] **T01: 01-project-foundation 01** `est:5min`
  - Bootstrap the PolicyFoundry Python project with uv, create the full src/ layout with all module directories, configure dev tooling (Ruff, Pyright, pre-commit, pytest via Makefile), and implement the NormalizedFlowLog and UniversalRule domain models with validation tests.

Purpose: Every subsequent phase needs a working, importable Python package with tooling guardrails. The ingestion and adapter schemas are the base types that pipeline models depend on.
Output: Installable policyfoundry package, passing lint/typecheck/tests, two domain models with full validation.
- [x] **T02: 01-project-foundation 02** `est:4min`
  - Implement the pipeline LLM output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision), the PipelineState TypedDict, and the complete exception hierarchy with tests for all three.

Purpose: These are the remaining domain types that every pipeline phase (6, 7, 8) depends on. The exception hierarchy provides structured error handling for all subsequent phases. Completing this plan means Phase 1's foundation is fully in place.
Output: All domain models defined, all exceptions importable, all Phase 1 success criteria met.

## Files Likely Touched

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
- `src/policyfoundry/pipeline/schema.py`
- `src/policyfoundry/pipeline/state.py`
- `src/policyfoundry/exceptions.py`
- `tests/test_models/test_pipeline_schema.py`
- `tests/test_models/test_pipeline_state.py`
- `tests/test_exceptions/__init__.py`
- `tests/test_exceptions/test_exceptions.py`
