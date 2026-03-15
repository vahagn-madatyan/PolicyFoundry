---
id: S01
parent: M002
milestone: M002
provides:
  - ExcelTrafficRecord Pydantic model (10 fields, validators for whitespace/DNS cleanup)
  - ColumnMapping model with from_headers classmethod and zero-based indices
  - ExcelIngestionResult model following IngestionResult pattern
  - detect_columns() synonym-based auto-detection with claimed-header tracking
  - ingest_excel_file() runtime parser with openpyxl read_only mode
  - ExcelParseError exception subclass with structured error codes
  - ExcelConfig nested in PolicyFoundryConfig (sheet_name, header_row, column_mapping)
  - CLI --source excel --file <path> with Rich summary output
requires:
  - slice: none
    provides: first slice in M002
affects:
  - S02 (consumes ExcelTrafficRecord, ExcelIngestionResult, ColumnMapping)
  - S05 (consumes ExcelConfig in PolicyFoundryConfig)
key_files:
  - src/policyfoundry/ingestion/excel_schema.py
  - src/policyfoundry/ingestion/column_detect.py
  - src/policyfoundry/ingestion/excel.py
  - src/policyfoundry/ingestion/__init__.py
  - src/policyfoundry/config/models.py
  - src/policyfoundry/exceptions.py
  - src/policyfoundry/main.py
  - pyproject.toml
  - tests/test_ingestion/test_excel_schema.py
  - tests/test_ingestion/test_column_detect.py
  - tests/test_ingestion/test_excel.py
key_decisions:
  - D043: Neutral field naming (ip1/port1/ip2/port2 not src/dst) — direction inference is S02's job
  - D044: Synonym dictionary for column auto-detect — deterministic exact match after normalize, no fuzzy/NLP
  - Hostname2 DNS annotation cleanup via regex extracting value before parenthetical
  - ColumnMapping uses zero-based indices matching openpyxl cell indexing
  - Workbook opened with read_only=True, data_only=True and closed via try/finally (not context manager)
  - Port coercion handles int, float (Excel stores numbers as float), and string representations
  - Bad rows logged at DEBUG and counted as skipped — never raised as exceptions
  - CLI source branching pattern — --source excel returns early with ingestion summary; pipeline integration is S03/S05
  - Lazy import pattern for Excel modules in CLI hot path
patterns_established:
  - Excel-specific Pydantic models parallel to VPC flow log models (separate schema, not extending NormalizedFlowLog)
  - Synonym dictionary pattern for deterministic column auto-detection
  - CLI source branching pattern for multiple ingestion modes
  - Lazy import pattern for optional heavy dependencies
observability_surfaces:
  - ExcelParseError includes error_code and details dict (unmatched_fields, available_headers) for programmatic inspection
  - ExcelIngestionResult.warnings list captures per-row skip reasons
  - Row-level parse failures logged via logger.debug() with row number and error details
  - CLI prints Rich summary panel with total/parsed/skipped counts and column mapping table
  - CLI error panel with MISSING_FILE_OPTION and actionable example when --file omitted
drill_down_paths:
  - .gsd/milestones/M002/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S01/tasks/T02-SUMMARY.md
duration: ~22min
verification_result: passed
completed_at: 2026-03-15
---

# S01: Excel Ingestion & Column Auto-Detection

**Built Excel traffic parser with synonym-based column auto-detection, 10-field Pydantic schema, config override support, and CLI wiring — parses 83,633 rows with all 10 columns auto-detected. 54 tests passing.**

## What Happened

Built the complete Excel ingestion pipeline in two tasks:

**T01 — Data contracts and detection logic:** Created `ExcelTrafficRecord` with 10 fields using neutral naming (ip1/port1 not src/dst since direction inference is S02's job). Added `@field_validator` for whitespace stripping on all string fields, DNS annotation cleanup on hostname2 (`"10.x.x.x (no DNS resolution)"` → extracted IP), and port bounds validation (0–65535). Built `ColumnMapping` with zero-based column indices and `from_headers()` classmethod. Built `detect_columns()` with a `SYNONYM_MAP` covering the sample file's exact headers plus common vendor synonyms — normalizes headers (lowercase, strip, collapse spaces), matches sequentially with claimed-header tracking to prevent double-mapping. Added `ExcelParseError(IngestionError)` with structured error codes. Added `ExcelConfig` (sheet_name, header_row, column_mapping override) nested in `PolicyFoundryConfig`.

**T02 — Runtime parser and CLI:** Built `ingest_excel_file()` using openpyxl `read_only=True, data_only=True` with explicit `wb.close()` in try/finally. Handles port type coercion (int/float/string), per-row ValidationError catch-and-skip with warnings, sheet selection by name or default-to-first. Wired `--source excel --file <path>` into the CLI `analyze` command — prints Rich summary panel with row counts and column mapping table. Moved openpyxl from dev to main dependencies. Extracted `_run_excel_ingestion` helper to keep `analyze()` focused.

## Verification

- `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py tests/test_ingestion/test_excel.py -v` → **54 passed** in ~7s
  - 17 schema tests (valid construction, whitespace stripping, DNS cleanup, port bounds, field count)
  - 13 detection tests (sample headers, case-insensitive, synonym variants, missing columns, error messages, config integration)
  - 24 parser tests (parsing, auto-detect integration, column mapping override, error handling, bad rows, sheet selection, 83K-row real sample)
- `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx` → prints summary with 83,633 parsed rows, 0 skipped, all 10 columns mapped
- `policyfoundry analyze --source excel` (without --file) → error panel with MISSING_FILE_OPTION and actionable example
- Full regression: 124+ tests pass with no regressions in existing M001 tests

## Requirements Advanced

- R101 (Excel traffic log ingestion with auto-detect column mapping) — Fully implemented: auto-detect maps all 10 columns from sample file headers, handles whitespace and DNS annotations, parses 83,633 rows
- R102 (Config override for custom column mappings) — Fully implemented: ExcelConfig in PolicyFoundryConfig provides sheet_name, header_row, and column_mapping overrides; tested with non-standard headers

## Requirements Validated

- R101 — Validated by 54 tests (schema validation, column detection with synonyms, full 83K-row sample parse) plus CLI demo against real sample file
- R102 — Validated by TestColumnMappingOverride tests proving config override works with both standard and non-standard headers

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None.

## Known Limitations

- CLI `--source excel` currently prints ingestion summary only — pipeline integration (analysis, proposals) is S03/S05
- No streaming/chunked reading for very large files (>1M rows) — the full record list is held in memory
- Column auto-detect requires at least a rough match to known synonyms — completely novel header names need config override (by design per D041)

## Follow-ups

- none — all planned work for S01 is complete

## Files Created/Modified

- `src/policyfoundry/ingestion/excel_schema.py` — New: ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult models
- `src/policyfoundry/ingestion/column_detect.py` — New: detect_columns() with SYNONYM_MAP
- `src/policyfoundry/ingestion/excel.py` — New: ingest_excel_file() parser with openpyxl read_only mode
- `src/policyfoundry/ingestion/__init__.py` — Updated: exports for all Excel ingestion symbols
- `src/policyfoundry/config/models.py` — Added: ExcelConfig model nested in PolicyFoundryConfig
- `src/policyfoundry/exceptions.py` — Added: ExcelParseError subclass of IngestionError
- `src/policyfoundry/main.py` — Extended: analyze command with --file option and --source excel branch
- `pyproject.toml` — Moved openpyxl from dev to main dependencies
- `tests/test_ingestion/test_excel_schema.py` — New: 17 schema validation tests
- `tests/test_ingestion/test_column_detect.py` — New: 13 column detection + config integration tests
- `tests/test_ingestion/test_excel.py` — New: 24 parser, integration, and real sample tests

## Forward Intelligence

### What the next slice should know
- `ExcelTrafficRecord` uses neutral naming (ip1/port1/ip2/port2, not src/dst). S02 must map these to src/dst via direction inference from the `flag` field and interface/port heuristics.
- The `flag` field contains values like "U", "UI", "UIO" — these are the primary signal for direction inference.
- `ingest_excel_file()` returns `ExcelIngestionResult` with `.records` (list[ExcelTrafficRecord]) and `.column_mapping` (ColumnMapping). S02 consumes the records list.
- Port coercion already handles int/float/string — downstream code can rely on `port1` and `port2` being `int`.

### What's fragile
- The synonym dictionary in `column_detect.py` is the complete mapping authority — if a new vendor uses completely novel header names, it will fail to auto-detect (config override is the escape hatch per D041, but the synonym list may need expansion as more vendors are encountered).
- `read_only=True` mode in openpyxl doesn't support some worksheet features (merged cells, etc.) — should be fine for tabular data exports but could break on heavily formatted spreadsheets.

### Authoritative diagnostics
- `ExcelIngestionResult.warnings` — any parse failures are captured here with row numbers; check this first when rows are skipped
- `ExcelParseError.details` dict — contains `unmatched_fields` and `available_headers` when column detection fails; this is the fastest path to diagnosing why a new Excel format isn't recognized

### What assumptions changed
- None — the sample file matched expectations exactly. All 10 columns auto-detected, 83,633 rows parsed with 0 skipped.
