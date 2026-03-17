---
id: S02
parent: M003-2heki1
milestone: M003-2heki1
provides:
  - ExportError on template with no matching columns (error_code TEMPLATE_NO_MATCHING_COLUMNS)
  - Warning log on orphaned decisions with decision_id and proposal_id context
  - Warning log with exc_info on adapter ImportError
  - Visible console warnings on render failures in rich_output.py (4 blocks)
  - Visible console warnings on render failures in excel_rich_output.py (4 blocks)
requires:
  - slice: none
    provides: independent slice
affects:
  - none
key_files:
  - src/policyfoundry/export/change_request.py
  - src/policyfoundry/export/models.py
  - src/policyfoundry/adapters/registry.py
  - src/policyfoundry/output/rich_output.py
  - src/policyfoundry/output/excel_rich_output.py
  - tests/test_export/test_xlsx_export.py
  - tests/test_export/test_export_models.py
  - tests/test_adapters/test_registry.py
  - tests/test_output/test_rich_output.py
  - tests/test_output/test_excel_output.py
key_decisions:
  - Used %-style logger formatting (not f-strings) for orphaned decision warning to avoid string interpolation when logging is disabled
  - Used Rich markup `[yellow]⚠ Failed to render {section}[/yellow]` for console warnings — matches project's existing Rich styling patterns
patterns_established:
  - Module-level logger via logging.getLogger(__name__) in export/models.py and adapters/registry.py
  - Console warning pattern in except blocks: `console.print("[yellow]⚠ Failed to render {section}[/yellow]")` after `logger.warning`
observability_surfaces:
  - Console output: `⚠ Failed to render {section}` printed to Rich console on render failure (8 sites across 2 files)
  - logger.warning "Orphaned decision {id}: proposal {id} not found" in policyfoundry.export.models
  - logger.warning "Failed to import adapter module" with exc_info=True in policyfoundry.adapters.registry
  - ExportError with error_code="TEMPLATE_NO_MATCHING_COLUMNS" propagates through existing error chain
drill_down_paths:
  - .gsd/milestones/M003-2heki1/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-2heki1/slices/S02/tasks/T02-SUMMARY.md
duration: ~18m
verification_result: passed
completed_at: 2026-03-16
---

# S02: Silent Failure Elimination

**Replaced four categories of silent failure with explicit error signals and visible console warnings — template export, orphaned decisions, adapter imports, and render failures.**

## What Happened

Four silent failure sites that produced wrong/missing output without any user-visible indication were fixed in two tasks:

**T01** addressed three one-line silent failures: (1) `_fill_template()` silently returned when a template had no recognized columns — now raises `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"`, propagating through the existing error chain. (2) `flatten_to_entries()` silently skipped decisions referencing missing proposals — now logs a warning with both `decision_id` and `proposal_id` before continuing. (3) `get_adapter()` swallowed `ImportError` with a bare `pass` — now logs a warning with `exc_info=True` so the full traceback is captured.

**T02** addressed the 8 bare `except Exception` blocks across `rich_output.py` (4 blocks) and `excel_rich_output.py` (4 blocks). Each block already had `logger.warning` calls but never told the user anything went wrong. Added `console.print(f"[yellow]⚠ Failed to render {section_name}[/yellow]")` after each existing logger call. Section names: "traffic analysis", "security assessment", "proposals", "decisions". Tests inject malformed data, capture console output, and verify both the warning text and graceful degradation (other sections still render).

## Verification

- `pytest tests/test_export/test_xlsx_export.py tests/test_export/test_export_models.py tests/test_adapters/test_registry.py -v` — 20 passed (T01 fixes)
- `pytest tests/test_output/test_rich_output.py tests/test_output/test_excel_output.py -v` — 28 passed (T02 fixes including 8 new render failure warning tests)
- `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — **647 passed, 0 failed**

## Requirements Advanced

- R401 — All four silent failure categories now have explicit error/warning signals with tests

## Requirements Validated

- R401 — Verified by 20 targeted tests: ExportError on zero matching columns, orphaned decision logging, adapter ImportError logging, and 8 render failure console warning tests. 647 tests pass.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None.

## Known Limitations

- Render failure warnings use Rich console `print` — if the console object is redirected (e.g. in non-TTY contexts), the warning still goes to wherever the console is pointed, which is correct behavior but may not be visible in all deployment modes.

## Follow-ups

- none

## Files Created/Modified

- `src/policyfoundry/export/change_request.py` — `_fill_template()` raises ExportError instead of silent return
- `src/policyfoundry/export/models.py` — Added logger, warning on orphaned decisions in `flatten_to_entries()`
- `src/policyfoundry/adapters/registry.py` — Added logger, warning with exc_info on ImportError in `get_adapter()`
- `src/policyfoundry/output/rich_output.py` — Added console warning in 4 except blocks
- `src/policyfoundry/output/excel_rich_output.py` — Added console warning in 4 except blocks
- `tests/test_export/test_xlsx_export.py` — Added `test_template_no_matching_columns`
- `tests/test_export/test_export_models.py` — New file with `TestOrphanedDecisionLogging`
- `tests/test_adapters/test_registry.py` — Added `test_get_adapter_logs_import_error`
- `tests/test_output/test_rich_output.py` — Added `TestFormatRichRenderFailureWarnings` (4 tests)
- `tests/test_output/test_excel_output.py` — Added `TestFormatExcelRichRenderFailureWarnings` (4 tests)

## Forward Intelligence

### What the next slice should know
- All silent failure sites in the codebase are now addressed. S03 can focus purely on type safety and data integrity without worrying about undiagnosed output issues.
- The console warning pattern (`console.print("[yellow]⚠ ..."`) is established — if S03 adds new exception handlers, use this same pattern for consistency.

### What's fragile
- The render failure tests depend on injecting specific bad data shapes (e.g. string where dict expected). If Pydantic model validation changes to be more permissive, these tests might stop triggering the except blocks.

### Authoritative diagnostics
- `grep -r "⚠ Failed to render" src/` — shows all 8 console warning sites
- `grep -rn "Orphaned decision\|Failed to import adapter\|TEMPLATE_NO_MATCHING_COLUMNS" src/` — shows all 3 logger/error sites
- `pytest tests/test_output/ tests/test_export/ tests/test_adapters/test_registry.py -v` — runs all S02-related tests (48 total)

### What assumptions changed
- Test count grew from 636 (plan estimate) to 647 — the 11 extra tests came from S01 being completed first and adding its own tests to the suite.
