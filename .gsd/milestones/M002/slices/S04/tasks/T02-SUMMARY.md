---
id: T02
parent: S04
milestone: M002
provides:
  - export_pdf() in export/change_request.py producing styled PDF change request documents
  - export_pdf re-exported from export/__init__.py
key_files:
  - src/policyfoundry/export/change_request.py
  - src/policyfoundry/export/__init__.py
  - tests/test_export/test_pdf_export.py
key_decisions:
  - _PDF_COLUMNS with tuned proportional widths (total 126 weight units) to avoid word-wrapping short values like CREATE/UPDATE in narrow cells
  - fpdf2 FlateDecode compresses content streams — tests use zlib decompression helper for text verification
patterns_established:
  - _extract_pdf_text() test helper decompresses FlateDecode streams for content assertions on fpdf2 output
observability_surfaces:
  - ExportError with error_code=PDF_EXPORT_FAILED, details={output_path, rule_count}, __cause__ preserving original exception
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: PDF export with fpdf2

**Implemented export_pdf() using fpdf2's table API with metadata header, styled table, and empty-proposals handling.**

## What Happened

Added `export_pdf()` to `change_request.py` using fpdf2's `FPDF` class with the `table()` context manager. The PDF includes:
- Page 1 metadata: bold title ("Firewall Change Request"), generated date, run_id, source type, total rules, separator line
- Styled table with `FontFace` heading row (bold white text on blue #4472C4 background), `SINGLE_TOP_LINE` borders, proportional column widths
- Empty proposals produce a valid PDF with metadata and italic "No rules proposed." message
- Built-in Helvetica only — no TTF embedding required

Updated `export/__init__.py` to re-export `export_pdf`. Created 16 tests across 5 test classes covering structure, metadata, data rows, empty proposals, and error handling.

## Verification

- `pytest tests/test_export/test_pdf_export.py -v` — 16/16 pass
- `npx pyright src/policyfoundry/export/` — 0 errors
- `pytest tests/ -x -q` — 586 passed (2 pre-existing moto import failures excluded, unrelated to this task)

Slice-level verification status:
- ✅ `pytest tests/test_export/test_models.py -v` — pass (from T01)
- ✅ `pytest tests/test_export/test_xlsx_export.py -v` — pass (from T01)
- ✅ `pytest tests/test_export/test_pdf_export.py -v` — 16/16 pass
- ✅ `npx pyright src/policyfoundry/export/` — 0 errors
- ✅ `pytest tests/ -x -q` — 586 passed (baseline was 564, now 586)

All slice verification checks pass. S04 is complete.

## Diagnostics

- `ExportError.error_code == "PDF_EXPORT_FAILED"` on any write/generation failure
- `ExportError.details` carries `output_path` and `rule_count`
- `ExportError.__cause__` preserves the original exception for chained tracebacks

## Deviations

- Column width proportions tuned during implementation: initial weights caused "CREATE"/"UPDATE" to word-wrap in narrow action column. Adjusted from even distribution to weighted proportions (action: 8→10, justification: 30→26) to prevent wrapping of short action values.
- Test approach: raw byte search on PDF won't work because fpdf2 uses FlateDecode compression. Added `_extract_pdf_text()` helper that decompresses zlib streams for content assertions.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/export/change_request.py` — added export_pdf() function, _PDF_COLUMNS definitions, fpdf2/FontFace imports
- `src/policyfoundry/export/__init__.py` — added export_pdf to public API and __all__
- `tests/test_export/test_pdf_export.py` — 16 tests across 5 classes: structure, metadata, data rows, empty proposals, error handling
