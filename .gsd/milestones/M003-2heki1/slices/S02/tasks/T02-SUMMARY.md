---
id: T02
parent: S02
milestone: M003-2heki1
provides:
  - Visible console warnings on render failures in rich_output.py (4 blocks)
  - Visible console warnings on render failures in excel_rich_output.py (4 blocks)
  - Tests proving console warning appears and graceful degradation holds
key_files:
  - src/policyfoundry/output/rich_output.py
  - src/policyfoundry/output/excel_rich_output.py
  - tests/test_output/test_rich_output.py
  - tests/test_output/test_excel_output.py
key_decisions:
  - Used Rich markup `[yellow]⚠ Failed to render {section}[/yellow]` for console warnings — matches project's existing Rich styling patterns
patterns_established:
  - Console warning pattern: `console.print("[yellow]⚠ Failed to render {section}[/yellow]")` after `logger.warning` in except blocks
observability_surfaces:
  - Console output: `⚠ Failed to render {section}` printed to Rich console on render failure
  - Logger: existing `logger.warning` with exc_info preserved alongside new console output
duration: 10m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Add console warnings on render failures and run full regression

**Added `[yellow]⚠ Failed to render {section}[/yellow]` Rich console output to all 8 except blocks across both output renderers, with tests proving warnings appear and graceful degradation holds.**

## What Happened

All 8 bare `except Exception` blocks in `rich_output.py` (4 blocks) and `excel_rich_output.py` (4 blocks) previously only logged via `logger.warning` — the user saw no indication that a section failed. Added `console.print(f"[yellow]⚠ Failed to render {section_name}[/yellow]")` after each existing `logger.warning` call. Section names: "traffic analysis", "security assessment", "proposals", "decisions".

Both files already had `Console` imported and a `console` object in scope within each except block, so no import changes were needed.

Added 4 tests per module (8 total) — each injects malformed data for one section (e.g. `"not-a-valid-analysis"` string instead of a dict), captures console output via `Console(file=StringIO())`, and asserts the warning text appears plus other sections still render (graceful degradation).

## Verification

- `pytest tests/test_output/test_rich_output.py tests/test_output/test_excel_output.py -v` — 28 passed (including 8 new render failure warning tests)
- `pytest tests/test_export/test_xlsx_export.py tests/test_export/test_export_models.py tests/test_adapters/test_registry.py -v` — 20 passed (T01 slice verification)
- `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — **647 passed, 0 failed**

All slice-level verification checks pass.

## Diagnostics

- Run the pipeline with malformed stage data and observe console output for `⚠` warnings
- `grep -r "⚠ Failed to render"` in source to find all 8 warning sites
- Tests inject specific bad data patterns: string where dict expected (`"not-a-valid-analysis"`), or dicts missing required fields (`{"bad": "proposal_data"}`)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/output/rich_output.py` — added console warning in 4 except blocks
- `src/policyfoundry/output/excel_rich_output.py` — added console warning in 4 except blocks
- `tests/test_output/test_rich_output.py` — added TestFormatRichRenderFailureWarnings (4 tests)
- `tests/test_output/test_excel_output.py` — added TestFormatExcelRichRenderFailureWarnings (4 tests)
