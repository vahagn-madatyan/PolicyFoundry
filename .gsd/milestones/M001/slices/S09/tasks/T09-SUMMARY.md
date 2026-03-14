---
id: T09
parent: S09
milestone: M001
provides:
  - 8 test files for ingestion and storage modules — 55 ingestion tests + 39 storage tests = 94 new tests
  - pytest asyncio_mode = "auto" configuration in pyproject.toml (D036)
key_files:
  - tests/test_ingestion/conftest.py
  - tests/test_ingestion/test_parser.py
  - tests/test_ingestion/test_dedup.py
  - tests/test_ingestion/test_local.py
  - tests/test_ingestion/test_s3.py
  - tests/test_storage/conftest.py
  - tests/test_storage/test_queries.py
  - tests/test_storage/test_writer.py
  - pyproject.toml
key_decisions:
  - "D036: Added asyncio_mode = 'auto' to pyproject.toml — storage tests in bytecode are async without @pytest.mark.asyncio decorators; required for pytest-asyncio 1.3.0"
patterns_established:
  - "S3 tests use mock_aws() as context manager (not decorator) because moto 5.x wraps async→sync when used as decorator, breaking pytest-asyncio detection"
  - "Storage conftest builds Parquet test data directly with PyArrow (bypassing write_records) for fixture independence"
  - "Ingestion conftest provides 7 fixtures: valid_vpc_v2_line, header_line, nodata_line, skipdata_line, malformed_line, sample_vpc_log_content, tmp_log_file"
observability_surfaces:
  - none
duration: 25min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T09: Reconstruct test files — ingestion, storage

**Reconstructed 8 test files from CPython 3.13 bytecode — 94 tests across ingestion (parser, dedup, local, S3) and storage (writer, queries) modules; added asyncio_mode = "auto" config (D036).**

## What Happened

Extracted structure, constants, and logic from 7 bytecode files (3–43KB each) using `dis` module disassembly. Reconstructed:

**Ingestion tests (55 tests):**
- `conftest.py` — 7 fixtures with exact VPC Flow Log v2 sample lines extracted from bytecode constants
- `test_parser.py` — 22 tests across 7 classes: valid line parsing, protocol/action mapping, sentinel handling, NODATA/SKIPDATA skipping (D008, D009), version handling
- `test_dedup.py` — 10 tests verifying 7-field composite key (D010): consistent hashing, field sensitivity (bytes/packets excluded, ports/protocol/action/timestamp included), hex string format
- `test_local.py` — 12 tests across 8 classes: single/multi file ingestion, malformed line handling, deduplication, missing files, glob patterns, empty files, NODATA/SKIPDATA
- `test_s3.py` — 11 tests across 7 classes: plain text, gzip decompression, prefix scan, cross-object dedup, malformed lines, error handling (nonexistent bucket, access denied), AWS profile forwarding (D012)

**Storage tests (39 tests):**
- `conftest.py` — 3 fixtures: 5 sample NormalizedFlowLog records (mixed protocols/actions/IPs), tmp data_dir, pre_written_parquet (direct PyArrow write)
- `test_writer.py` — 20 tests across 7 classes: write produces Parquet, zstd compression, 13-column schema, IP/enum string storage, custom metadata (source_files, timestamp, record_count), cross-run dedup, purge, empty input, filename pattern (D014)
- `test_queries.py` — 19 tests across 6 classes: top_talkers (ranking, n-limit, total_bytes), denied_flows (action filter, grouping), traffic_by_protocol (protocol coverage, percentage sum, per-protocol bytes), traffic_summary (totals, unique counts, allowed/denied, date range), empty data dir, corrupt file handling

**Config change:** Added `[tool.pytest.ini_options] asyncio_mode = "auto"` — bytecode analysis revealed storage tests use `async def` without `@pytest.mark.asyncio` decorators, which requires auto mode (D036).

## Verification

- `uv run pytest tests/test_ingestion/ -x -v` → **55 passed** ✓
- `uv run pytest tests/test_storage/ -x -v` → **39 passed** ✓
- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ -x -v` → **169 passed** (no regressions) ✓

**Slice-level checks (partial — intermediate task):**
- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ -x` → ✓ pass (5 of 8 test modules covered)
- Remaining: test_adapters, test_output, test_pipeline, test_safety, test_cli — not yet reconstructed (T10, T11, T12, T13)

## Diagnostics

- Run `uv run pytest tests/test_ingestion/ -v` to see per-test results for parser, dedup, local, S3
- Run `uv run pytest tests/test_storage/ -v` to see per-test results for writer and queries
- If a test fails, the class/method name identifies exactly which module behavior is broken (e.g., `TestCrossRunDedup::test_duplicate_records_filtered` → storage writer dedup logic)

## Deviations

- S3 tests use `mock_aws()` as context manager instead of decorator (original bytecode shows decorator pattern). Moto 5.1.22's `@mock_aws` wraps async→sync, breaking pytest-asyncio detection. Context manager achieves identical isolation. This is a moto version compatibility adaptation, not a logic change.

## Known Issues

None.

## Files Created/Modified

- `tests/test_ingestion/conftest.py` — 7 fixtures with exact VPC Flow Log v2 sample data
- `tests/test_ingestion/test_parser.py` — 22 parser tests covering valid/malformed/NODATA/SKIPDATA lines
- `tests/test_ingestion/test_dedup.py` — 10 dedup key composition tests (7-field hash, D010)
- `tests/test_ingestion/test_local.py` — 12 async local file ingestion tests
- `tests/test_ingestion/test_s3.py` — 11 S3 ingestion tests with moto mocks (D012)
- `tests/test_storage/conftest.py` — 3 fixtures (5 sample records, data_dir, pre_written_parquet)
- `tests/test_storage/test_writer.py` — 20 Parquet writer tests (schema, metadata, dedup, naming)
- `tests/test_storage/test_queries.py` — 19 DuckDB query tests (top_talkers, denied_flows, traffic_by_protocol, traffic_summary)
- `pyproject.toml` — Added `[tool.pytest.ini_options] asyncio_mode = "auto"` (D036)
