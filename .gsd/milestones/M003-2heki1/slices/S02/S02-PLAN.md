# S02: Silent Failure Elimination

**Goal:** Replace four categories of silent failure with visible diagnostics: template export error on zero matching columns, orphaned decision logging, adapter ImportError logging, and console warnings on render failures.
**Demo:** Template export with unrecognized columns raises `ExportError`; render failures print `[yellow]⚠` warnings to the console; orphaned decisions and adapter import failures appear in logs.

## Must-Haves

- `_fill_template()` raises `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"` when no columns match
- `flatten_to_entries()` logs warning with decision_id and proposal_id before skipping orphaned decisions
- `get_adapter()` logs warning with exc_info before falling through on `ImportError`
- All 8 bare `except Exception` blocks in `rich_output.py` and `excel_rich_output.py` print visible `[yellow]⚠ Failed to render {section}[/yellow]` console warnings alongside existing `logger.warning` calls
- Targeted tests for each fix
- Full test suite passes (636+ tests, zero regressions)

## Verification

- `pytest tests/test_export/test_xlsx_export.py tests/test_export/test_export_models.py tests/test_adapters/test_registry.py -v` — targeted tests for template error, orphaned decisions, adapter ImportError
- `pytest tests/test_output/test_rich_output.py tests/test_output/test_excel_output.py -v` — targeted tests for console warnings on render failures
- `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — full regression, 636+ passed

## Observability / Diagnostics

- Runtime signals: `logger.warning` on orphaned decisions (decision_id, proposal_id), `logger.warning` with exc_info on adapter ImportError, `[yellow]⚠` Rich console output on render failures
- Inspection surfaces: console output during pipeline run shows render warnings; log output shows orphaned decisions and import failures
- Failure visibility: `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"` propagates through existing error handling chain

## Tasks

- [x] **T01: Raise ExportError on empty template match, log orphaned decisions and adapter ImportError** `est:45m`
  - Why: Three independent silent-failure fixes that each touch one source file and one test file — small enough to combine. Covers the template deception (success message on empty output), orphaned decision drops, and swallowed adapter ImportError.
  - Files: `src/policyfoundry/export/change_request.py`, `src/policyfoundry/export/models.py`, `src/policyfoundry/adapters/registry.py`, `tests/test_export/test_xlsx_export.py`, `tests/test_export/test_export_models.py`, `tests/test_adapters/test_registry.py`
  - Do: (1) In `_fill_template()`, replace `if not col_mapping: return` with `raise ExportError("Template contains no recognized columns", error_code="TEMPLATE_NO_MATCHING_COLUMNS")`. (2) In `flatten_to_entries()`, add `logger.warning(f"Orphaned decision {decision.decision_id}: proposal {decision.proposal_id} not found")` before the `continue`. (3) In `get_adapter()`, add `logger.warning("Failed to import adapter module", exc_info=True)` before the `pass` in the `except ImportError` block. (4) Add targeted tests for each: `pytest.raises(ExportError)` on template with unrecognized columns; assert `logger.warning` called with orphaned decision context; assert `logger.warning` called on mocked ImportError.
  - Verify: `pytest tests/test_export/test_xlsx_export.py tests/test_export/test_export_models.py tests/test_adapters/test_registry.py -v`
  - Done when: All three targeted tests pass, no regressions in related test files

- [x] **T02: Add console warnings on render failures and run full regression** `est:45m`
  - Why: The 8 bare `except Exception` blocks in output renderers log errors but never tell the user anything went wrong. Adding Rich console warnings makes failures visible. This is the largest change by file count but is a single repeated pattern. Includes full regression to close the slice.
  - Files: `src/policyfoundry/output/rich_output.py`, `src/policyfoundry/output/excel_rich_output.py`, `tests/test_output/test_rich_output.py`, `tests/test_output/test_excel_output.py`
  - Do: (1) In `rich_output.py`, add `console.print(f"[yellow]⚠ Failed to render {section_name}[/yellow]")` inside each of the 4 `except Exception` blocks (traffic analysis ~L224, security assessment ~L233, proposals ~L243, decisions ~L253), keeping existing `logger.warning` calls. (2) Apply the same pattern to the 4 `except Exception` blocks in `excel_rich_output.py` (~L113, ~L122, ~L132, ~L142). (3) Add tests that inject bad data causing `model_validate()` or section-rendering to fail, then capture console output and assert the `⚠ Failed to render` warning text appears. (4) Run full regression: `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — expect 636+ passed, 0 failed.
  - Verify: `pytest tests/test_output/test_rich_output.py tests/test_output/test_excel_output.py -v` then `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q`
  - Done when: Console warning tests pass for both output modules, full suite passes with 636+ tests and zero failures

## Files Likely Touched

- `src/policyfoundry/export/change_request.py`
- `src/policyfoundry/export/models.py`
- `src/policyfoundry/adapters/registry.py`
- `src/policyfoundry/output/rich_output.py`
- `src/policyfoundry/output/excel_rich_output.py`
- `tests/test_export/test_xlsx_export.py`
- `tests/test_export/test_export_models.py`
- `tests/test_adapters/test_registry.py`
- `tests/test_output/test_rich_output.py`
- `tests/test_output/test_excel_output.py`
