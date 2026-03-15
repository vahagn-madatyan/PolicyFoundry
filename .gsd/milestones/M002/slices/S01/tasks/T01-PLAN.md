---
estimated_steps: 5
estimated_files: 6
---

# T01: Pydantic models, column auto-detection, and ExcelConfig

**Slice:** S01 — Excel Ingestion & Column Auto-Detection
**Milestone:** M002

## Description

Build the data contracts and column detection logic that the Excel parser and all downstream slices consume. This is the foundation layer — ExcelTrafficRecord defines the normalized record shape, ColumnMapping captures which Excel column maps to which semantic field, and detect_columns implements the synonym-based auto-detection. Also adds ExcelConfig to the config hierarchy and ExcelParseError to the exception tree.

## Steps

1. **Create `excel_schema.py`** with three Pydantic models:
   - `ExcelTrafficRecord`: 10 fields using neutral naming (protocol, ip1, port1, interface1, hostname1, ip2, port2, interface2, hostname2, flag). String fields get `@field_validator` that strips whitespace. hostname2 gets a validator that extracts the value from DNS annotations like "10.x.x.x (no DNS resolution)". Ports are `int` with `Field(ge=0, le=65535)`.
   - `ColumnMapping`: Maps semantic names (protocol, ip1, port1, etc.) to column indices (`int`). All 10 fields required. Add a `from_headers(headers: list[str]) -> ColumnMapping` classmethod that delegates to `detect_columns`.
   - `ExcelIngestionResult`: records (`list[ExcelTrafficRecord]`), column_mapping (`ColumnMapping`), total_rows (`int`), parsed_rows (`int`), skipped_rows (`int`), warnings (`list[str]`), source_file (`str`). Follow `IngestionResult` pattern.

2. **Create `column_detect.py`** with `detect_columns(headers: list[str]) -> ColumnMapping`:
   - Define a `SYNONYM_MAP: dict[str, list[str]]` mapping each semantic field to ranked synonyms. E.g. `"protocol": ["protocol", "proto", "ip_protocol", "ipprotocol"]`, `"ip1": ["ip1", "source ip", "srcip", "src_ip", "source address", "srcaddr", "source_ip"]`, etc.
   - Normalize headers: lowercase, strip whitespace, collapse spaces.
   - For each semantic field, find the first header that matches any synonym. Track which headers are claimed.
   - If all 10 matched → return ColumnMapping. If any unmatched → raise `ExcelParseError` with clear message listing unmatched semantic fields and available headers.

3. **Add `ExcelParseError`** to `exceptions.py` as subclass of `IngestionError`.

4. **Add `ExcelConfig`** to `config/models.py`:
   - `sheet_name: str | None = None` (default: first sheet)
   - `header_row: int = 1`
   - `column_mapping: dict[str, int] | None = None` (override for detect_columns)
   - Add `excel: ExcelConfig = Field(default_factory=ExcelConfig)` to `PolicyFoundryConfig`.

5. **Write tests** in `test_excel_schema.py` and `test_column_detect.py`:
   - Schema: valid record construction, whitespace stripping, DNS annotation cleanup, port validation (0-65535), invalid port rejection.
   - Column detect: sample file headers match all 10 fields, common synonym variants match, missing column raises ExcelParseError with actionable message, case-insensitive matching.
   - Config: ExcelConfig instantiates with defaults, nests in PolicyFoundryConfig.

## Must-Haves

- [ ] ExcelTrafficRecord has all 10 fields with proper validators
- [ ] Whitespace stripping works on all string fields
- [ ] DNS annotation "IP (no DNS resolution)" is cleaned to just the IP/hostname portion
- [ ] ColumnMapping requires all 10 column indices
- [ ] detect_columns maps the sample file's exact headers: Protocol, Interface1, HostName1, IP1, Port1, Interface2, HostName2, IP2, Port2, Flag
- [ ] detect_columns handles common synonyms (Source IP, SrcIP, src_ip, etc.)
- [ ] Missing columns produce ExcelParseError with unmatched fields listed
- [ ] ExcelConfig nests in PolicyFoundryConfig following D006

## Verification

- `pytest tests/test_ingestion/test_excel_schema.py tests/test_ingestion/test_column_detect.py -v` — all pass
- `python -c "from policyfoundry.config.models import PolicyFoundryConfig; c = PolicyFoundryConfig(); print(c.excel)"` — prints ExcelConfig defaults

## Inputs

- `src/policyfoundry/ingestion/schema.py` — reference for Pydantic model style (don't extend NormalizedFlowLog)
- `src/policyfoundry/ingestion/result.py` — reference for IngestionResult pattern
- `src/policyfoundry/config/models.py` — reference for nested BaseModel pattern (D006)
- `src/policyfoundry/exceptions.py` — reference for exception hierarchy
- S01-RESEARCH.md sample data profile — exact headers, data types, edge cases

## Expected Output

- `src/policyfoundry/ingestion/excel_schema.py` — ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult models
- `src/policyfoundry/ingestion/column_detect.py` — detect_columns function with synonym dictionary
- `src/policyfoundry/config/models.py` — ExcelConfig added to PolicyFoundryConfig
- `src/policyfoundry/exceptions.py` — ExcelParseError added
- `tests/test_ingestion/test_excel_schema.py` — schema validation tests
- `tests/test_ingestion/test_column_detect.py` — column detection tests
