---
id: S04
parent: M002
milestone: M002
provides:
  - export_xlsx(state, output_path, template_path=None) -> Path — Excel change request form with default or custom template
  - export_pdf(state, output_path) -> Path — PDF change request document with metadata and styled table
  - ChangeRequestEntry model and flatten_to_entries() for pipeline-state-to-export conversion
  - ExportError exception with error_code (XLSX_EXPORT_FAILED, PDF_EXPORT_FAILED, TEMPLATE_LOAD_FAILED)
requires:
  - slice: S03
    provides: ExcelPipelineState, ExcelPipelineResult.from_state(), PolicyProposal, RuleDecision, UniversalRule, NetworkEndpoint, PortRange
affects:
  - S05
key_files:
  - src/policyfoundry/export/__init__.py
  - src/policyfoundry/export/models.py
  - src/policyfoundry/export/change_request.py
  - src/policyfoundry/exceptions.py
  - tests/test_export/conftest.py
  - tests/test_export/test_models.py
  - tests/test_export/test_xlsx_export.py
  - tests/test_export/test_pdf_export.py
key_decisions:
  - D051 — flatten_to_entries excludes SKIP decisions (only actionable rules in exports)
  - D052 — Custom template column matching via case-insensitive header scan with synonym dict
  - D053 — fpdf2 for PDF generation (pure Python, no system lib deps, built-in table API)
patterns_established:
  - export/ package with models.py for flattening logic and change_request.py for file generation
  - format_endpoints() / format_port_range() as reusable display helpers for NetworkEndpoint and PortRange
  - ExportError with error_code enum and details dict carrying context (output_path, template_path, rule_count)
  - _extract_pdf_text() test helper decompresses fpdf2 FlateDecode streams for content assertions
observability_surfaces:
  - ExportError with error_code (XLSX_EXPORT_FAILED, PDF_EXPORT_FAILED, TEMPLATE_LOAD_FAILED) and details dict
  - ExportError.__cause__ preserves original exception for chained tracebacks
drill_down_paths:
  - .gsd/milestones/M002/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S04/tasks/T02-SUMMARY.md
duration: 40m
verification_result: passed
completed_at: 2026-03-15
---

# S04: Change Request Form Export

**Export package producing filled Excel and PDF change request forms from pipeline state, with custom template support for xlsx.**

## What Happened

T01 created the export/ package foundation: `ChangeRequestEntry` Pydantic model with `flatten_to_entries()` that pairs proposals with decisions by proposal_id, filters SKIP actions, and flattens NetworkEndpoint lists and PortRange to display strings. `export_xlsx()` supports two modes — default builds a styled workbook (metadata header rows 1-5, bold white-on-blue header row, proportional column widths), and template mode loads a user-provided xlsx, scans row 1 for case-insensitive column matches via COLUMN_MAP, and fills data below. Added fpdf2 dep to pyproject.toml and ExportError to the exception hierarchy.

T02 added `export_pdf()` using fpdf2's table() context manager — metadata header on page 1 (title, date, run_id, source type, rule count), styled FontFace heading row, proportional column widths tuned to prevent word-wrap on short values like "CREATE". Built-in Helvetica only, no TTF embedding. Empty proposals produce a valid PDF with metadata and italic "No rules proposed." message.

## Verification

- `pytest tests/test_export/test_models.py -v` — 13 passed (format_endpoints 6 cases, format_port_range 3, flatten_to_entries 4)
- `pytest tests/test_export/test_xlsx_export.py -v` — 11 passed (default 5, template 2, empty 2, errors 2)
- `pytest tests/test_export/test_pdf_export.py -v` — 16 passed (structure 3, metadata 4, data rows 3, empty 3, errors 3)
- `npx pyright src/policyfoundry/export/` — 0 errors, 0 warnings
- `pytest tests/ -x -q` — 586 passed (excludes 2 pre-existing moto import failures unrelated to this slice)

## Requirements Advanced

- R109 — xlsx export fully implemented and tested
- R110 — PDF export fully implemented and tested
- R111 — Custom template fill implemented and tested

## Requirements Validated

- R109 — 11 tests prove export_xlsx produces valid .xlsx with correct metadata, headers, data rows, custom template fill, empty proposals
- R110 — 16 tests prove export_pdf produces valid PDF with metadata, styled table, data rows, empty proposals, error handling
- R111 — 2 template tests prove case-insensitive column matching and data insertion into user-provided templates

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- PDF column width proportions tuned during T02: initial even distribution caused "CREATE"/"UPDATE" to word-wrap. Adjusted action column weight (8→10) and justification (30→26).
- PDF test approach: raw byte search doesn't work with fpdf2's FlateDecode compression. Added zlib decompression helper for content assertions.

## Known Limitations

- Custom template support assumes single-row headers in row 1. Templates with merged cells or multi-row headers are not supported (documented via ExportError).
- PDF uses built-in Helvetica only — no Unicode glyph support for CJK or other non-Latin scripts.
- Visual quality of PDF not yet human-verified (deferred to S05 UAT).

## Follow-ups

- S05 wires `--export xlsx|pdf` and `--template` CLI flags to export functions.

## Files Created/Modified

- `pyproject.toml` — added fpdf2>=2.8 dependency
- `src/policyfoundry/exceptions.py` — added ExportError(PolicyFoundryError)
- `src/policyfoundry/export/__init__.py` — package init with public API re-exports
- `src/policyfoundry/export/models.py` — ChangeRequestEntry, format_endpoints, format_port_range, flatten_to_entries
- `src/policyfoundry/export/change_request.py` — export_xlsx() and export_pdf() implementations
- `tests/test_export/__init__.py` — package init
- `tests/test_export/conftest.py` — shared fixtures (sample_excel_state, sample_excel_state_empty)
- `tests/test_export/test_models.py` — 13 tests for models and flattening
- `tests/test_export/test_xlsx_export.py` — 11 tests for xlsx export
- `tests/test_export/test_pdf_export.py` — 16 tests for PDF export

## Forward Intelligence

### What the next slice should know
- `export_xlsx()` and `export_pdf()` both take `ExcelPipelineState` (TypedDict) and a `Path` for output. The template_path kwarg is xlsx-only.
- `flatten_to_entries()` uses `ExcelPipelineResult.from_state()` for typed reconstruction — the state dict must have the expected keys from run_excel_pipeline().
- Import from `policyfoundry.export`: `export_xlsx`, `export_pdf`, `ChangeRequestEntry`, `flatten_to_entries`.

### What's fragile
- Custom template column matching is strict on row 1 headers — templates with different header locations will fail silently (no data inserted, no error).

### Authoritative diagnostics
- `ExportError.error_code` + `ExportError.details` dict gives immediate context on any export failure — check output_path, template_path, and rule_count.

### What assumptions changed
- None — slice executed cleanly per plan.
