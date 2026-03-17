# S04: Change Request Form Export — UAT

**Milestone:** M002
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Export functions produce files to temp dirs — file content verification via openpyxl reads and PDF byte inspection confirms correct output without a running server. Live CLI integration and visual inspection deferred to S05.

## Preconditions

- Python 3.13+ with project dependencies installed (`pip install -e .`)
- Sample pipeline state available via test fixtures in `tests/test_export/conftest.py`

## Smoke Test

Run `pytest tests/test_export/ -v` — 40 tests pass, covering models, xlsx, and PDF export.

## Test Cases

### 1. Default xlsx export produces valid workbook

1. Call `export_xlsx(state, Path("output.xlsx"))` with populated pipeline state
2. Open output with openpyxl
3. **Expected:** Rows 1-5 contain metadata (Generated date, Run ID, Source Type, Total Rules, blank). Row 6 is header row with 8 columns. Data rows start at row 7 with correct field values.

### 2. Custom template xlsx export fills user template

1. Create a template xlsx with headers in row 1 (e.g., "Source", "Destination", "Port")
2. Call `export_xlsx(state, Path("output.xlsx"), template_path=Path("template.xlsx"))`
3. **Expected:** Template headers preserved. Data rows inserted below headers in matching columns. Non-matching columns left empty.

### 3. PDF export produces formatted document

1. Call `export_pdf(state, Path("output.pdf"))` with populated pipeline state
2. Read PDF bytes
3. **Expected:** File starts with `%PDF`. Contains title "Firewall Change Request", run_id, source type, rule count, proposal IDs, action values (CREATE/UPDATE), protocol values.

### 4. Empty proposals produce valid files

1. Call `export_xlsx(state_empty, Path("output.xlsx"))` and `export_pdf(state_empty, Path("output.pdf"))`
2. **Expected:** Both produce valid files with metadata headers but no data rows. PDF contains "No rules proposed." message.

## Edge Cases

### Missing proposal for a decision

1. Provide pipeline state where a decision references a proposal_id not in the proposals list
2. Call `flatten_to_entries(state)`
3. **Expected:** Orphaned decision is silently skipped — no error raised. Other valid entries still produced.

### Invalid output path

1. Call `export_xlsx(state, Path("/nonexistent/dir/output.xlsx"))`
2. **Expected:** `ExportError` raised with `error_code="XLSX_EXPORT_FAILED"` and details containing output_path.

### Invalid template path

1. Call `export_xlsx(state, Path("output.xlsx"), template_path=Path("missing.xlsx"))`
2. **Expected:** `ExportError` raised with `error_code="TEMPLATE_LOAD_FAILED"` and details containing template_path.

## Failure Signals

- `ExportError` raised during export — check `error_code` and `details` dict for context
- xlsx file unreadable by openpyxl (corrupt workbook)
- PDF file doesn't start with `%PDF` magic bytes
- Missing data rows when proposals/decisions exist in pipeline state
- SKIP decisions appearing in export output (should be filtered)

## Requirements Proved By This UAT

- R109 — xlsx export produces valid change request form with metadata and rule data
- R110 — PDF export produces formatted change request document with metadata and styled table
- R111 — Custom template support fills user-provided xlsx by matching column headers

## Not Proven By This UAT

- Visual quality of exported files (PDF typography, xlsx styling) — deferred to S05 UAT for human inspection
- CLI integration (`--export xlsx|pdf`, `--template` flags) — S05 scope
- Export with real LLM-generated pipeline data (this UAT uses fixtures with mock data)

## Notes for Tester

- All 40 test cases are automated in `tests/test_export/`. Run `pytest tests/test_export/ -v` for full coverage.
- PDF content assertions use a zlib decompression helper (`_extract_pdf_text()`) because fpdf2 uses FlateDecode compression — raw byte search won't find text strings.
- The 2 pre-existing moto import failures (`test_aws_sg_adapter.py`, `test_s3.py`) are M001 issues, not related to S04.
