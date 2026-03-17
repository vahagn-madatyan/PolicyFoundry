# S01: Pipeline Correctness & Observability

**Goal:** Pipeline errors report the correct stage that failed; token usage shows per-stage breakdown; LLM prompts reference actual field names; rejected proposals and stage failures are logged.
**Demo:** Run the pipeline with a mock LLM failure at the "generate" stage → error message says `stage: "generate"` (not `"starting"`). Token usage output shows `analyze`, `assess`, `generate`, `decide` labels (not `"unknown"`). Generate prompt text references `dst_ip`/`src_ip` (not `counterpart_ip`). Rejected proposals emit a warning log with proposal_id and reason.

## Must-Haves

- All 8 LLM `complete()` calls pass `stage=` parameter matching their pipeline stage name
- Both runners' error handlers extract the actual failed stage from the exception chain, not from `initial_state`
- Generate prompt describes `dst_ip`/`src_ip` field names (not `counterpart_ip`)
- Rejected proposals in both validate stages are logged with context
- All 8 stage functions wrap their body in `try/except` that raises `PipelineError` with stage name in details

## Proof Level

- This slice proves: contract
- Real runtime required: no
- Human/UAT required: no

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — all pipeline tests pass including new targeted tests
- `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — full suite regression (605+ tests, zero failures)
- New tests verify: (a) `stage=` kwarg on all 8 `complete()` calls, (b) runner error handler reports correct stage, (c) prompt contains `dst_ip`/`src_ip` not `counterpart_ip`, (d) `logger.warning` called on rejected proposals, (e) stage functions wrap exceptions in `PipelineError` with stage name

## Observability / Diagnostics

- Runtime signals: `PipelineError.details["stage"]` now carries the actual failed stage; token usage breakdown shows named stages; `logger.warning` on rejected proposals with proposal_id
- Inspection surfaces: Token usage CLI output; `PipelineError` exception details dict
- Failure visibility: Stage name in error messages; rejected proposal IDs in warning logs
- Redaction constraints: none

## Tasks

- [x] **T01: Add stage identity to all LLM calls and fix runner error handlers** `est:45m`
  - Why: Without `stage=`, all token usage shows as "unknown" (R404). Without the runner fix, all errors report stage "starting" (R403). These are the two highest-value fixes and share the "stage identity" theme.
  - Files: `src/policyfoundry/pipeline/excel_stages/analyze.py`, `assess.py`, `generate.py`, `decide.py`, `src/policyfoundry/pipeline/stages/analyze.py`, `assess.py`, `generate.py`, `decide.py`, `src/policyfoundry/pipeline/excel_runner.py`, `src/policyfoundry/pipeline/runner.py`, `tests/test_pipeline/test_excel_stages.py`, `tests/test_pipeline/test_stages.py`, `tests/test_pipeline/test_excel_runner.py`, `tests/test_pipeline/test_runner.py`
  - Do: Add `stage="<name>"` kwarg to all 8 `complete()` calls. Fix both runners' error handlers to extract stage from caught exception (`PipelineError.details.get("stage")` if available, else `"unknown"`) instead of reading `initial_state.get("current_stage")`. Add/update tests asserting `stage=` is passed in `call_args` for each stage. Add runner tests that mock `ainvoke` to raise `PipelineError` with stage details and assert the re-raised error contains the correct stage (not `"starting"`).
  - Verify: `python3 -m pytest tests/test_pipeline/ -v`
  - Done when: All 8 `complete()` calls pass `stage=`; both runners extract stage from exception chain; new tests pass

- [x] **T02: Fix generate prompt to reference actual shared_patterns field names** `est:20m`
  - Why: The generate prompt tells the LLM that `shared_patterns` has a `counterpart_ip` key — this key doesn't exist. Actual keys are `dst_ip` (source grouping) and `src_ip` (destination grouping). This causes LLM hallucination (R402).
  - Files: `src/policyfoundry/pipeline/excel_prompts/generate.py`, `tests/test_pipeline/test_excel_stages.py`
  - Do: In `excel_prompts/generate.py` lines 18-22, replace the prompt text that references `counterpart_ip` with accurate description of both `dst_ip` and `src_ip` field variants (both can appear in the same list of subnet groups), plus `service_port` and `protocol`. Add a test that asserts the system prompt string contains `dst_ip` and `src_ip` and does NOT contain `counterpart_ip`.
  - Verify: `python3 -m pytest tests/test_pipeline/ -v`
  - Done when: Prompt text accurately describes `dst_ip`/`src_ip`; no reference to `counterpart_ip` remains; test passes

- [x] **T03: Add validate rejection logging and stage-specific error wrapping** `est:45m`
  - Why: Rejected proposals silently disappear making diagnosis impossible (R405 #9). All 8 stage functions have zero local error handling — exceptions propagate to the runner catch-all without stage context (R405 #7). The main.py docstring may reference "6 stages" but the pipeline has 5 (#14).
  - Files: `src/policyfoundry/pipeline/excel_stages/validate.py`, `src/policyfoundry/pipeline/stages/validate.py`, `src/policyfoundry/pipeline/excel_stages/analyze.py`, `assess.py`, `generate.py`, `decide.py`, `src/policyfoundry/pipeline/stages/analyze.py`, `assess.py`, `generate.py`, `decide.py`, `src/policyfoundry/main.py`, `tests/test_pipeline/test_excel_stages.py`, `tests/test_pipeline/test_stages.py`
  - Do: (1) In both validate stages, add `import logging` / `logger = logging.getLogger(__name__)` and `logger.warning(...)` when a proposal is rejected, including proposal_id and rejection reason. (2) In all 8 stage functions, wrap the function body in `try/except Exception as e` that checks `if isinstance(e, PipelineError): raise` (don't double-wrap) else raises `PipelineError(str(e), details={"stage": "<stage_name>"})` from e. Import `PipelineError` from `exceptions`. (3) Check `main.py` docstring — if it says "6 stages", fix to "5 stages". (4) Add tests: mock a rejected proposal scenario and assert `logger.warning` was called; mock a stage raising a non-PipelineError exception and assert it gets wrapped in `PipelineError` with the correct stage name in details.
  - Verify: `python3 -m pytest tests/test_pipeline/ -v` then `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q`
  - Done when: Rejected proposals logged with context; all 8 stages wrap exceptions in PipelineError with stage name; main.py docstring accurate; all tests pass including full suite regression

## Files Likely Touched

- `src/policyfoundry/pipeline/excel_stages/analyze.py`
- `src/policyfoundry/pipeline/excel_stages/assess.py`
- `src/policyfoundry/pipeline/excel_stages/generate.py`
- `src/policyfoundry/pipeline/excel_stages/decide.py`
- `src/policyfoundry/pipeline/excel_stages/validate.py`
- `src/policyfoundry/pipeline/stages/analyze.py`
- `src/policyfoundry/pipeline/stages/assess.py`
- `src/policyfoundry/pipeline/stages/generate.py`
- `src/policyfoundry/pipeline/stages/decide.py`
- `src/policyfoundry/pipeline/stages/validate.py`
- `src/policyfoundry/pipeline/excel_runner.py`
- `src/policyfoundry/pipeline/runner.py`
- `src/policyfoundry/pipeline/excel_prompts/generate.py`
- `src/policyfoundry/main.py`
- `tests/test_pipeline/test_excel_stages.py`
- `tests/test_pipeline/test_stages.py`
- `tests/test_pipeline/test_excel_runner.py`
- `tests/test_pipeline/test_runner.py`
