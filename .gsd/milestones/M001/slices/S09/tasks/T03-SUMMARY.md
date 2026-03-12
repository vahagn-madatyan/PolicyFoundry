---
id: T03
parent: S09
milestone: M001
provides:
  - policyfoundry.ingestion package: schema, parser, dedup, result, local, s3 modules
  - NormalizedFlowLog 12-field Pydantic model with ProtocolEnum, ActionEnum, FlowDirection enums
  - VPC Flow Log v2 parser (parse_vpc_flow_log_line) — pure function, returns None on failure
  - SHA-256 dedup via 7-field composite key (compute_dedup_key)
  - IngestionResult Pydantic model with records, stats, warnings
  - async ingest_local_files with glob expansion, aiofiles I/O
  - async ingest_from_s3 with boto3+asyncio.to_thread, gzip support, pagination
key_files:
  - src/policyfoundry/ingestion/__init__.py
  - src/policyfoundry/ingestion/schema.py
  - src/policyfoundry/ingestion/parser.py
  - src/policyfoundry/ingestion/dedup.py
  - src/policyfoundry/ingestion/result.py
  - src/policyfoundry/ingestion/local.py
  - src/policyfoundry/ingestion/s3.py
key_decisions:
  - D008 confirmed: parse_vpc_flow_log_line returns None on malformed lines, never raises
  - D009 confirmed: NODATA/SKIPDATA silently skipped (checked at fields[13])
  - D010 confirmed: dedup key uses 7 fields (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action)
  - D011 confirmed: flow_direction defaults to FlowDirection.INBOUND for v2 lines
  - D012 confirmed: S3 uses boto3 + asyncio.to_thread (not aioboto3)
patterns_established:
  - Parser uses _EXPECTED_FIELD_COUNT=14, PROTOCOL_MAP (1→ICMP, 6→TCP, 17→UDP), ACTION_MAP (ACCEPT→ALLOW, REJECT→DENY)
  - _SENTINEL = "-" for missing fields, _parse_int_or_sentinel helper for int parsing
  - IngestionResult uses Field(default_factory=lambda: list[T]()) for mutable defaults
  - Local ingestion catches FileNotFoundError/PermissionError per file, adds warning, continues
  - S3 ingestion catches ClientError with response['Error']['Code'] extraction, BadGzipFile handling
observability_surfaces:
  - Parser logs warnings via logging.getLogger(__name__) for field count mismatches, unsupported protocols, unknown actions, parse errors
  - Local/S3 ingestion surfaces errors via IngestionResult.warnings list and errors_skipped count
duration: 20min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T03: Reconstruct src ingestion module from bytecode

**Reconstructed 7 ingestion source files from CPython 3.13 bytecode: schema, parser, dedup, result, local, and S3 modules with full VPC Flow Log v2 parsing pipeline.**

## What Happened

Disassembled all 7 `.pyc` files in `src/policyfoundry/ingestion/__pycache__/` using the `dis` module to extract constants, names, variable names, and control flow. Reconstructed each source file matching the original bytecode structure:

1. **schema.py** — 3 StrEnum classes (ProtocolEnum, ActionEnum, FlowDirection) and NormalizedFlowLog BaseModel with 12 fields. Port fields use `Field(ge=0, le=65535)`, bytes_transferred and packets_count use `Field(ge=0, default=0)`, IP fields use `IPv4Address | IPv6Address` union type.

2. **parser.py** — VPC Flow Log v2 parser with `_EXPECTED_FIELD_COUNT=14`, `PROTOCOL_MAP` (int→ProtocolEnum), `ACTION_MAP` (str→ActionEnum). `parse_vpc_flow_log_line` is a pure function wrapped in try/except that returns None on any failure. `is_header_line` checks `startswith("version ")`. `is_metadata_line` checks `fields[13] in _METADATA_STATUSES`.

3. **dedup.py** — `compute_dedup_key` builds a `|`-joined composite from 7 fields (str(src_ip), str(dst_ip), str(src_port), str(dst_port), protocol.value, timestamp.isoformat(), action.value) then returns SHA-256 hexdigest.

4. **result.py** — `IngestionResult(BaseModel)` with 6 fields: records, total_lines, duplicates_removed, errors_skipped, source_files, warnings. Mutable defaults via `Field(default_factory=lambda: list[T]())`.

5. **local.py** — `_expand_paths` handles glob expansion with dedup via seen set. `ingest_local_files` is async, uses aiofiles, catches FileNotFoundError/PermissionError per file.

6. **s3.py** — `ingest_from_s3` is async, uses `boto3.Session(profile_name=aws_profile).client("s3")`, `asyncio.to_thread` for `_list_object_keys` and `_get_object_bytes`. Handles gzip decompression, BadGzipFile, and nested ClientError/Exception handling at both per-object and per-bucket levels.

7. **__init__.py** — Re-exports 5 symbols with `__all__`.

## Verification

- `uv run python -c "from policyfoundry.ingestion.parser import parse_vpc_flow_log_line; from policyfoundry.ingestion.local import ingest_local_files; from policyfoundry.ingestion.schema import NormalizedFlowLog; print('OK')"` → OK ✅
- `uv run python -c "from policyfoundry.ingestion.dedup import compute_dedup_key; from policyfoundry.ingestion.result import IngestionResult; print('OK')"` → OK ✅
- Parser returns None on malformed lines (D008) ✅
- Parser skips NODATA/SKIPDATA (D009) ✅
- Dedup key uses exactly 7 fields; identical records with different bytes/packets produce same hash (D010) ✅
- flow_direction defaults to INBOUND (D011) ✅
- `ingest_local_files` is `async def` (verified with `inspect.iscoroutinefunction`) ✅
- All 7 files import without error ✅
- End-to-end local ingestion test: 3 lines → 2 records (1 duplicate removed), 0 errors ✅

### Slice-level verification (intermediate — partial expected):
- `uv run pytest tests/test_ingestion/ -x` → 0 items collected (test files not yet reconstructed — later task) — expected
- `uv run pytest tests/test_cli/ -x` → 22 tests, all `pytest.fail("Not yet implemented")` — expected (waiting for T10+)

## Diagnostics

- Import and call `parse_vpc_flow_log_line` with a sample v2 line to verify parsing
- Check `IngestionResult.warnings` list for any ingestion issues
- Parser logs warnings via `logging.getLogger(__name__)` — enable DEBUG to see per-line decisions

## Deviations

- Task plan verification command used `deduplicate_records` but bytecode proves the function is `compute_dedup_key` — used correct name
- Task plan described NormalizedFlowLog as "10-field" but bytecode shows 12 fields (docstring says "12 fields") — schema includes rule_id and app_name as optional fields plus the original 10

## Known Issues

None

## Files Created/Modified

- `src/policyfoundry/ingestion/__init__.py` — Package init with 5-symbol __all__ re-export
- `src/policyfoundry/ingestion/schema.py` — NormalizedFlowLog, ProtocolEnum, ActionEnum, FlowDirection
- `src/policyfoundry/ingestion/parser.py` — VPC Flow Log v2 parser with regex-free field splitting
- `src/policyfoundry/ingestion/dedup.py` — SHA-256 7-field composite dedup key
- `src/policyfoundry/ingestion/result.py` — IngestionResult Pydantic model
- `src/policyfoundry/ingestion/local.py` — Async local file ingestion with glob/aiofiles
- `src/policyfoundry/ingestion/s3.py` — Async S3 ingestion with boto3/asyncio.to_thread/gzip
