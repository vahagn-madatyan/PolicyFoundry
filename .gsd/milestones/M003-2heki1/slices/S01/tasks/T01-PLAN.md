---
estimated_steps: 5
estimated_files: 8
---

# T01: Add stage identity to all LLM calls and fix runner error handlers

**Slice:** S01 — Pipeline Correctness & Observability
**Milestone:** M003-2heki1

## Description

Every LLM `complete()` call in the pipeline omits the `stage=` parameter, so all token usage is reported as `"unknown"`. Both pipeline runners (Excel and VPC) read the failed stage from `initial_state.get("current_stage")` which is always `"starting"` — so every error reports the wrong stage.

Fix both problems: add `stage=` to all 8 `complete()` calls, and fix both runners to extract stage from the caught exception instead of initial state.

The `complete()` method in `src/policyfoundry/pipeline/llm.py` already accepts `stage: str = "unknown"` — no API change needed. Each caller just needs to pass the parameter.

## Steps

1. **Read all 8 stage files** to find the exact `complete()` call syntax in each:
   - Excel pipeline: `src/policyfoundry/pipeline/excel_stages/analyze.py` (line ~69), `assess.py` (~81), `generate.py` (~71), `decide.py` (~68)
   - VPC pipeline: `src/policyfoundry/pipeline/stages/analyze.py` (~56), `assess.py` (~47), `generate.py` (~58), `decide.py` (~57)
   - Add `stage="analyze"`, `stage="assess"`, `stage="generate"`, `stage="decide"` to each respective call.

2. **Fix `excel_runner.py` error handler** (line ~76): Currently reads `initial_state.get("current_stage", "unknown")`. Change to: if the caught exception is a `PipelineError` with `details.get("stage")`, use that stage name. Otherwise fall back to `"unknown"`. Do NOT read from `initial_state`.

3. **Fix `runner.py` error handler** (line ~52): Same fix as excel_runner — extract stage from exception details if available, else `"unknown"`.

4. **Add tests for `stage=` parameter**: In `tests/test_pipeline/test_excel_stages.py` and `tests/test_pipeline/test_stages.py`, existing tests call stages and check `mock_llm_client.complete` call_args. Add assertions that `stage=` kwarg is passed with the correct value. Pattern: `assert call_args.kwargs["stage"] == "analyze"` (or however kwargs are accessed in the existing test style — check the test fixtures first).

5. **Add runner error handler tests**: In `tests/test_pipeline/test_excel_runner.py` and `tests/test_pipeline/test_runner.py` (create if they don't exist), test that when `pipeline.ainvoke` raises a `PipelineError` with `details={"stage": "generate"}`, the runner's re-raised error includes `stage: "generate"` (not `"starting"`). Use `conftest.py` fixtures for mock setup.

## Must-Haves

- [ ] All 8 `complete()` calls pass `stage=` with the correct stage name
- [ ] Both runners extract stage from caught exception, not from `initial_state`
- [ ] Tests assert `stage=` kwarg on all 8 `complete()` calls
- [ ] Tests assert runner error handler reports correct stage from exception

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — all tests pass including new stage= assertions
- Grep check: `rg 'complete\(' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — every `complete()` call has `stage=`

## Inputs

- `src/policyfoundry/pipeline/llm.py` — already has `stage: str = "unknown"` parameter on `complete()`. No changes needed to this file.
- `src/policyfoundry/exceptions.py` — `PipelineError` class with `details` dict. Import this in runners if not already imported.
- `tests/test_pipeline/conftest.py` — shared fixtures: `mock_llm_client`, `mock_adapter`, `mock_pipeline_context`

## Observability Impact

- **Token usage breakdown**: `TokenUsage.add_call()` now receives named stages (`analyze`, `assess`, `generate`, `decide`) instead of `"unknown"`. CLI token usage output shows per-stage cost attribution.
- **Error stage identity**: `PipelineError.details["stage"]` in runner error handlers now carries the actual failed stage (extracted from caught exception cause) instead of always `"starting"`. Error messages say `stage: "generate"` when generate fails.
- **Future agent inspection**: Grep `stage=` in stage files to verify all calls are tagged. Run `python3 -m pytest tests/test_pipeline/test_runner.py tests/test_pipeline/test_excel_runner.py -v` to verify error handler behavior. Check `PipelineError.details["stage"]` in exception for correct stage on failures.

## Expected Output

- 8 stage files modified: each `complete()` call now has `stage=` parameter
- 2 runner files modified: error handlers extract stage from exception, not initial state
- 2+ test files updated: new assertions for `stage=` kwargs and runner error handler behavior
