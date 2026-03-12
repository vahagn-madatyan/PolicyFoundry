---
estimated_steps: 4
estimated_files: 7
---

# T03: Reconstruct src ingestion module from bytecode

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the ingestion module: the VPC Flow Log parser, deduplication logic, ingestion result types, and local/S3 file readers. The parser contains complex regex patterns for AWS VPC Flow Log v2 format. Local and S3 ingestion are async functions. The pipeline runner calls `ingest_local_files()` during the analyze command.

## Steps

1. **Reconstruct `ingestion/schema.py`** — `NormalizedFlowLog` dataclass or Pydantic model with the 10-field normalized schema (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action, bytes_transferred, packets_count, flow_direction). Extract field names from bytecode constants.

2. **Reconstruct `ingestion/parser.py` + `ingestion/dedup.py` + `ingestion/result.py`** — Parser: `parse_flow_log_line(line: str) -> NormalizedFlowLog | None` (returns None on failure per D008, skips NODATA/SKIPDATA per D009). Dedup: uses 7-field key per D010. Result: `IngestionResult` dataclass with counts and file paths. Extract regex patterns and field mappings from string constants in bytecode.

3. **Reconstruct `ingestion/local.py` + `ingestion/s3.py`** — `async ingest_local_files(paths) -> IngestionResult` reads local files, parses lines, deduplicates. `s3.py` does the same via boto3 with `asyncio.to_thread` (per D012). Both use `aiofiles` for async I/O.

4. **Reconstruct `ingestion/__init__.py`** and verify all imports work.

## Must-Haves

- [ ] `parse_flow_log_line` returns `None` on malformed lines (D008) and skips NODATA/SKIPDATA (D009)
- [ ] Dedup key uses exactly 7 fields per D010
- [ ] `flow_direction` defaults to INBOUND for v2 lines (D011)
- [ ] `ingest_local_files` is an `async def` function
- [ ] All 7 files import without error

## Verification

- `uv run python -c "from policyfoundry.ingestion.parser import parse_flow_log_line; from policyfoundry.ingestion.local import ingest_local_files; from policyfoundry.ingestion.schema import NormalizedFlowLog; print('OK')"`
- `uv run python -c "from policyfoundry.ingestion.dedup import deduplicate_records; from policyfoundry.ingestion.result import IngestionResult; print('OK')"`

## Observability Impact

- Signals added/changed: None (reconstruction only)
- How a future agent inspects this: Import and call `parse_flow_log_line` with a sample line to verify parsing
- Failure state exposed: None

## Inputs

- `src/policyfoundry/ingestion/__pycache__/*.cpython-313.pyc` (7 files, 678–7600 bytes)
- `tools/inspect_pyc.py` from T01
- Decisions D008, D009, D010, D011, D012
- `src/policyfoundry/exceptions.py` from T02 (IngestionError, ParseError, S3AccessError)

## Expected Output

- `src/policyfoundry/ingestion/__init__.py` — package re-exports
- `src/policyfoundry/ingestion/schema.py` — NormalizedFlowLog 10-field schema
- `src/policyfoundry/ingestion/parser.py` — VPC Flow Log v2 parser with regex
- `src/policyfoundry/ingestion/dedup.py` — deduplication logic
- `src/policyfoundry/ingestion/result.py` — IngestionResult type
- `src/policyfoundry/ingestion/local.py` — async local file ingestion
- `src/policyfoundry/ingestion/s3.py` — async S3 ingestion
