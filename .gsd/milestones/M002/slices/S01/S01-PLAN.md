# S01: Excel Ingestion & Column Auto-Detection

**Goal:** Parse the sample Excel traffic export, auto-detect all 10 columns by header name, normalize records into Pydantic models, and expose config override for non-standard layouts.
**Demo:** `policyfoundry analyze --source excel --file traffic.xlsx` parses the sample Excel, auto-detects all 10 columns, and prints a summary showing "Parsed 83,633 flows from 10 columns" with detected column mapping.

## Must-Haves

- `ExcelTrafficRecord` Pydantic model with 10 fields (protocol, ip1, port1, interface1, hostname1, ip2, port2, interface2, hostname2, flag) — neutral naming, not src/dst
- `ColumnMapping` Pydantic model mapping semantic names to column indices
- `ExcelIngestionResult` model (records, column_mapping, stats, warnings) following IngestionResult pattern
- `detect_columns(headers) -> ColumnMapping` using synonym dictionary — deterministic, no fuzzy matching
- `ingest_excel_file(path, column_mapping=None) -> ExcelIngestionResult` using openpyxl read_only mode
- `ExcelConfig` nested BaseModel in PolicyFoundryConfig (D006 pattern)
- Whitespace stripping on all string cells
- HostName2 DNS annotation cleanup ("10.x.x.x (no DNS resolution)" → extracted value)
- openpyxl moved from dev to main dependencies
- CLI `--source excel --file <path>` prints parsed summary (pipeline integration is S03/S05)
- All 10 columns auto-detected from the sample file's headers without configuration
- Config override path works when auto-detect is insufficient

## Verification

- `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py tests/test_ingestion/test_excel.py -v` — all pass
- `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx` prints summary with row count and column mapping

## Tasks

- [x] **T01: Pydantic models, column auto-detection, and ExcelConfig** `est:45m`
  - Why: Establishes the data contracts (ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult) and detection logic that the parser and all downstream slices depend on. Also adds ExcelConfig to the config hierarchy.
  - Files: `src/policyfoundry/ingestion/excel_schema.py`, `src/policyfoundry/ingestion/column_detect.py`, `src/policyfoundry/config/models.py`, `src/policyfoundry/exceptions.py`, `tests/test_ingestion/test_excel_schema.py`, `tests/test_ingestion/test_column_detect.py`
  - Do: Build ExcelTrafficRecord with validators (strip whitespace, clean DNS annotations), ColumnMapping with column index fields, ExcelIngestionResult following IngestionResult pattern. Build synonym dictionary for detect_columns with ranked matches for each semantic column. Add ExcelConfig (column_mapping overrides, sheet_name, header_row) as nested BaseModel in PolicyFoundryConfig. Add ExcelParseError to exceptions. Test schema validation (valid/invalid records, whitespace stripping, annotation cleanup) and column detection (sample headers, common synonyms, missing columns, ambiguous headers).
  - Verify: `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py -v`
  - Done when: All schema validation tests pass including edge cases; detect_columns correctly maps all 10 sample headers and common synonyms; ExcelConfig loads in PolicyFoundryConfig.

- [x] **T02: Excel parser, CLI wiring, and integration tests** `est:45m`
  - Why: Implements the runtime parser that reads Excel files via openpyxl, wires `--source excel --file` into the CLI, and proves the full slice demo works against the real sample file.
  - Files: `src/policyfoundry/ingestion/excel.py`, `src/policyfoundry/ingestion/__init__.py`, `src/policyfoundry/main.py`, `pyproject.toml`, `tests/test_ingestion/test_excel.py`
  - Do: Move openpyxl from dev to main deps. Build ingest_excel_file using read_only mode with explicit wb.close() in try/finally (not context manager per research). Auto-detect columns from header row, fall back to provided column_mapping. Parse each row into ExcelTrafficRecord, collecting warnings for unparseable rows. Wire `--source excel --file <path>` into the analyze command — load config, call ingest_excel_file, print Rich summary table with row count, column mapping, and any warnings. Export new symbols from ingestion __init__.py. Test against a small generated fixture Excel file (not the 83K row sample) for unit tests; run CLI against real sample for integration verification.
  - Verify: `pytest tests/test_ingestion/test_excel.py -v` and `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx`
  - Done when: Unit tests pass for parsing valid/invalid rows, auto-detect integration, config override path. CLI prints summary with "83,633" flow count and all 10 columns mapped from the sample file.

## Files Likely Touched

- `src/policyfoundry/ingestion/excel_schema.py` (new)
- `src/policyfoundry/ingestion/column_detect.py` (new)
- `src/policyfoundry/ingestion/excel.py` (new)
- `src/policyfoundry/ingestion/__init__.py` (extend exports)
- `src/policyfoundry/config/models.py` (add ExcelConfig)
- `src/policyfoundry/exceptions.py` (add ExcelParseError)
- `src/policyfoundry/main.py` (extend analyze command)
- `pyproject.toml` (move openpyxl to main deps)
- `tests/test_ingestion/test_excel_schema.py` (new)
- `tests/test_ingestion/test_column_detect.py` (new)
- `tests/test_ingestion/test_excel.py` (new)
