---
estimated_steps: 3
estimated_files: 3
---

# T02: PDF export with fpdf2

**Slice:** S04 — Change Request Form Export
**Milestone:** M002

## Description

Implement `export_pdf()` using fpdf2's table API to produce a professional change request PDF document. Delivers R110 (pdf export). The ChangeRequestEntry model and flattening logic from T01 are consumed directly.

## Steps

1. **Implement export_pdf() in change_request.py.** Create FPDF instance, set auto page break. Page 1 metadata section: title ("Firewall Change Request"), generated date, run_id, source type ("Excel Traffic Analysis"), total rule count — using set_font("Helvetica", "B", 14) for title, normal 10pt for metadata fields. Add a separator line. Then table() context manager with FontFace heading style (bold, dark background, white text), col_widths proportional to content type (wider for justification/source/dest), borders_layout="SINGLE_TOP_LINE". One row per ChangeRequestEntry. Wrap in try/except → ExportError with PDF_EXPORT_FAILED error_code. Handle empty entries: produce PDF with metadata section and "No rules proposed" text.

2. **Update export/__init__.py** to re-export `export_pdf`.

3. **Write tests/test_export/test_pdf_export.py.** Test that export_pdf produces a file starting with `%PDF` bytes. Read the file with fpdf2's output or raw bytes to verify: file size > 0, metadata text present (run_id appears in PDF content), non-empty proposals produce multi-page-capable output. Test empty proposals produce valid PDF with metadata only. Test ExportError on write failure (e.g., directory doesn't exist). Reuse conftest.py fixtures from T01.

## Must-Haves

- [ ] export_pdf() produces valid PDF (starts with %PDF magic bytes)
- [ ] PDF contains metadata header: title, date, run_id, rule count
- [ ] PDF contains styled table with correct column headers and data rows
- [ ] Empty proposals produce valid PDF with "No rules proposed" message
- [ ] ExportError raised on write failures with PDF_EXPORT_FAILED error_code
- [ ] Built-in fonts only (Helvetica) — no TTF embedding

## Verification

- `pytest tests/test_export/test_pdf_export.py -v` — all pass
- `pytest tests/ -x -q` — full suite green
- `npx pyright src/policyfoundry/export/` — 0 errors (including new code)

## Inputs

- `src/policyfoundry/export/models.py` — ChangeRequestEntry, flatten_to_entries (from T01)
- `src/policyfoundry/export/change_request.py` — export_xlsx already present (from T01)
- `src/policyfoundry/exceptions.py` — ExportError (from T01)
- `tests/test_export/conftest.py` — shared fixtures (from T01)

## Expected Output

- `src/policyfoundry/export/change_request.py` — export_pdf() added
- `src/policyfoundry/export/__init__.py` — export_pdf re-exported
- `tests/test_export/test_pdf_export.py` — PDF export tests
