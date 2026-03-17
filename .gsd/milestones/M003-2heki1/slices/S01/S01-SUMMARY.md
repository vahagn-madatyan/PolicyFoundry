---
id: S01
parent: M003-2heki1
milestone: M003-2heki1
provides:
  - stage= parameter on all 8 LLM complete() calls for per-stage token tracking
  - Runner error handlers extract stage from exception cause chain, not initial_state
  - Generate prompt accurately describes dst_ip/src_ip shared_patterns field names
  - Rejected proposals logged with proposal_id and reason in both validate stages
  - PipelineError wrapping with details["stage"] on all 10 stage functions
  - PipelineError pass-through to prevent double-wrapping
requires: []
affects:
  - S02
  - S03
key_files:
  - src/policyfoundry/pipeline/excel_stages/analyze.py
  - src/policyfoundry/pipeline/excel_stages/assess.py
  - src/policyfoundry/pipeline/excel_stages/generate.py
  - src/policyfoundry/pipeline/excel_stages/decide.py
  - src/policyfoundry/pipeline/excel_stages/validate.py
  - src/policyfoundry/pipeline/stages/analyze.py
  - src/policyfoundry/pipeline/stages/assess.py
  - src/policyfoundry/pipeline/stages/generate.py
  - src/policyfoundry/pipeline/stages/decide.py
  - src/policyfoundry/pipeline/stages/validate.py
  - src/policyfoundry/pipeline/excel_runner.py
  - src/policyfoundry/pipeline/runner.py
  - src/policyfoundry/pipeline/excel_prompts/generate.py
  - tests/test_pipeline/test_excel_stages.py
  - tests/test_pipeline/test_stages.py
  - tests/test_pipeline/test_runner.py
  - tests/test_pipeline/test_excel_runner.py
key_decisions:
  - "D063: Runner error handlers inspect exc.__cause__ for PipelineError with stage details, fallback to 'unknown' — never reads initial_state"
  - "D064: Stage-level error wrapping pattern: try/except PipelineError: raise / except Exception: raise PipelineError(str(e), details={'stage': name}) from e"
  - "Prompt describes both grouping directions explicitly (source-side → dst_ip, destination-side → src_ip) rather than generic 'counterpart'"
  - "Prompt content regression tests import the constant directly — no LLM mock needed"
  - "Rejection reason extracted from ValidationResult.errors joined with semicolons, fallback to 'validation failed'"
patterns_established:
  - Every complete() call passes stage= kwarg matching the function's pipeline stage name
  - Runner error handlers extract stage from exception cause chain, not from mutable state
  - All stage functions use try/except PipelineError: raise / except Exception: raise PipelineError with stage name
  - Validate stages log rejections as logger.warning with proposal_id and reasons
  - Prompt content tests are sync, importing constants directly without LLM mocking
observability_surfaces:
  - "PipelineError.details['stage'] on every stage failure — accessible via exception inspection"
  - "TokenUsage per-stage breakdown via stage= parameter (analyze, assess, generate, decide)"
  - "logger.warning 'Rejected proposal {id}: {reasons}' on every rejected proposal in both validate stages"
  - "rg 'counterpart_ip' returns empty — confirms no stale field references in prompts"
drill_down_paths:
  - .gsd/milestones/M003-2heki1/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-2heki1/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M003-2heki1/slices/S01/tasks/T03-SUMMARY.md
duration: ~35min
verification_result: passed
completed_at: 2026-03-16
---

# S01: Pipeline Correctness & Observability

**Fixed stage identity across all pipeline LLM calls and error handlers, corrected generate prompt field names, and added rejection logging and stage-specific error wrapping to all 10 stage functions.**

## What Happened

Three tasks addressed the five highest-value pipeline correctness issues from the M002 PR review.

**T01 — Stage identity (R403, R404):** All 8 `complete()` calls across both pipelines (4 Excel + 4 VPC stages) were missing the `stage=` parameter, causing token usage to report as "unknown". Added `stage="analyze"`, `stage="assess"`, `stage="generate"`, `stage="decide"` to each. Both runners (`excel_runner.py` and `runner.py`) had error handlers reading `initial_state.get("current_stage")` which always returned `"starting"`. Changed both to inspect `exc.__cause__` — if it's a `PipelineError` with `details.get("stage")`, use that; otherwise fall back to `"unknown"`.

**T02 — Prompt field names (R402):** The generate prompt told the LLM that `shared_patterns` entries contain a `counterpart_ip` key — this key doesn't exist. Replaced with accurate descriptions of both grouping directions: source-side groups contain `dst_ip`, destination-side groups contain `src_ip`. Added 5 regression tests that import the prompt constant directly.

**T03 — Rejection logging and error wrapping (R405):** Both validate stages silently dropped rejected proposals. Added `logger.warning` with `proposal_id` and joined error reasons from `ValidationResult.errors`. All 10 stage functions (5 Excel + 5 VPC) now wrap their bodies in `try/except PipelineError: raise / except Exception: raise PipelineError(str(e), details={"stage": name}) from e`. This means stage-level wrapping catches non-PipelineError exceptions before the runner catch-all, so every exception carries `details["stage"]`. Three pre-existing tests were updated because stage-level wrapping now catches before the runner's error_code assignment.

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — 152 passed, 0 failed
- `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — 636 passed, 0 failed
- `rg 'stage=' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — all 8 complete() calls have stage= kwarg
- `rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/` — returns empty
- `rg 'Rejected proposal' src/policyfoundry/pipeline/*/validate.py` — present in both validate stages
- `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — all 10 stage files have wrapping

## Requirements Advanced

- R402 → validated: Generate prompt now accurately describes dst_ip/src_ip field names with 5 regression tests
- R403 → validated: Both runners extract stage from exception cause chain; 8 runner tests verify correct extraction
- R404 → validated: All 8 complete() calls pass stage= kwarg; 8 test assertions verify in call_args
- R405 → validated: Rejected proposals logged with context (7 tests); all 10 stages wrap exceptions with stage name (11 tests)

## Requirements Validated

- R402 — 5 prompt content regression tests + rg confirms no counterpart_ip references
- R403 — 8 runner error handler tests prove stage extracted from cause, "starting" never used
- R404 — 8 stage= call_args assertions + rg confirms all calls tagged
- R405 — 7 rejection logging tests + 11 error wrapping tests + rg confirms all stages have wrapping

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T03 updated 3 pre-existing tests in `test_excel_pipeline.py`, `test_graph.py`, and `test_stages.py` that expected `error_code == "PIPELINE_STAGE_FAILED"`. Stage-level wrapping now catches before the runner, so PipelineError carries `details["stage"]` directly instead of being re-wrapped with an error_code. This is correct behavior — the tests were updated to match, not worked around.

## Known Limitations

- Stage extraction falls back to `"unknown"` when a non-PipelineError exception has no PipelineError in its `__cause__` chain. This is the correct fallback — all stage functions now wrap, so this path only fires for errors outside stage functions (e.g., graph construction failures).

## Follow-ups

- none

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_stages/analyze.py` — added stage="analyze" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/excel_stages/assess.py` — added stage="assess" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/excel_stages/generate.py` — added stage="generate" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/excel_stages/decide.py` — added stage="decide" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/excel_stages/validate.py` — added rejection logging, PipelineError wrapping
- `src/policyfoundry/pipeline/stages/analyze.py` — added stage="analyze" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/stages/assess.py` — added stage="assess" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/stages/generate.py` — added stage="generate" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/stages/decide.py` — added stage="decide" to complete(), PipelineError wrapping
- `src/policyfoundry/pipeline/stages/validate.py` — added rejection logging, PipelineError wrapping
- `src/policyfoundry/pipeline/excel_runner.py` — error handler extracts stage from exc.__cause__
- `src/policyfoundry/pipeline/runner.py` — error handler extracts stage from exc.__cause__
- `src/policyfoundry/pipeline/excel_prompts/generate.py` — replaced counterpart_ip with dst_ip/src_ip descriptions
- `tests/test_pipeline/test_excel_stages.py` — added 14 tests (stage= assertions, prompt content, rejection logging, error wrapping)
- `tests/test_pipeline/test_stages.py` — added 13 tests (stage= assertions, rejection logging, error wrapping)
- `tests/test_pipeline/test_runner.py` — created: 4 runner error handler tests
- `tests/test_pipeline/test_excel_runner.py` — created: 4 Excel runner error handler tests
- `tests/test_pipeline/test_excel_pipeline.py` — updated 1 test for stage-level wrapping behavior
- `tests/test_pipeline/test_graph.py` — updated 1 test for stage-level wrapping behavior

## Forward Intelligence

### What the next slice should know
- All 10 stage functions now have try/except wrapping — S02's "replace 8 bare except Exception blocks" task should check whether any of the 8 targets overlap with pipeline stages (they probably don't — S02 targets are in output/export/adapter code, not pipeline stages).
- The stage-level wrapping pattern (D064) changed how runner catch-all tests work — three pre-existing tests were updated. S02/S03 should not expect `error_code == "PIPELINE_STAGE_FAILED"` for exceptions originating inside stage functions.

### What's fragile
- The runner error handler's `exc.__cause__` inspection chain — if someone wraps a PipelineError in another exception type before the runner sees it, the stage will show as "unknown". The pattern relies on PipelineError being the direct `__cause__`, not nested deeper.

### Authoritative diagnostics
- `rg 'stage=' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — confirms all complete() calls tagged. If any line is missing, a stage is reporting as "unknown" in token usage.
- `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — confirms all 10 stages have wrapping. Should show exactly 10 lines.

### What assumptions changed
- Original plan assumed runner catch-all would still fire for stage exceptions — stage-level wrapping now catches first, making PIPELINE_STAGE_FAILED error_code unreachable for stage errors. This is better behavior, not a regression.
