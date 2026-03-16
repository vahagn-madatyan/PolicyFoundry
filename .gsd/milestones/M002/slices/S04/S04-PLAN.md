# S04: Change Request Form Export

**Goal:** `export_xlsx()` and `export_pdf()` produce filled change request forms from pipeline state, with custom template support for xlsx.
**Demo:** Unit tests prove xlsx/pdf files are generated with correct headers, rule data rows, and metadata — including custom template fill and empty-proposals edge case.

## Must-Haves

- `ChangeRequestEntry` Pydantic model flattens `PolicyProposal` + `RuleDecision` into export-ready rows (source, dest, port, protocol, direction, action, justification, risk)
- `export_xlsx(state, output_path, template_path=None) -> Path` produces valid Excel with metadata header and rule rows
- `export_xlsx()` with `template_path` fills a user-provided template by matching column headers
- `export_pdf(state, output_path) -> Path` produces valid PDF with metadata header, styled table, and rule rows
- `ExportError(PolicyFoundryError)` for export-specific failures
- Both exporters handle empty proposals/decisions gracefully (metadata only, no data rows)
- `NetworkEndpoint` lists flatten to readable strings: joined CIDRs, "any" for `is_any`, sg-id or tag
- `PortRange` display: single port for equal from/to, range for different, "any" for None

## Proof Level

- This slice proves: contract (export functions produce correct files from typed pipeline state)
- Real runtime required: no (file I/O to tmp dirs in tests)
- Human/UAT required: no (S05 UAT covers visual inspection)

## Verification

- `pytest tests/test_export/test_models.py -v` — ChangeRequestEntry flattening, NetworkEndpoint formatting, PortRange display, empty inputs
- `pytest tests/test_export/test_xlsx_export.py -v` — default template generation, custom template fill, metadata header, data rows, empty proposals
- `pytest tests/test_export/test_pdf_export.py -v` — PDF structure, metadata header, table content, empty proposals
- `npx pyright src/policyfoundry/export/` — 0 errors (D001: strict on src/)
- `pytest tests/ -x -q` — full suite green (baseline 564 → ~590+)

## Observability / Diagnostics

- Runtime signals: `ExportError` with `error_code` (XLSX_EXPORT_FAILED, PDF_EXPORT_FAILED, TEMPLATE_LOAD_FAILED) and `details` dict (output_path, template_path, rule_count)
- Failure visibility: ExportError carries the original exception as `__cause__` for chained tracebacks

## Integration Closure

- Upstream surfaces consumed: `ExcelPipelineState` (S03), `ExcelPipelineResult.from_state()` for typed reconstruction, `PolicyProposal`/`RuleDecision`/`UniversalRule`/`NetworkEndpoint`/`PortRange` models
- New wiring introduced in this slice: none (S05 wires export into CLI)
- What remains before the milestone is truly usable end-to-end: S05 wires `--export xlsx|pdf` and `--template` CLI flags to these functions

## Tasks

- [x] **T01: Export package with ChangeRequestEntry model and xlsx export** `est:45m`
  - Why: Creates the export package, flattening model, ExportError, and xlsx export — delivering R109 (xlsx export) and R111 (custom template support)
  - Files: `src/policyfoundry/export/__init__.py`, `src/policyfoundry/export/models.py`, `src/policyfoundry/export/change_request.py`, `src/policyfoundry/exceptions.py`, `pyproject.toml`, `tests/test_export/__init__.py`, `tests/test_export/conftest.py`, `tests/test_export/test_models.py`, `tests/test_export/test_xlsx_export.py`
  - Do: Add fpdf2 dep to pyproject.toml. Add ExportError to exceptions.py. Create ChangeRequestEntry with `flatten_to_entries(state)` that pairs proposals with decisions by proposal_id, flattens NetworkEndpoint lists and PortRange to display strings. Create export_xlsx() — default path builds workbook programmatically (styled header row, metadata section above data); template_path loads user xlsx, scans row 1 for known column names (case-insensitive), maps fields to columns, inserts data rows below headers. Shared test fixtures in conftest.py extending sample_excel_state pattern.
  - Verify: `pytest tests/test_export/test_models.py tests/test_export/test_xlsx_export.py -v` all pass, `npx pyright src/policyfoundry/export/` 0 errors
  - Done when: export_xlsx produces valid .xlsx readable by openpyxl with correct metadata, headers, and data rows — including custom template fill and empty-proposals case

- [x] **T02: PDF export with fpdf2** `est:30m`
  - Why: Adds PDF change request generation — delivering R110 (pdf export)
  - Files: `src/policyfoundry/export/change_request.py`, `src/policyfoundry/export/__init__.py`, `tests/test_export/test_pdf_export.py`
  - Do: Implement export_pdf() using fpdf2 FPDF class with table() context manager. Metadata header on page 1 only (date, run_id, source, rule count). Styled table with FontFace heading row, auto column widths, automatic page breaks. Built-in fonts only (Helvetica). Handle empty proposals gracefully.
  - Verify: `pytest tests/test_export/test_pdf_export.py -v` all pass, `pytest tests/ -x -q` full suite green
  - Done when: export_pdf produces valid PDF (starts with %PDF, contains metadata and rule data), empty proposals produce metadata-only PDF

## Files Likely Touched

- `src/policyfoundry/export/__init__.py`
- `src/policyfoundry/export/models.py`
- `src/policyfoundry/export/change_request.py`
- `src/policyfoundry/exceptions.py`
- `pyproject.toml`
- `tests/test_export/__init__.py`
- `tests/test_export/conftest.py`
- `tests/test_export/test_models.py`
- `tests/test_export/test_xlsx_export.py`
- `tests/test_export/test_pdf_export.py`
