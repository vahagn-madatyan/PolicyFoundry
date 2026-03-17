---
id: T03
parent: S01
milestone: M003-2heki1
provides:
  - logger.warning on rejected proposals with proposal_id and reason in both validate stages
  - PipelineError wrapping with details["stage"] on all 10 stage functions
  - PipelineError pass-through to prevent double-wrapping
key_files:
  - src/policyfoundry/pipeline/excel_stages/validate.py
  - src/policyfoundry/pipeline/stages/validate.py
  - src/policyfoundry/pipeline/excel_stages/analyze.py
  - src/policyfoundry/pipeline/stages/analyze.py
  - tests/test_pipeline/test_excel_stages.py
  - tests/test_pipeline/test_stages.py
key_decisions:
  - Rejection reason is extracted from ValidationResult.errors (list of ValidationIssue), joined with semicolons, with fallback to "validation failed" when errors list is empty
  - Stage-level error wrapping catches before runner-level catch-all, making PIPELINE_STAGE_FAILED error_code unreachable for stage exceptions — updated 3 pre-existing tests accordingly
patterns_established:
  - Every stage function uses try/except PipelineError: raise / except Exception: raise PipelineError(..., details={"stage": name}) from e
  - Validate stages log rejections as logger.warning("Rejected proposal %s: %s", proposal_id, reasons)
observability_surfaces:
  - logger.warning "Rejected proposal {id}: {reasons}" on every rejected proposal in both validate stages
  - PipelineError.details["stage"] on every stage failure, accessible via exception inspection
duration: 15min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Add validate rejection logging and stage-specific error wrapping

**Added rejection logging to both validate stages and PipelineError wrapping to all 10 stage functions.**

## What Happened

Both validate stages (Excel and VPC) had bare `continue` on rejected proposals with no logging. Added `logger.warning` with proposal_id and joined error reasons from `ValidationResult.errors`. All 10 stage functions (5 Excel + 5 VPC) now wrap their bodies in `try/except PipelineError: raise / except Exception: raise PipelineError(str(e), details={"stage": name}) from e`. This means stage-level wrapping catches non-PipelineError exceptions before the runner catch-all, so the exception always carries `details["stage"]`. Three pre-existing tests that asserted `error_code == "PIPELINE_STAGE_FAILED"` were updated because stage-level wrapping now catches first (the exception carries `details["stage"]` instead of the runner's `error_code`). `main.py` docstring was verified accurate (no "6 stages" reference) — no fix needed.

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — 152 passed, 0 failed
- `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — 636 passed, 0 failed
- `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` — all 10 stage files have wrapping catches

## Diagnostics

- Grep logs for `"Rejected proposal"` warnings to see which proposals were dropped and why
- Inspect `PipelineError.details["stage"]` on any pipeline exception to identify which stage failed
- `rg 'except Exception' src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/stages/` confirms all stages have wrapping

## Deviations

- Updated 3 pre-existing tests in `test_excel_pipeline.py`, `test_graph.py`, and `test_stages.py` that expected `error_code == "PIPELINE_STAGE_FAILED"`. Stage-level wrapping now catches before the runner, so the PipelineError carries `details["stage"]` directly instead of being re-wrapped by the runner with an error_code.

## Known Issues

None

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_stages/validate.py` — Added logging import, logger, rejection warning, and PipelineError wrapping
- `src/policyfoundry/pipeline/stages/validate.py` — Same changes for VPC validate
- `src/policyfoundry/pipeline/excel_stages/analyze.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/excel_stages/assess.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/excel_stages/generate.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/excel_stages/decide.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/stages/analyze.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/stages/assess.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/stages/generate.py` — Added PipelineError import and try/except wrapping
- `src/policyfoundry/pipeline/stages/decide.py` — Added PipelineError import and try/except wrapping
- `tests/test_pipeline/test_excel_stages.py` — Added TestExcelValidateRejectionLogging (4 tests) and TestExcelStageErrorWrapping (5 tests)
- `tests/test_pipeline/test_stages.py` — Added TestVpcValidateRejectionLogging (3 tests) and TestVpcStageErrorWrapping (6 tests)
- `tests/test_pipeline/test_excel_pipeline.py` — Updated 1 test for stage-level wrapping behavior
- `tests/test_pipeline/test_graph.py` — Updated 1 test for stage-level wrapping behavior
