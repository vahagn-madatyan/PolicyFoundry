# S01: Pipeline Correctness & Observability — UAT

**Milestone:** M003-2heki1
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All fixes are mechanically verifiable via tests and grep. No runtime LLM or live pipeline needed — stage identity, prompt content, and logging behavior are all contract-testable.

## Preconditions

- Python 3.13+ with project dependencies installed (`pip install -e '.[dev]'`)
- Working directory is the project root

## Smoke Test

```bash
python3 -m pytest tests/test_pipeline/ -v --tb=short
```
Expected: 152 tests pass, 0 failures.

## Test Cases

### 1. Token usage reports per-stage breakdown (R404)

1. Run: `python3 -m pytest tests/test_pipeline/test_excel_stages.py::TestExcelAnalyzeStage::test_calls_llm_with_traffic_analysis_model -v`
2. Run: `python3 -m pytest tests/test_pipeline/test_stages.py::TestAnalyzeStage::test_analyze_stage_calls_llm_complete -v`
3. **Expected:** Both pass. The `stage=` kwarg is asserted in `call_args` for all 8 complete() calls.
4. Verify coverage: `rg 'stage=' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/`
5. **Expected:** 8 lines, one per stage function, showing `stage="analyze"`, `stage="assess"`, `stage="generate"`, `stage="decide"` for each pipeline.

### 2. Runner error handler reports correct stage (R403)

1. Run: `python3 -m pytest tests/test_pipeline/test_runner.py -v`
2. Run: `python3 -m pytest tests/test_pipeline/test_excel_runner.py -v`
3. **Expected:** 8 tests pass (4 per runner):
   - PipelineError passes through unchanged
   - Non-PipelineError wraps with stage="unknown"
   - PipelineError cause extracts correct stage name
   - "starting" is never used as stage value

### 3. Generate prompt references correct field names (R402)

1. Run: `python3 -m pytest tests/test_pipeline/test_excel_stages.py::TestExcelGeneratePromptContent -v`
2. **Expected:** 5 tests pass:
   - Prompt contains `dst_ip`
   - Prompt contains `src_ip`
   - Prompt does NOT contain `counterpart_ip`
   - Prompt describes both grouping directions
   - Prompt mentions `service_port` and `protocol`
3. Verify no stale references: `rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/`
4. **Expected:** No output (exit code 1).

### 4. Rejected proposals are logged (R405 — rejection logging)

1. Run: `python3 -m pytest tests/test_pipeline/test_excel_stages.py::TestExcelValidateRejectionLogging -v`
2. Run: `python3 -m pytest tests/test_pipeline/test_stages.py::TestVpcValidateRejectionLogging -v`
3. **Expected:** 7 tests pass:
   - Warning logged on rejected proposal with proposal_id and reason
   - Fallback reason "validation failed" when errors list is empty
   - No warning when all proposals are valid
   - Multiple error reasons joined with semicolons (Excel only)

### 5. Stage functions wrap exceptions with stage identity (R405 — error wrapping)

1. Run: `python3 -m pytest tests/test_pipeline/test_excel_stages.py::TestExcelStageErrorWrapping -v`
2. Run: `python3 -m pytest tests/test_pipeline/test_stages.py::TestVpcStageErrorWrapping -v`
3. **Expected:** 11 tests pass:
   - Each stage wraps RuntimeError in PipelineError with correct details["stage"]
   - PipelineError is NOT double-wrapped (pass-through)
4. Verify coverage: `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/`
5. **Expected:** 10 lines, one per stage function.

### 6. Full suite regression

1. Run: `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q`
2. **Expected:** 636+ tests pass, 0 failures.

## Edge Cases

### PipelineError cause chain depth

1. Run: `python3 -m pytest tests/test_pipeline/test_runner.py::TestRunnerErrorHandler::test_wrapped_pipeline_error_extracts_stage -v`
2. **Expected:** Pass. Runner inspects `exc.__cause__` one level deep. If the PipelineError is the direct cause, stage is extracted correctly.

### Empty validation errors fallback

1. Run: `python3 -m pytest tests/test_pipeline/test_excel_stages.py::TestExcelValidateRejectionLogging::test_logs_fallback_reason_when_no_errors -v`
2. **Expected:** Pass. When `ValidationResult.errors` is empty but `is_valid=False`, the logged reason falls back to "validation failed".

### Stage-level wrapping vs runner catch-all

1. Run: `python3 -m pytest tests/test_pipeline/test_excel_pipeline.py::TestRunExcelPipelineErrorHandling -v`
2. Run: `python3 -m pytest tests/test_pipeline/test_graph.py::TestPipelineErrorHandling -v`
3. **Expected:** Both pass. Stage-level wrapping catches before the runner catch-all. Exceptions from stage functions carry `details["stage"]` directly, not `error_code="PIPELINE_STAGE_FAILED"`.

## Failure Signals

- Any test in `tests/test_pipeline/` failing — indicates a regression in stage identity, prompt content, or error handling
- `rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/` returning results — stale field reference reintroduced
- `rg 'stage=' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` returning fewer than 8 lines — a complete() call is missing stage identity
- `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` returning fewer than 10 lines — a stage function is missing error wrapping

## Requirements Proved By This UAT

- R402 — Test case 3 proves prompt field name accuracy and regression prevention
- R403 — Test case 2 proves runner error handlers report correct stage from exception cause
- R404 — Test case 1 proves all 8 complete() calls pass stage= parameter
- R405 — Test cases 4 and 5 prove rejection logging and stage-specific error wrapping

## Not Proven By This UAT

- Runtime token usage CLI output appearance (would require live LLM call)
- Runtime rejected proposal log messages in actual pipeline execution (tested via mock only)
- Whether the fixed generate prompt improves LLM output quality (requires live inference comparison)

## Notes for Tester

- Tests in `test_aws_sg_adapter.py` and `test_ingestion/test_s3.py` are excluded from full regression because they require AWS credentials or moto setup. This is consistent with all prior milestones.
- The 3 updated pre-existing tests (test_excel_pipeline, test_graph, test_stages) reflect intentional behavior change: stage-level wrapping now catches before runner catch-all. This is expected per D064.
