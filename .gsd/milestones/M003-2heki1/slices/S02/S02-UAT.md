# S02: Silent Failure Elimination — UAT

**Milestone:** M003-2heki1
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All fixes are mechanically verifiable through pytest — each silent failure site has a targeted test that injects bad data and asserts the correct error/warning appears. No runtime pipeline execution or human judgment needed.

## Preconditions

- Python 3.13 virtualenv at `.venv/` with project installed in editable mode
- All dependencies installed (`pip install -e ".[dev]"`)
- No running services required

## Smoke Test

Run `pytest tests/test_export/test_xlsx_export.py::TestExportErrors::test_template_no_matching_columns -v` — should pass, confirming the most critical fix (ExportError on empty template match) is working.

## Test Cases

### 1. Template with no matching columns raises ExportError

1. Run `pytest tests/test_export/test_xlsx_export.py::TestExportErrors::test_template_no_matching_columns -v`
2. **Expected:** Test passes — an xlsx template containing only unrecognized column headers triggers `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"` instead of silently producing an empty file.

### 2. Orphaned decisions are logged with context

1. Run `pytest tests/test_export/test_export_models.py::TestOrphanedDecisionLogging::test_orphaned_decision_logs_warning -v`
2. **Expected:** Test passes — when a `RuleDecision` references a `proposal_id` that doesn't exist in the proposals list, `logger.warning` is called with both the `decision_id` and `proposal_id` before the decision is skipped.

### 3. Adapter ImportError is logged with traceback

1. Run `pytest tests/test_adapters/test_registry.py::TestAdapterRegistry::test_get_adapter_logs_import_error -v`
2. **Expected:** Test passes — when the aws_sg adapter module fails to import, `logger.warning` is called with `exc_info=True` so the full traceback is captured in logs.

### 4. Rich output render failures show console warnings

1. Run `pytest tests/test_output/test_rich_output.py::TestFormatRichRenderFailureWarnings -v`
2. **Expected:** 4 tests pass — each injects malformed data for one section (traffic analysis, security assessment, proposals, decisions), captures Rich console output, and asserts `⚠ Failed to render {section}` appears. Other sections still render (graceful degradation).

### 5. Excel Rich output render failures show console warnings

1. Run `pytest tests/test_output/test_excel_output.py::TestFormatExcelRichRenderFailureWarnings -v`
2. **Expected:** 4 tests pass — same pattern as test case 4 but for the Excel pipeline's Rich formatter.

### 6. Full regression passes

1. Run `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q`
2. **Expected:** 647+ tests pass, 0 failures. No regressions from the silent failure fixes.

## Edge Cases

### Template with partial column matches still works

1. Run `pytest tests/test_export/test_xlsx_export.py::TestTemplateExport -v`
2. **Expected:** 2 tests pass — templates with at least some recognized columns still fill correctly (case-insensitive matching). The ExportError only fires when zero columns match.

### Render failure in one section doesn't break others

1. Run `pytest tests/test_output/test_rich_output.py::TestFormatRichRenderFailureWarnings::test_warns_on_analysis_render_failure -v`
2. **Expected:** Test passes and verifies that when traffic analysis rendering fails, the security assessment, proposals, and decisions sections still render normally.

### Adapter registry still works when import succeeds

1. Run `pytest tests/test_adapters/test_registry.py::TestAdapterRegistry::test_get_adapter_found -v`
2. **Expected:** Normal adapter lookup still works — the ImportError logging only triggers on actual import failures, not on successful imports.

## Failure Signals

- Any of the 20 targeted S02 tests failing indicates a regression in silent failure handling
- `grep -r "except Exception" src/policyfoundry/output/` returning blocks without both `logger.warning` and `console.print` indicates a missed warning site
- `grep -n "if not col_mapping" src/policyfoundry/export/change_request.py` returning a bare `return` instead of `raise ExportError` indicates the template fix regressed
- `grep -n "except ImportError" src/policyfoundry/adapters/registry.py` returning a bare `pass` without `logger.warning` indicates the adapter fix regressed

## Requirements Proved By This UAT

- R401 — All four silent failure categories (template export, orphaned decisions, adapter imports, render failures) now have explicit error/warning signals verified by targeted tests

## Not Proven By This UAT

- Runtime behavior under actual pipeline execution with real LLM output — these tests use mocked/injected data
- Console warning visibility in non-TTY deployment modes (Docker, CI) — tested only with Rich Console capturing to StringIO

## Notes for Tester

- The `--ignore` flags on the full regression exclude two test files that require AWS credentials (S3 and real AWS SG adapter). This is the standard test invocation for local development.
- Test count (647) may increase if S03 adds tests before this UAT is run.
