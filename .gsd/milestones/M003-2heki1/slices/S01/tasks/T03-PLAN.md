---
estimated_steps: 5
estimated_files: 8
---

# T03: Add validate rejection logging and stage-specific error wrapping

**Slice:** S01 — Pipeline Correctness & Observability
**Milestone:** M003-2heki1

## Description

Two failure-visibility problems remain: (1) both validate stages silently drop rejected proposals with a bare `continue` and no logging, and (2) all 8 pipeline stage functions have zero local error handling — exceptions propagate to the runner catch-all without stage context. Also check if `main.py` docstring incorrectly references "6 stages" (research found this may already be fixed).

## Steps

1. **Add rejection logging to Excel validate stage**: In `src/policyfoundry/pipeline/excel_stages/validate.py` (line ~37), where rejected proposals `continue`, add `import logging` at the top, create `logger = logging.getLogger(__name__)`, and add `logger.warning("Rejected proposal %s: %s", proposal_id, reason)` (use the actual variable names from the code — read the file first to get exact names). The warning should include enough context to diagnose why a proposal was dropped.

2. **Add rejection logging to VPC validate stage**: Same fix in `src/policyfoundry/pipeline/stages/validate.py`. Read the file to find the rejection point and add the same logging pattern.

3. **Add stage-specific error wrapping to all 8 stage functions**: In each stage function (4 Excel + 4 VPC), wrap the function body in:
   ```python
   try:
       # existing body
   except PipelineError:
       raise  # don't double-wrap
   except Exception as e:
       raise PipelineError(str(e), details={"stage": "<stage_name>"}) from e
   ```
   Import `PipelineError` from `policyfoundry.exceptions` in each file. The stage names are: `"analyze"`, `"assess"`, `"generate"`, `"decide"`, `"validate"` (validate stages get wrapping too). Note: T01 already edited these files to add `stage=` — read the current state before editing.

4. **Check and fix main.py docstring**: Read `src/policyfoundry/main.py` and check if any docstring or comment says "6 stages". If found, fix to reflect the actual pipeline stage count (the pipeline has 5 stages: analyze, assess, generate, decide, validate). If the text is already accurate, skip this step.

5. **Add tests**:
   - **Rejection logging test**: In `tests/test_pipeline/test_excel_stages.py`, add a test that runs the validate stage with a mock scenario where a proposal is rejected, then asserts `logger.warning` was called. Use `unittest.mock.patch` on the validate module's logger. Same for VPC validate in `tests/test_pipeline/test_stages.py`.
   - **Error wrapping test**: Add a test for at least one Excel stage and one VPC stage where `complete()` raises a non-`PipelineError` exception (e.g., `RuntimeError("LLM timeout")`), and assert the caught exception is a `PipelineError` with `details["stage"]` matching the stage name.
   - Run full suite regression: `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q`

## Must-Haves

- [ ] Both validate stages log rejected proposals with `logger.warning` including proposal_id and reason
- [ ] All 8 stage functions (+ 2 validate) wrap exceptions in `PipelineError` with stage name
- [ ] `PipelineError` is re-raised without double-wrapping
- [ ] Tests verify rejection logging and error wrapping behavior
- [ ] Full test suite passes (605+ tests, zero regressions)
- [ ] `main.py` docstring is accurate (if it was wrong)

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — all pipeline tests pass
- `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — full suite regression passes
- `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/ | grep -v 'PipelineError'` — all bare catches are now PipelineError-wrapping catches

## Observability Impact

- Signals added: `logger.warning` on rejected proposals with proposal_id and reason; `PipelineError.details["stage"]` on every stage failure
- How a future agent inspects this: grep logs for "Rejected proposal" warnings; inspect `PipelineError.details` dict on any pipeline exception
- Failure state exposed: which proposal was dropped and why; which stage raised an unexpected exception

## Inputs

- All 8 stage files (modified by T01 with `stage=` parameter — read current state)
- Both validate stage files (for rejection logging)
- `src/policyfoundry/exceptions.py` — `PipelineError` class to import
- `tests/test_pipeline/conftest.py` — shared test fixtures

## Expected Output

- 10 stage files modified: all have `try/except` error wrapping; both validate stages have rejection logging
- `src/policyfoundry/main.py` — docstring fixed if needed
- Test files updated with rejection logging and error wrapping tests
- Full test suite passes with zero regressions
