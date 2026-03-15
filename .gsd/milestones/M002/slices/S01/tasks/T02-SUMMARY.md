---
id: T02
parent: S01
milestone: M002
provides:
  - ingest_excel_file() runtime parser with openpyxl read_only mode
  - CLI --source excel --file <path> command with Rich summary output
  - 24 tests covering parsing, auto-detection integration, error handling, and 83K-row sample
key_files:
  - src/policyfoundry/ingestion/excel.py
  - src/policyfoundry/ingestion/__init__.py
  - src/policyfoundry/main.py
  - pyproject.toml
  - tests/test_ingestion/test_excel.py
key_decisions:
  - Workbook opened with openpyxl.load_workbook(read_only=True, data_only=True) and closed via try/finally (not context manager)
  - Port coercion handles int, float (Excel stores numbers as float), and string representations
  - Bad rows logged at DEBUG level and counted as skipped — never raised as exceptions
  - Excel ingestion helper (_run_excel_ingestion) extracted as module-level function to keep analyze() focused
patterns_established:
  - CLI source branching pattern — --source excel returns early with ingestion summary; flow log sources continue to pipeline
  - Lazy import pattern for Excel modules in CLI hot path (avoids importing openpyxl until needed)
observability_surfaces:
  - Row-level parse failures logged via logger.debug() with row number and error details
  - ExcelIngestionResult.warnings list captures per-row skip reasons for programmatic inspection
  - CLI prints Rich summary panel with total/parsed/skipped counts and column mapping table
duration: ~10min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Excel parser, CLI wiring, and integration tests

**Built ingest_excel_file() parser with openpyxl read_only mode, wired `--source excel --file` into CLI with Rich summary, and proved 83,633 rows parse with all 10 columns auto-detected — 24 tests passing.**

## What Happened

1. **pyproject.toml** — Moved `openpyxl>=3.1.5` from `[dependency-groups] dev` to `[project] dependencies`. Ran `uv sync` to verify.

2. **excel.py** — Built `ingest_excel_file(path, column_mapping=None, sheet_name=None, header_row=1) -> ExcelIngestionResult`:
   - Opens workbook with `openpyxl.load_workbook(path, read_only=True, data_only=True)` in try/finally for explicit `wb.close()`.
   - Selects sheet by name or defaults to first. Raises ExcelParseError if sheet not found.
   - Reads header row, calls `detect_columns(headers)` if no column_mapping provided.
   - Iterates data rows, constructs ExcelTrafficRecord for each. Catches ValidationError per-row — appends warning, increments skipped_rows, continues.
   - Handles None cells (skip row with warning), int/str/float type coercion for ports via `_coerce_port()`.
   - Returns ExcelIngestionResult with all stats populated.

3. **ingestion/__init__.py** — Exports `ingest_excel_file`, `ExcelTrafficRecord`, `ColumnMapping`, `ExcelIngestionResult`, `detect_columns`.

4. **main.py** — Extended `analyze` command:
   - Added `--file` option (Optional[Path]).
   - When `--source excel`: validates `--file` is provided, loads config, resolves ExcelConfig overrides, calls `ingest_excel_file`, prints Rich summary panel with source file, row counts, column mapping table, and optional warnings.
   - When `--source excel` without `--file`: raises PolicyFoundryError with actionable message.

5. **test_excel.py** — 24 tests across 7 test classes:
   - TestSuccessfulParsing (8): record count, field values, whitespace stripping, DNS annotation cleanup, string/float port coercion, source_file, column_mapping
   - TestAutoDetectIntegration (2): header detection, column index verification
   - TestColumnMappingOverride (2): explicit mapping with standard and non-standard headers
   - TestErrorHandling (4): missing file, missing file error code, sheet not found, sheet not found error code
   - TestBadRowHandling (3): bad rows skipped with warnings, good rows still parsed, total count correct
   - TestSheetSelection (2): explicit sheet name, default first sheet
   - TestRealSampleIntegration (3): 83,633 rows parsed, all 10 columns detected, first record fields correct

## Verification

- `pytest tests/test_ingestion/test_excel.py -v` → **24 passed** in ~7s
- `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py tests/test_ingestion/test_excel.py -v` → **54 passed** (full slice)
- `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx` → prints summary with 83,633 parsed rows, 0 skipped, all 10 columns mapped
- `policyfoundry analyze --source excel` (without --file) → error panel with "MISSING_FILE_OPTION" and actionable example

### Slice-level verification (T02 is final task):
- ✅ `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py tests/test_ingestion/test_excel.py -v` → 54 passed
- ✅ `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx` → prints summary with 83,633 parsed flows and all 10 columns mapped

## Diagnostics

- `ingest_excel_file()` returns `ExcelIngestionResult` with `.warnings` list for per-row skip reasons
- Row-level parse failures logged at `DEBUG` level — enable with `--debug` flag
- `ExcelParseError` includes structured `error_code` and `details` dict for programmatic inspection
- CLI `--verbose` flag shows first 20 warnings in the summary output

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `pyproject.toml` — Moved openpyxl from dev to main dependencies
- `src/policyfoundry/ingestion/excel.py` — New: ingest_excel_file() with read_only openpyxl, port coercion, bad-row handling
- `src/policyfoundry/ingestion/__init__.py` — Updated: exports ingest_excel_file, ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult, detect_columns
- `src/policyfoundry/main.py` — Extended: analyze command with --file option, --source excel branch, _run_excel_ingestion helper
- `tests/test_ingestion/test_excel.py` — New: 24 tests covering parsing, detection integration, overrides, errors, bad rows, sheet selection, real sample
