---
estimated_steps: 5
estimated_files: 2
---

# T03: Modify LLMClient to track token usage via create_with_completion

**Slice:** S08 — Output And Safety
**Milestone:** M001

## Description

Switch LLMClient from Instructor's `create()` to `create_with_completion()` to capture the raw LiteLLM ModelResponse with token usage metadata. Accumulate usage across multiple complete() calls and expose via get_usage(). This is the core change for SAFE-02 (token tracking). The modification touches the hot path — _call_with_retry and complete() — so existing tests must remain green while new token tracking tests are added.

## Steps

1. Modify `LLMClient.__init__` in `src/policyfoundry/pipeline/llm.py`:
   - Import `TokenUsage` from `policyfoundry.output.models`
   - Add `self._usage = TokenUsage()` accumulator field
   - Add `get_usage() -> TokenUsage` method that returns current accumulated usage
   - Add `reset_usage() -> None` method that resets accumulator to fresh TokenUsage()

2. Modify `_call_with_retry` to use `create_with_completion`:
   - Change `self._client.chat.completions.create(...)` to `self._client.chat.completions.create_with_completion(...)`
   - Return type changes from `T` to `tuple[T, Any]` (model, raw_response)
   - The tenacity `@retry` decorator still works — it retries the whole function on transient exceptions
   - Type ignore comments may need updating for the new return shape

3. Modify `complete()` to unpack tuple and accumulate usage:
   - Unpack `model, raw_response = await self._call_with_retry(...)`
   - Extract usage: `usage = getattr(raw_response, 'usage', None)`
   - If usage is not None, extract: `prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0`, same for `completion_tokens`, `total_tokens`
   - Extract cost: `cost = 0.0`; try `cost = raw_response._hidden_params.get("response_cost", 0.0) or 0.0` with except for AttributeError
   - Accumulate into `self._usage`: add to prompt_tokens, completion_tokens, total_tokens, cost; append to per_stage list
   - Return `model` (not the tuple)

4. Update existing tests in `tests/test_pipeline/test_llm.py`:
   - All mocks that set `mock_instructor_client.chat.completions.create` must now set `mock_instructor_client.chat.completions.create_with_completion` instead
   - Mock return values change from `model` to `(model, mock_raw_response)` where mock_raw_response has a `.usage` attribute with prompt_tokens/completion_tokens/total_tokens and `._hidden_params` dict
   - Create a helper `_make_mock_response(usage_dict)` to build consistent mock raw responses
   - Verify all existing test classes still pass with updated mocks

5. Add new token tracking tests to `tests/test_pipeline/test_llm.py`:
   - `TestTokenTracking.test_usage_accumulated_across_calls` — two complete() calls, get_usage() returns sum
   - `TestTokenTracking.test_usage_with_none_usage` — raw response has no usage attr, no crash, usage stays at 0
   - `TestTokenTracking.test_cost_extraction_from_hidden_params` — cost accumulated correctly
   - `TestTokenTracking.test_cost_fallback_for_local_model` — _hidden_params missing or cost is None, cost stays 0.0
   - `TestTokenTracking.test_reset_usage` — reset_usage() zeros everything
   - `TestTokenTracking.test_get_usage_returns_copy` — modifying returned TokenUsage doesn't affect internal state
   - Run full test suite to confirm nothing broken

## Must-Haves

- [ ] `_call_with_retry` uses `create_with_completion` (not `create`)
- [ ] `complete()` returns only the Pydantic model T (not the tuple) — external API unchanged
- [ ] Token usage accumulated across multiple complete() calls
- [ ] `get_usage()` returns TokenUsage with correct totals
- [ ] Graceful handling when `response.usage` is None (Ollama edge case)
- [ ] Graceful handling when `_hidden_params` or `response_cost` is absent
- [ ] All existing LLM tests pass (mocks updated for new API)
- [ ] New token tracking tests pass
- [ ] pyright strict passes on llm.py

## Verification

- `pytest tests/test_pipeline/test_llm.py -v` — all tests pass (existing + new)
- `pyright src/policyfoundry/pipeline/llm.py` — 0 errors
- `ruff check src/policyfoundry/pipeline/llm.py tests/test_pipeline/test_llm.py` — clean

## Observability Impact

- Signals added/changed: LLMClient now accumulates TokenUsage per-call; each call appends to per_stage list with tokens and cost. This data flows into PipelineState.token_usage and ultimately into Rich/JSON output.
- How a future agent inspects this: Call `llm_client.get_usage()` at any point to see accumulated token counts and cost
- Failure state exposed: If usage extraction fails silently (None usage), token counts stay at 0 — the output layer shows 0 tokens rather than crashing

## Inputs

- `src/policyfoundry/pipeline/llm.py` (init branch) — current LLMClient with create() call to modify
- `tests/test_pipeline/test_llm.py` (init branch) — existing tests to update and extend
- `src/policyfoundry/output/models.py` (from T02) — TokenUsage model to import and use
- S08-RESEARCH.md — Instructor create_with_completion API details, LiteLLM usage/cost patterns

## Expected Output

- `src/policyfoundry/pipeline/llm.py` — modified with create_with_completion, usage accumulation, get_usage()/reset_usage()
- `tests/test_pipeline/test_llm.py` — modified with updated mocks + new TestTokenTracking class (6+ tests)
