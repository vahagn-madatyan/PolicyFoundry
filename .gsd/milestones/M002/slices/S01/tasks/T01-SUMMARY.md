---
id: T01
parent: S01
milestone: M002
provides:
  - ExcelTrafficRecord Pydantic model (10 fields, validators)
  - ColumnMapping model with from_headers classmethod
  - ExcelIngestionResult model following IngestionResult pattern
  - detect_columns() synonym-based auto-detection
  - ExcelParseError exception subclass
  - ExcelConfig nested in PolicyFoundryConfig
key_files:
  - src/policyfoundry/ingestion/excel_schema.py
  - src/policyfoundry/ingestion/column_detect.py
  - src/policyfoundry/config/models.py
  - src/policyfoundry/exceptions.py
  - tests/test_ingestion/test_excel_schema.py
  - tests/test_ingestion/test_column_detect.py
key_decisions:
  - Hostname2 DNS annotation cleanup uses regex to extract value before parenthetical (handles "IP (no DNS resolution)" and any other annotation pattern)
  - SYNONYM_MAP uses ranked lists per semantic field; first match wins with claimed-header tracking to prevent double-mapping
  - ColumnMapping uses zero-based indices to match openpyxl's cell indexing convention
patterns_established:
  - Excel-specific Pydantic models parallel to VPC flow log models (separate schema, not extending NormalizedFlowLog)
  - Synonym dictionary pattern for deterministic column auto-detection
observability_surfaces:
  - ExcelParseError includes error_code="COLUMN_DETECT_FAILED" and details dict with unmatched_fields and available_headers
duration: ~12min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Pydantic models, column auto-detection, and ExcelConfig

**Built ExcelTrafficRecord (10 fields with whitespace/DNS validators), ColumnMapping, ExcelIngestionResult, synonym-based detect_columns(), ExcelParseError, and ExcelConfig — 30 tests passing.**

## What Happened

Created the foundation data contracts for Excel ingestion:

1. **excel_schema.py** — Three Pydantic models: `ExcelTrafficRecord` with 10 fields (protocol, ip1, port1, interface1, hostname1, ip2, port2, interface2, hostname2, flag), `@field_validator` for whitespace stripping on all string fields, DNS annotation cleanup on hostname2, and port bounds (0-65535). `ColumnMapping` with all 10 fields required as `int` indices plus `from_headers()` classmethod. `ExcelIngestionResult` following the IngestionResult pattern.

2. **column_detect.py** — `detect_columns()` with a `SYNONYM_MAP` covering the sample file's exact headers plus common vendor synonyms (Source IP, SrcIP, src_ip, etc.). Normalizes headers (lowercase, strip, collapse spaces), matches sequentially with claimed-header tracking, raises `ExcelParseError` with actionable message on failure.

3. **exceptions.py** — Added `ExcelParseError(IngestionError)` with structured details.

4. **config/models.py** — Added `ExcelConfig` (sheet_name, header_row, column_mapping override) nested in `PolicyFoundryConfig` following D006 pattern.

5. **Tests** — 17 schema tests (valid construction, whitespace stripping, DNS annotation cleanup, port bounds, field count) and 13 detection tests (sample headers, case-insensitive, synonym variants, missing columns, error messages, config integration).

## Verification

- `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py -v` → **30 passed**
- `python -c "from policyfoundry.config.models import PolicyFoundryConfig; c = PolicyFoundryConfig(); print(c.excel)"` → `sheet_name=None header_row=1 column_mapping=None`
- Full regression: `pytest tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ -v` → **124 passed** (no regressions)

### Slice-level verification status (T01 is intermediate):
- `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py` → ✅ passes
- `tests/test_ingestion/test_excel.py` → does not exist yet (T02)
- `policyfoundry analyze --source excel --file ...` → not wired yet (T02)

## Diagnostics

- `ExcelParseError` includes `error_code="COLUMN_DETECT_FAILED"` and `details` dict with `unmatched_fields` (list of field names) and `available_headers` (list of header strings) for programmatic inspection.
- `ColumnMapping.from_headers()` is the primary entry point — pass any header list to test detection.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/ingestion/excel_schema.py` — New: ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult models
- `src/policyfoundry/ingestion/column_detect.py` — New: detect_columns() with SYNONYM_MAP
- `src/policyfoundry/exceptions.py` — Added ExcelParseError subclass of IngestionError
- `src/policyfoundry/config/models.py` — Added ExcelConfig model and nested it in PolicyFoundryConfig
- `tests/test_ingestion/test_excel_schema.py` — New: 17 schema validation tests
- `tests/test_ingestion/test_column_detect.py` — New: 13 column detection + config integration tests
