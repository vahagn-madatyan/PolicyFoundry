# S01: Pipeline Correctness & Observability — Research

**Date:** 2026-03-16

## Summary

S01 fixes five issues in the pipeline layer: wrong stage in error messages (#4), missing `stage=` on all 8 LLM calls (#6), factually wrong field names in the generate prompt (#3), silent rejection drops in validate (#9), and zero local error handling in pipeline stages (#7). Also fixes the main.py docstring (#14) if the "6 stages" text still exists (not currently found in codebase — may already be fixed).

All fixes are mechanical and localized. The `complete()` method already accepts `stage=` as an optional kwarg defaulting to `"unknown"` — every fix is just adding the parameter at the call site. The error-handler bug in both runners reads `initial_state` (always `"starting"`) instead of the LangGraph result — the fix is to read `current_stage` from the `result` state when available, falling back to `"unknown"`. The prompt fix is a string replacement. Validate logging is adding a `logger.warning()` call. Stage-specific error wrapping is adding `try/except` blocks around each stage body that wrap exceptions in `PipelineError` with the stage name.

## Recommendation

Organize into three tasks by dependency order: (1) fix `stage=` parameter on all 8 `complete()` calls plus both runners' error handlers, (2) fix the generate prompt field names, (3) add validate rejection logging and stage-specific error wrapping. All are independent but grouping the `complete()` and runner fixes together makes sense since they share the "stage identity" theme.

## Implementation Landscape

### Key Files

- `src/policyfoundry/pipeline/llm.py` — `complete()` already has `stage: str = "unknown"` parameter. No changes needed here — just need callers to pass it.
- `src/policyfoundry/pipeline/excel_stages/analyze.py` — line 69: `complete()` call missing `stage="analyze"`
- `src/policyfoundry/pipeline/excel_stages/assess.py` — line 81: missing `stage="assess"`
- `src/policyfoundry/pipeline/excel_stages/generate.py` — line 71: missing `stage="generate"`
- `src/policyfoundry/pipeline/excel_stages/decide.py` — line 68: missing `stage="decide"`
- `src/policyfoundry/pipeline/stages/analyze.py` — line 56: missing `stage="analyze"`
- `src/policyfoundry/pipeline/stages/assess.py` — line 47: missing `stage="assess"`
- `src/policyfoundry/pipeline/stages/generate.py` — line 58: missing `stage="generate"`
- `src/policyfoundry/pipeline/stages/decide.py` — line 57: missing `stage="decide"`
- `src/policyfoundry/pipeline/excel_runner.py` — error handler at line 76 reads `initial_state.get("current_stage")` which is always `"starting"`. Fix: read from `result` if available, or catch the stage from the exception chain.
- `src/policyfoundry/pipeline/runner.py` — same error-handler bug at line 52: reads `initial_state.get("current_stage")`.
- `src/policyfoundry/pipeline/excel_prompts/generate.py` — line 18-22: prompt says `counterpart_ip` but actual `shared_patterns` keys are `dst_ip` (for source grouping) and `src_ip` (for destination grouping), plus `service_port` and `protocol`.
- `src/policyfoundry/pipeline/excel_stages/validate.py` — line 37: rejected proposals silently `continue` with no logging. Need `import logging` and `logger.warning()` with proposal_id and reason.
- `src/policyfoundry/pipeline/excel_stages/*.py` and `stages/*.py` — all stage functions have zero `try/except` — exceptions propagate to the runner's catch-all. Fix: wrap each stage body in `try/except Exception` that raises `PipelineError` with stage name in details.
- `src/policyfoundry/pipeline/stages/validate.py` — VPC validate stage: check if it also silently drops. (Same pattern as excel validate.)

### Existing Test Patterns

- Tests in `tests/test_pipeline/test_excel_stages.py` use `MagicMock` runtime with `mock_llm_client.complete = AsyncMock(return_value=...)`. Tests check `call_args` for temperature but NOT for `stage=`.
- Tests in `tests/test_pipeline/test_stages.py` follow the same pattern.
- `tests/test_pipeline/conftest.py` provides shared fixtures: `mock_llm_client`, `mock_adapter`, `mock_pipeline_context`, sample data objects.
- Test for `stage=` fix: assert `call_args[1]["stage"]` equals the expected stage name in each stage's test.
- Test for runner error handler: create a state, mock `pipeline.ainvoke` to raise, assert the `PipelineError.details["stage"]` is NOT `"starting"`.
- Test for prompt fix: assert the system prompt contains `dst_ip` and `src_ip` but NOT `counterpart_ip`.
- Test for validate logging: mock a rejected proposal, assert `logger.warning` was called with the proposal_id.

### Build Order

1. **Stage parameter + runner error handler** — Fix all 8 `stage=` parameters and both runner error handlers. This is the highest-value fix (makes token usage and error messages useful) and touches the most files. Test immediately.
2. **Generate prompt fix** — Replace `counterpart_ip` with correct field names (`dst_ip`/`src_ip`). Pure string change. Test by asserting prompt content.
3. **Validate rejection logging + stage error wrapping** — Add logging in validate stages, add `try/except PipelineError` wrapping in all stage functions. Test by asserting logger calls and error wrapping behavior.

### Verification Approach

- Run `python3 -m pytest tests/test_pipeline/ -v` after each task to verify no regressions in existing stage tests.
- Run `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` for full suite regression (605 tests).
- New tests should verify: (a) `stage=` kwarg passed to `complete()`, (b) `PipelineError.details["stage"]` is correct in runner error handlers, (c) prompt text contains `dst_ip`/`src_ip` not `counterpart_ip`, (d) `logger.warning` called on rejected proposals.

## Constraints

- The `complete()` signature already has `stage: str = "unknown"` — callers just need to pass it. No API change needed.
- LangGraph `ainvoke()` returns a new state dict — it does NOT mutate `initial_state`. The runner error handler must use a different approach: either wrap the `ainvoke` to capture the last known stage, or parse it from the exception context. Simplest approach: since each stage sets `current_stage` in its return dict, and LangGraph state is accumulated, the `result` variable holds the evolved state. But on exception, `result` is not assigned. Better approach: track `last_known_stage` in the except block by examining the exception's context or simply note that the stage name IS embedded in `PipelineError` raised by the stage-level error wrapper (task 3). Once stages wrap themselves, the runner catch-all is only for truly unexpected errors.
- VPC pipeline validate stage (`src/policyfoundry/pipeline/stages/validate.py`) also silently drops invalid proposals — needs the same logging fix.

## Common Pitfalls

- **Runner error handler race** — If stage-level error wrapping (task 3) is done first, the runner catch-all for non-`PipelineError` exceptions becomes rare. But both fixes are needed: the stage wrapper handles expected failures; the runner catch-all handles unexpected ones (e.g., LangGraph internal errors). The runner fix should extract stage from the chained exception's details if available.
- **Prompt field names aren't just a rename** — The prompt says each `shared_patterns` entry has ONE `counterpart_ip` key, but the actual data uses `dst_ip` for source-side groups and `src_ip` for destination-side groups. The prompt needs to describe BOTH variants since both can appear in the same list of subnet groups.
