---
id: T01
parent: S01
milestone: M003-2heki1
provides:
  - stage= parameter on all 8 LLM complete() calls for per-stage token tracking
  - runner error handlers that extract stage from exception cause, not initial_state
key_files:
  - src/policyfoundry/pipeline/excel_stages/analyze.py
  - src/policyfoundry/pipeline/excel_stages/assess.py
  - src/policyfoundry/pipeline/excel_stages/generate.py
  - src/policyfoundry/pipeline/excel_stages/decide.py
  - src/policyfoundry/pipeline/stages/analyze.py
  - src/policyfoundry/pipeline/stages/assess.py
  - src/policyfoundry/pipeline/stages/generate.py
  - src/policyfoundry/pipeline/stages/decide.py
  - src/policyfoundry/pipeline/excel_runner.py
  - src/policyfoundry/pipeline/runner.py
  - tests/test_pipeline/test_runner.py
  - tests/test_pipeline/test_excel_runner.py
key_decisions:
  - Runner error handlers check exc.__cause__ for PipelineError with stage details, falling back to "unknown" — never reads initial_state
patterns_established:
  - Every complete() call passes stage= kwarg matching the function's stage name
  - Runner error handlers extract stage from exception cause chain, not from mutable state
observability_surfaces:
  - TokenUsage per-stage breakdown via stage= parameter (analyze, assess, generate, decide)
  - PipelineError.details["stage"] carries actual failed stage in error messages
duration: ~12 minutes
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add stage identity to all LLM calls and fix runner error handlers

**Added `stage=` to all 8 pipeline `complete()` calls and fixed both runners to extract stage from exception cause instead of initial state.**

## What Happened

All 8 `complete()` calls across both pipelines (Excel: analyze, assess, generate, decide; VPC: same four) were missing the `stage=` parameter, causing all token usage to report as `"unknown"`. Added `stage="analyze"`, `stage="assess"`, `stage="generate"`, `stage="decide"` to each respective call.

Both runners (`excel_runner.py` and `runner.py`) had error handlers reading `initial_state.get("current_stage", "unknown")` which was always `"starting"`. Changed both to inspect `exc.__cause__` — if it's a `PipelineError` with `details.get("stage")`, use that; otherwise fall back to `"unknown"`.

Created two new test files (`test_runner.py`, `test_excel_runner.py`) with 4 tests each covering: PipelineError passthrough, unknown stage for bare exceptions, stage extraction from wrapped PipelineError cause, and explicit verification that `"starting"` is never used.

Added `stage=` kwarg assertions to existing tests in `test_excel_stages.py` (4 assertions: analyze, assess, generate, decide) and `test_stages.py` (4 assertions: same four stages).

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — 129 tests pass (was ~121 before, +8 new)
- `rg 'stage=' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — all 8 calls have `stage=`
- `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — 613 passed, 0 failures (full regression)

### Slice verification status (T01 is first of 5 tasks):
- ✅ `python3 -m pytest tests/test_pipeline/ -v` — all 129 pass
- ✅ Full suite regression — 613 passed, 0 failures
- ✅ New tests verify stage= kwarg on all 8 complete() calls
- ✅ New tests verify runner error handler reports correct stage from exception
- ⬜ Prompt contains dst_ip/src_ip not counterpart_ip (T02 scope)
- ⬜ logger.warning on rejected proposals (T03 scope)
- ⬜ Stage functions wrap exceptions in PipelineError with stage name (T04 scope)

## Diagnostics

- Grep `stage=` in `src/policyfoundry/pipeline/excel_stages/` and `src/policyfoundry/pipeline/stages/` to verify all calls tagged
- Run `python3 -m pytest tests/test_pipeline/test_runner.py tests/test_pipeline/test_excel_runner.py -v` for runner error handler tests
- At runtime: `PipelineError.details["stage"]` in exceptions carries actual stage; token usage CLI shows named stages instead of "unknown"

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_stages/analyze.py` — added `stage="analyze"` to complete() call
- `src/policyfoundry/pipeline/excel_stages/assess.py` — added `stage="assess"` to complete() call
- `src/policyfoundry/pipeline/excel_stages/generate.py` — added `stage="generate"` to complete() call
- `src/policyfoundry/pipeline/excel_stages/decide.py` — added `stage="decide"` to complete() call
- `src/policyfoundry/pipeline/stages/analyze.py` — added `stage="analyze"` to complete() call
- `src/policyfoundry/pipeline/stages/assess.py` — added `stage="assess"` to complete() call
- `src/policyfoundry/pipeline/stages/generate.py` — added `stage="generate"` to complete() call
- `src/policyfoundry/pipeline/stages/decide.py` — added `stage="decide"` to complete() call
- `src/policyfoundry/pipeline/excel_runner.py` — error handler extracts stage from exc.__cause__ instead of initial_state
- `src/policyfoundry/pipeline/runner.py` — error handler extracts stage from exc.__cause__ instead of initial_state
- `tests/test_pipeline/test_runner.py` — created: 4 tests for VPC runner error handler
- `tests/test_pipeline/test_excel_runner.py` — created: 4 tests for Excel runner error handler
- `tests/test_pipeline/test_excel_stages.py` — added stage= assertions to analyze, assess, generate, decide tests
- `tests/test_pipeline/test_stages.py` — added stage= assertions to analyze, assess, generate, decide tests
- `.gsd/milestones/M003-2heki1/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
