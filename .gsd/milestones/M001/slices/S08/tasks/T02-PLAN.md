---
estimated_steps: 5
estimated_files: 5
---

# T02: Implement token tracking in LLMClient and extend PipelineState

**Slice:** S08 — Output And Safety
**Milestone:** M001

## Description

Modify the LLMClient hot path to capture token usage from LLM calls, and create the output models that the formatters will consume. This is the most technically sensitive change — it modifies `_call_with_retry` to use Instructor's `create_with_completion()` instead of `create()`, captures the raw response's usage metadata, and accumulates it across pipeline stages. The public `complete()` API remains unchanged (still returns `T`), but internally the client now tracks prompt_tokens, completion_tokens, total_tokens, and estimated cost per call.

## Steps

1. Create `src/policyfoundry/output/models.py`:
   - `TokenUsage` dataclass with fields: `prompt_tokens: int = 0`, `completion_tokens: int = 0`, `total_tokens: int = 0`, `total_cost: float = 0.0`, `calls: list[dict[str, Any]]` (per-call breakdown).
   - Method `add_call(prompt_tokens, completion_tokens, total_tokens, cost, stage)` to accumulate.
   - Method `to_dict() -> dict[str, Any]` for PipelineState serialization.
   - `PipelineResult` Pydantic model with fields: `run_id: str`, `started_at: str`, `analysis: TrafficAnalysis | None`, `assessment: SecurityAssessment | None`, `proposals: list[PolicyProposal]`, `decisions: list[RuleDecision]`, `token_usage: dict[str, Any]`.
   - Class method `from_state(state: PipelineState) -> PipelineResult` that reconstructs Pydantic models from state dicts via `model_validate()`.
2. Update `src/policyfoundry/output/__init__.py` to export `TokenUsage`, `PipelineResult`.
3. Modify `src/policyfoundry/pipeline/llm.py`:
   - Add `self._usage: TokenUsage` to `__init__`.
   - Change `_call_with_retry` to use `create_with_completion()` — returns `tuple[T, Any]`. Extract `T` for return, capture raw response usage.
   - After successful call, extract `usage = getattr(raw_response, 'usage', None)` and `cost = getattr(getattr(raw_response, '_hidden_params', {}), 'get', lambda k, d: d)('response_cost', 0.0)` (handle dynamic LiteLLM types safely).
   - Call `self._usage.add_call(...)` with extracted data.
   - `complete()` still returns `T` — no public API change. Add `stage: str | None = None` optional parameter for labeling usage.
   - Add `get_usage() -> TokenUsage` method.
   - Add `reset_usage() -> None` for test isolation.
4. Extend `src/policyfoundry/pipeline/state.py`:
   - Add `token_usage: dict` field to PipelineState TypedDict (with `type: ignore[type-arg]` per D003).
5. Update `tests/test_pipeline/test_llm.py`:
   - Fix existing tests: mock must now return `(model_instance, mock_raw_response)` tuple for `create_with_completion`.
   - Add `test_complete_tracks_token_usage` — call complete twice, verify `get_usage()` accumulates.
   - Add `test_complete_handles_missing_usage` — raw response without `.usage` attribute doesn't crash.
   - Add `test_get_usage_returns_token_usage` — verify return type.
   - Add `test_reset_usage` — verify reset clears accumulated data.

## Must-Haves

- [ ] `TokenUsage` dataclass accumulates per-call token counts and cost
- [ ] `PipelineResult` model reconstructs typed stage outputs from PipelineState dicts
- [ ] `LLMClient._call_with_retry` uses `create_with_completion()` and captures raw response usage
- [ ] `LLMClient.complete()` public return type unchanged (still `T`)
- [ ] `LLMClient.get_usage()` returns accumulated TokenUsage
- [ ] PipelineState has optional `token_usage: dict` field
- [ ] All existing LLM tests updated and still pass
- [ ] New token tracking tests pass
- [ ] `pyright src/policyfoundry/pipeline/llm.py src/policyfoundry/output/models.py` clean

## Verification

- `pytest tests/test_pipeline/test_llm.py -v` — all tests pass (existing + new)
- `pytest tests/test_output/test_models.py -v` — model tests pass
- `pyright src/policyfoundry/pipeline/llm.py src/policyfoundry/output/models.py src/policyfoundry/pipeline/state.py` — strict mode clean

## Observability Impact

- Signals added/changed: `LLMClient.get_usage()` surfaces per-call token counts and cost. `PipelineState["token_usage"]` persists across LangGraph checkpoints.
- How a future agent inspects this: Call `llm_client.get_usage().to_dict()` to see accumulated token data at any point during pipeline execution.
- Failure state exposed: If `create_with_completion` returns a response without `.usage`, the client logs a warning-level message and records zeros — no crash, no silent data loss.

## Inputs

- `src/policyfoundry/pipeline/llm.py` — current LLMClient with `create()` call in `_call_with_retry`
- `src/policyfoundry/pipeline/state.py` — current PipelineState TypedDict
- `tests/test_pipeline/test_llm.py` — existing LLM tests that mock `create()`
- `src/policyfoundry/pipeline/schema.py` — TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision for PipelineResult model
- S08-RESEARCH.md — Instructor `create_with_completion` API, LiteLLM response shape

## Expected Output

- `src/policyfoundry/output/models.py` — TokenUsage dataclass + PipelineResult Pydantic model
- `src/policyfoundry/output/__init__.py` — exports TokenUsage, PipelineResult
- `src/policyfoundry/pipeline/llm.py` — modified with token tracking
- `src/policyfoundry/pipeline/state.py` — extended with token_usage field
- `tests/test_pipeline/test_llm.py` — updated existing tests + 4 new token tracking tests
