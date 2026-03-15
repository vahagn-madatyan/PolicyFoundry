---
estimated_steps: 5
estimated_files: 5
---

# T02: Excel parser, CLI wiring, and integration tests

**Slice:** S01 — Excel Ingestion & Column Auto-Detection
**Milestone:** M002

## Description

Build the runtime Excel parser using openpyxl read_only mode, wire `--source excel --file <path>` into the CLI analyze command, and prove the slice demo against the real 83K-row sample file. This task consumes the models and detection logic from T01 and produces the boundary outputs that S02 depends on.

## Steps

1. **Move openpyxl to main dependencies** in `pyproject.toml` — cut from `[dependency-groups] dev` and add `"openpyxl>=3.1.5"` to `[project] dependencies`. Run `uv sync` to verify.

2. **Create `excel.py`** with `ingest_excel_file(path: str | Path, column_mapping: ColumnMapping | None = None, sheet_name: str | None = None, header_row: int = 1) -> ExcelIngestionResult`:
   - Open workbook with `openpyxl.load_workbook(path, read_only=True, data_only=True)` in try/finally for explicit `wb.close()`.
   - Select sheet by name or default to first. Raise ExcelParseError if sheet not found.
   - Read header row, call `detect_columns(headers)` if no column_mapping provided.
   - Iterate data rows, construct ExcelTrafficRecord for each. Catch validation errors per-row — append warning, increment skipped_rows, continue.
   - Handle None cells (skip row with warning), int/str type coercion for ports.
   - Return ExcelIngestionResult with all stats populated.
   - Use logging for row-level parse failures (not console output).

3. **Update `ingestion/__init__.py`** — export `ingest_excel_file`, `ExcelTrafficRecord`, `ColumnMapping`, `ExcelIngestionResult`, `detect_columns`.

4. **Wire CLI** in `main.py`:
   - Add `--file` option to `analyze` command (Optional[Path]).
   - When `--source excel`: validate `--file` is provided, load config, resolve ExcelConfig overrides (column_mapping, sheet_name, header_row), call `ingest_excel_file`, print Rich summary panel showing: source file, sheet name, total rows, parsed rows, skipped rows, column mapping table, any warnings. Return early (no pipeline yet — that's S03/S05).
   - When `--source excel` without `--file`: raise PolicyFoundryError with actionable message.

5. **Write tests** in `test_excel.py`:
   - Create a pytest fixture that generates a small Excel file (10-20 rows) with the sample headers using openpyxl. Include edge cases: trailing whitespace, DNS annotation in hostname2, varying port values.
   - Test: successful parse returns correct record count and all fields populated.
   - Test: auto-detect integration — headers detected, records parsed correctly.
   - Test: config override column_mapping works when headers are non-standard.
   - Test: missing file raises ExcelParseError.
   - Test: unparseable rows are skipped with warnings (not exceptions).
   - Test: sheet_name selection works.

## Must-Haves

- [ ] openpyxl is a main dependency (not dev-only)
- [ ] ingest_excel_file parses the 83K-row sample file without error
- [ ] Workbook is explicitly closed via try/finally (not context manager)
- [ ] Bad rows are skipped with warnings, not exceptions
- [ ] CLI `--source excel --file <path>` prints summary with row count and column mapping
- [ ] CLI `--source excel` without `--file` produces actionable error
- [ ] New symbols exported from ingestion __init__.py

## Verification

- `pytest tests/test_ingestion/test_excel.py -v` — all pass
- `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx` — prints summary showing 83,633 parsed flows and all 10 columns mapped

## Inputs

- `src/policyfoundry/ingestion/excel_schema.py` — T01 output: models and validators
- `src/policyfoundry/ingestion/column_detect.py` — T01 output: detect_columns function
- `src/policyfoundry/config/models.py` — T01 output: ExcelConfig in PolicyFoundryConfig
- `referance/samples/test-FW501_20260219_All_App1-updated.xlsx` — real sample file for integration verification

## Expected Output

- `src/policyfoundry/ingestion/excel.py` — ingest_excel_file function (S01→S02 boundary output)
- `src/policyfoundry/ingestion/__init__.py` — updated exports
- `src/policyfoundry/main.py` — analyze command extended with --source excel --file
- `pyproject.toml` — openpyxl in main dependencies
- `tests/test_ingestion/test_excel.py` — parser and integration tests
