---
id: T03
parent: S08
milestone: M001
provides:
  - LLMClient.get_usage() returns deep-copy of TokenUsage (safe external mutation)
  - _extract_cost() helper handles None response_cost without crashing
  - 3 new token tracking tests (cost extraction, cost fallback, copy safety)
key_files:
  - src/policyfoundry/pipeline/llm.py
  - tests/test_pipeline/test_llm.py
key_decisions:
  - get_usage() returns deepcopy to prevent callers from corrupting internal accumulator state
  - Extracted cost logic into standalone _extract_cost() helper for testability and None-safety
patterns_established:
  - _extract_cost(raw_response) pattern for safe cost extraction with None/missing _hidden_params fallback
observability_surfaces:
  - LLMClient.get_usage() returns accumulated TokenUsage with per-call breakdown including cost
  - WARNING log when LLM response lacks .usage attribute (model=%s, stage=%s)
duration: 10min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T03: Modify LLMClient to track token usage via create_with_completion

**Hardened LLMClient token tracking with copy-safe get_usage(), None-safe cost extraction, and 3 new edge-case tests.**

## What Happened

T02 already implemented the core `create_with_completion` switch, token accumulation, `get_usage()`/`reset_usage()` methods, and updated all existing test mocks. T03 focused on the remaining edge cases and test coverage gaps:

1. **Fixed potential crash**: The inline cost extraction `float(hidden_params.get("response_cost", 0.0))` would crash with `TypeError` when `response_cost` exists but is `None` (common with Ollama). Extracted into a standalone `_extract_cost()` helper that explicitly handles `None` values.

2. **Copy-safe `get_usage()`**: Changed from returning `self._usage` directly to `copy.deepcopy(self._usage)`, so external callers can't corrupt the internal accumulator by mutating the returned object.

3. **Added 3 missing tests**:
   - `test_cost_extraction_from_hidden_params` — verifies cost flows correctly from `_hidden_params.response_cost`
   - `test_cost_fallback_for_local_model` — verifies both `None` cost and missing `_hidden_params` produce 0.0
   - `test_get_usage_returns_copy` — verifies mutations to returned TokenUsage don't affect client internals

## Verification

- `pytest tests/test_pipeline/test_llm.py -v` — **25 passed** (22 existing + 3 new)
- `pyright src/policyfoundry/pipeline/llm.py` — **0 errors**
- `ruff check src/policyfoundry/pipeline/llm.py tests/test_pipeline/test_llm.py` — **clean**

### Slice-level verification (partial — T03 is intermediate):
- `pytest tests/test_pipeline/test_llm.py -v` — ✅ all pass
- `pytest tests/test_output/ -v` — ❌ ImportError (output formatters not yet implemented — T04+)
- `pytest tests/test_safety/ -v` — ❌ ImportError (safety adapter not yet implemented — T04+)
- `pyright` on src/ — 0 errors in modified files (4 pre-existing errors in prompts/)
- `ruff check src/ tests/` — 0 errors in modified files (31 pre-existing in other files)

## Diagnostics

- **Token usage inspection:** `llm_client.get_usage()` returns a deep copy of accumulated `TokenUsage` — safe to inspect/serialize without side effects
- **Missing usage warning:** When raw LLM response lacks `.usage`, logs: `"LLM response missing usage metadata; recording zeros (model=%s, stage=%s)"` at WARNING level
- **Cost extraction:** `_extract_cost(raw_response)` returns 0.0 for local Ollama models (where `_hidden_params` is missing or `response_cost` is None)

## Deviations

- T02 already implemented the core `create_with_completion` switch and token accumulation, so T03 was scoped to edge-case hardening and missing test coverage rather than the full implementation described in the plan.
- Cost extraction was refactored into a standalone `_extract_cost()` helper function rather than keeping it inline in `_call_with_retry`, for better None-safety and testability.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/llm.py` — Added `_extract_cost()` helper, `import copy`, changed `get_usage()` to return deepcopy
- `tests/test_pipeline/test_llm.py` — Added 3 new tests in `TestTokenTracking` class (cost extraction, cost fallback, copy safety)
