# S01: Excel Ingestion & Column Auto-Detection — UAT

**Milestone:** M002
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: Core deliverables are testable via pytest (schema validation, parsing logic) plus a single CLI command that exercises the full ingestion path against the real 83K-row sample file.

## Preconditions

- PolicyFoundry installed in development mode (`uv sync` or `pip install -e .`)
- Sample Excel file present at `referance/samples/test-FW501_20260219_All_App1-updated.xlsx`
- openpyxl available as a main dependency (not just dev)

## Smoke Test

```bash
policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx
```
Should print a Rich panel showing "Total rows: 83,633", "Parsed rows: 83,633", "Skipped rows: 0" and a column mapping table with all 10 fields.

## Test Cases

### 1. Full sample file ingestion

1. Run `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx`
2. **Expected:** Rich panel shows 83,633 total/parsed rows, 0 skipped rows, and all 10 columns (protocol, ip1, port1, interface1, hostname1, ip2, port2, interface2, hostname2, flag) with correct column indices.

### 2. Missing --file flag produces actionable error

1. Run `policyfoundry analyze --source excel`
2. **Expected:** Error panel with "MISSING_FILE_OPTION" error code and example usage showing `--file traffic.xlsx`.

### 3. Non-existent file produces clear error

1. Run `policyfoundry analyze --source excel --file nonexistent.xlsx`
2. **Expected:** Error panel with a file-not-found message and FILE_NOT_FOUND error code.

### 4. Unit test suite passes

1. Run `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py tests/test_ingestion/test_excel.py -v`
2. **Expected:** 54 tests pass covering schema validation, column detection, parsing, error handling, and real sample integration.

## Edge Cases

### Whitespace in cell values

1. The test suite includes `test_whitespace_stripped` which verifies leading/trailing whitespace is stripped from all string fields.
2. **Expected:** ExcelTrafficRecord validator strips whitespace — `"  tcp  "` becomes `"tcp"`.

### DNS annotation cleanup

1. The test suite includes `test_dns_annotation_cleanup_no_dns_resolution` and related tests.
2. **Expected:** `"10.1.2.3 (no DNS resolution)"` in hostname2 becomes `"10.1.2.3"`.

### Float port coercion

1. Excel stores numbers as floats internally (e.g. 443.0 instead of 443).
2. **Expected:** Port fields correctly coerce float to int. Verified by `test_float_port_coerced`.

### Bad rows skipped gracefully

1. The test suite includes `TestBadRowHandling` with rows containing invalid data.
2. **Expected:** Invalid rows are skipped with warnings, valid rows still parsed, total count reflects reality.

## Failure Signals

- Test count drops below 54 → regression in schema, detection, or parsing logic
- CLI output shows skipped rows > 0 on the sample file → parser regression or data corruption
- Column mapping table shows fewer than 10 fields → synonym dictionary regression
- `ModuleNotFoundError: openpyxl` → dependency not moved to main deps in pyproject.toml

## Requirements Proved By This UAT

- R101 (Excel traffic log ingestion with auto-detect column mapping) — Smoke test and test case 1 prove auto-detection works on the real 83K-row sample with all 10 columns mapped
- R102 (Config override for custom column mappings) — Unit tests prove config override works with non-standard headers (TestColumnMappingOverride in test_excel.py)

## Not Proven By This UAT

- Pipeline integration (--source excel feeding into LangGraph analysis) — deferred to S03/S05
- Behavior with different vendor Excel formats beyond the test synonyms — covered by config override mechanism but not UAT-tested with real alternate vendor files
- Performance under extremely large files (>1M rows) — not tested

## Notes for Tester

- The sample file is ~83K rows and takes ~7s to parse in tests. CLI execution against it is similarly fast.
- The "referance" directory name is intentionally misspelled (matches the existing project convention).
- Column indices in the mapping table are zero-based (matching openpyxl convention).
