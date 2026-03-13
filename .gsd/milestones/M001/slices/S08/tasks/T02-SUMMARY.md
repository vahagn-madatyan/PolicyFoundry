---
id: T02
parent: S08
milestone: M001
provides:
  - TokenUsage dataclass for accumulating per-call LLM token counts and cost
  - PipelineResult Pydantic model with typed stage outputs from PipelineState dicts
  - LLMClient token tracking via create_with_completion() with get_usage()/reset_usage()
  - PipelineState extended with token_usage dict field
key_files:
  - src/policyfoundry/output/models.py
  - src/policyfoundry/pipeline/llm.py
  - src/policyfoundry/pipeline/state.py
  - tests/test_pipeline/test_llm.py
key_decisions:
  - TokenUsage is a stdlib dataclass (not Pydantic) for lightweight accumulation; PipelineResult uses arbitrary_types_allowed to embed it
  - Usage extraction uses getattr() chains with fallbacks — never crashes on missing/dynamic LiteLLM attributes
  - Missing usage metadata records zeros with a warning log, not silent skip
patterns_established:
  - _mock_raw_response() helper in test_llm.py for consistent LiteLLM response mocking with usage data
  - create_with_completion tuple unpacking pattern in _call_with_retry
  - PipelineResult.from_state() reconstructs typed Pydantic models via model_validate() from state dicts
observability_surfaces:
  - LLMClient.get_usage() returns accumulated TokenUsage at any point during pipeline execution
  - logger.warning when LLM response lacks usage metadata (model=%s, stage=%s)
  - TokenUsage.to_dict() serializes to PipelineState-compatible dict with per_stage breakdown
duration: 20m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T02: Implement token tracking in LLMClient and extend PipelineState

**Created TokenUsage dataclass, PipelineResult model, switched LLMClient to create_with_completion() for token tracking, and extended PipelineState with token_usage field.**

## What Happened

1. Created `src/policyfoundry/output/models.py` with:
   - `TokenUsage` dataclass — accumulates prompt_tokens, completion_tokens, total_tokens, total_cost across calls. Supports `add_call()` for incremental accumulation, `to_dict()` for PipelineState serialization, and `__add__` for combining instances.
   - `PipelineResult` Pydantic model — wraps PipelineState with typed stage outputs (TrafficAnalysis, SecurityAssessment, etc.). `from_state()` classmethod reconstructs Pydantic models from state dicts via `model_validate()`.

2. Updated `src/policyfoundry/output/__init__.py` to export `TokenUsage` and `PipelineResult`.

3. Modified `src/policyfoundry/pipeline/llm.py`:
   - Added `self._usage = TokenUsage()` to `LLMClient.__init__`.
   - Changed `_call_with_retry` from `create()` to `create_with_completion()` — unpacks `(model, raw_response)` tuple, extracts usage from `raw_response.usage` and cost from `raw_response._hidden_params["response_cost"]`.
   - Added `stage` parameter to `complete()` and `_call_with_retry` for labeling per-call usage.
   - Added `get_usage()` and `reset_usage()` methods.
   - Graceful fallback: if raw response lacks `.usage`, logs a warning and records zeros.

4. Extended `src/policyfoundry/pipeline/state.py` with `token_usage: dict` field (TypedDict total=False).

5. Updated `tests/test_pipeline/test_llm.py`:
   - All existing tests updated to mock `create_with_completion` returning `(model, mock_raw)` tuples instead of `create` returning plain models.
   - Added `_mock_raw_response()` and `_mock_raw_response_no_usage()` helpers.
   - Added 4 new tests in `TestTokenTracking`: usage accumulation across calls, missing usage handling, get_usage return type, and reset_usage.

## Verification

- `pytest tests/test_pipeline/test_llm.py -v` — **22 passed** (18 existing updated + 4 new token tracking)
- `pytest tests/test_output/test_models.py -v` — **4 passed** (PipelineResult from_state, serialization, TokenUsage defaults, accumulation)
- `pytest tests/test_pipeline/ -v` — **66 passed** (no regressions across graph, prompts, stages tests)
- `pyright src/policyfoundry/pipeline/llm.py src/policyfoundry/output/models.py src/policyfoundry/pipeline/state.py` — **0 errors**
- `ruff check src/policyfoundry/output/ src/policyfoundry/pipeline/llm.py src/policyfoundry/pipeline/state.py tests/test_pipeline/test_llm.py` — **all checks passed**

### Slice-level verification status (intermediate):
- ✅ `pytest tests/test_pipeline/test_llm.py -v` — all pass
- ✅ `pytest tests/test_output/test_models.py -v` — all pass
- ❌ `pytest tests/test_output/ -v` — 4 pass, 2 errors (rich_output/json_output modules not yet created — T04 scope)
- ❌ `pytest tests/test_safety/ -v` — ImportError (adapters/safety module not yet created — future task)
- ✅ `pyright` strict on new src/ files — clean
- ✅ `ruff check` — no violations

## Diagnostics

- **Token usage inspection:** Call `llm_client.get_usage()` to get accumulated `TokenUsage` at any pipeline point. Use `.to_dict()` for JSON-serializable output.
- **Missing usage warning:** When a raw LLM response lacks `.usage`, the client logs: `"LLM response missing usage metadata; recording zeros (model=%s, stage=%s)"` at WARNING level.
- **PipelineResult reconstruction:** `PipelineResult.from_state(state)` provides typed access to all stage outputs; `model_dump_json(indent=2)` for serialization.

## Deviations

- Updated `tests/test_pipeline/conftest.py` — changed `mock_instructor_client` fixture to set up `create_with_completion` instead of `create` by default. This was necessary since the production code no longer calls `create()`.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/output/models.py` — Created: TokenUsage dataclass + PipelineResult Pydantic model
- `src/policyfoundry/output/__init__.py` — Updated: exports TokenUsage, PipelineResult
- `src/policyfoundry/pipeline/llm.py` — Modified: create_with_completion, token tracking, get_usage/reset_usage
- `src/policyfoundry/pipeline/state.py` — Extended: added token_usage dict field
- `tests/test_pipeline/test_llm.py` — Updated: all mocks to create_with_completion + 4 new token tracking tests
- `tests/test_pipeline/conftest.py` — Updated: mock_instructor_client fixture uses create_with_completion
