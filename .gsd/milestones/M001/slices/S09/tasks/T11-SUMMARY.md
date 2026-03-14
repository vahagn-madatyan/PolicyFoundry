---
id: T11
parent: S09
milestone: M001
provides:
  - "6 pipeline test files (conftest + 4 test modules) — 69 tests covering all 5 stages, LLMClient, prompts, graph construction"
  - "1 safety test file — 6 tests defining ReadOnlyAdapter/SafetyError interface for T12"
  - "Full test suite verified: 318 tests passing (excluding safety/CLI)"
key_files:
  - tests/test_pipeline/conftest.py
  - tests/test_pipeline/test_stages.py
  - tests/test_pipeline/test_llm.py
  - tests/test_pipeline/test_prompts.py
  - tests/test_pipeline/test_graph.py
  - tests/test_safety/test_readonly_adapter.py
key_decisions:
  - "D037: Added reraise=True to LLMClient @retry decorator — tenacity 9.x wraps exhausted retries in RetryError; test bytecode proves PipelineError expected"
patterns_established:
  - "Pipeline test stages use patch() on query functions with _QUERIES_PATH prefix for DuckDB mock isolation"
  - "Graph integration tests use _make_llm_mock with response_map dict keyed by response_model type for multi-stage mock routing"
  - "Safety tests define the exact ReadOnlyAdapter contract: delegates get_rules/validate/capabilities, blocks apply_rule/apply_rules with SafetyError(error_code='SAFETY_WRITE_BLOCKED')"
observability_surfaces:
  - "Run `uv run pytest tests/test_pipeline/ -v` to see all 69 pipeline test results"
  - "Run `uv run pytest tests/ --ignore=tests/test_safety --ignore=tests/test_cli -q` to see full 318-test suite"
duration: 35min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T11: Reconstruct test files — pipeline, safety — and verify full test suite

**Reconstructed 6 pipeline test files (69 tests) and 1 safety test file (6 tests) from CPython 3.13 bytecode; verified 318-test full suite passes; fixed retry decorator bug (D037).**

## What Happened

Reconstructed all pipeline test files from bytecode:
- **conftest.py** — 16 fixtures (mock LLM config, mock instructor client, mock adapter, pipeline context, sample data for all 5 stages)
- **test_stages.py** — 24 tests across 7 classes: TestAnalyzeStage (4), TestEmptyDataHandling (1), TestBuildPipeline (1), TestRunPipeline (1), TestAssessStage (4), TestGenerateStage (4), TestValidateProposals (5), TestDecideStage (4)
- **test_llm.py** — 26 tests across 8 classes: TestComposeModelName (4), TestHealthCheck (3), TestDefaults (1), TestComplete (4), TestTokenTracking (7), TestValidationRetry (1), TestTransientRetry (3), TestFactory (2)
- **test_prompts.py** — 12 tests across 4 classes: TestAnalyzePrompt (4), TestAssessPrompt (3), TestGeneratePrompt (3), TestDecidePrompt (3)
- **test_graph.py** — 7 tests across 2 classes: TestPipelineExecution (5 integration tests), TestPipelineErrorHandling (2)

Reconstructed safety test file:
- **test_readonly_adapter.py** — 6 tests across 6 classes defining the ReadOnlyAdapter contract: delegates get_rules, validate, capabilities; blocks apply_rule, apply_rules with SafetyError; verifies structured error details

Fixed source bug discovered during verification: LLMClient's `@retry` decorator was missing `reraise=True`, causing tenacity 9.x to wrap exhausted retries in `RetryError` instead of re-raising the original transient exception. This prevented the `except _TRANSIENT_EXCEPTIONS` handler in `complete()` from converting to `PipelineError`. Added `reraise=True` (D037).

## Verification

- `uv run pytest tests/test_pipeline/ -x -v` → **69 passed** (all pipeline tests green)
- `uv run pytest tests/ --ignore=tests/test_safety --ignore=tests/test_cli -x -q` → **318 passed** (full suite minus safety/CLI)
- `uv run pytest tests/test_safety/ --collect-only -q` → ImportError on `policyfoundry.adapters.safety` (expected — module doesn't exist until T12; tests import from exact paths)
- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ tests/test_adapters/ tests/test_output/ tests/test_pipeline/ -x` → **318 passed** (slice verification check 1)

### Slice Verification Status

| Check | Status |
|-------|--------|
| `uv run pytest tests/test_models/ ... tests/test_pipeline/ -x` → all pre-existing tests pass | ✅ 318 passed |
| `uv run pytest tests/test_safety/ -x` → 6 safety tests pass | ❌ Expected — `policyfoundry.adapters.safety` not yet implemented (T12) |
| `uv run pytest tests/test_cli/ -x` → CLI integration tests pass | ❌ Expected — CLI not yet implemented (T12/T13) |
| `uv run policyfoundry --help` → exits 0 | ❌ Expected — CLI not yet implemented (T12) |
| `uv run policyfoundry analyze --help` → shows options | ❌ Expected — CLI not yet implemented (T12) |

## Diagnostics

- Run `uv run pytest tests/test_pipeline/ -v` to see per-test results for all 69 pipeline tests
- Run `uv run pytest tests/test_pipeline/test_llm.py -v` to verify LLM client retry behavior (D037)
- Run `uv run pytest tests/test_pipeline/test_graph.py -v` to verify full pipeline integration
- Safety tests define T12 interface: `from policyfoundry.adapters.safety import ReadOnlyAdapter` + `from policyfoundry.exceptions import SafetyError`

## Deviations

- **D037 (reraise=True fix):** Source code `@retry` decorator was missing `reraise=True`. Test bytecode proves `PipelineError` is expected on retry exhaustion. Added `reraise=True` to `src/policyfoundry/pipeline/llm.py` to make the `except _TRANSIENT_EXCEPTIONS` handler fire correctly with tenacity 9.x.

## Known Issues

None.

## Files Created/Modified

- `tests/test_pipeline/conftest.py` — 16 fixtures for pipeline tests (mock LLM, adapter, sample data)
- `tests/test_pipeline/test_stages.py` — 24 tests for all 5 pipeline stages
- `tests/test_pipeline/test_llm.py` — 26 tests for LLMClient (Instructor integration, health checks, token tracking, retry)
- `tests/test_pipeline/test_prompts.py` — 12 tests for prompt template formatting
- `tests/test_pipeline/test_graph.py` — 7 tests for LangGraph pipeline construction and execution
- `tests/test_safety/test_readonly_adapter.py` — 6 tests defining ReadOnlyAdapter safety wrapper contract
- `src/policyfoundry/pipeline/llm.py` — Added `reraise=True` to `@retry` decorator (D037)
- `.gsd/DECISIONS.md` — Added D037
