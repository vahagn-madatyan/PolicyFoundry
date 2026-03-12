---
estimated_steps: 4
estimated_files: 8
---

# T09: Reconstruct test files — ingestion, storage

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the ingestion and storage test files. These are medium-to-large test modules: ingestion tests verify flow log parsing, deduplication, local file reading, and S3 access (with moto mocks). Storage tests verify Parquet writing and DuckDB query functions. The ingestion parser test is particularly large (41KB pyc) with many edge cases for malformed log lines.

## Steps

1. **Reconstruct ingestion test fixtures** — `test_ingestion/conftest.py` with sample flow log lines, temporary directories, and fixture data for parser testing.

2. **Reconstruct ingestion tests** — `test_ingestion/test_parser.py` (largest — 41KB pyc, tests parse_flow_log_line with valid/invalid/NODATA/SKIPDATA lines per D008, D009), `test_dedup.py` (dedup key composition per D010), `test_local.py` (async local file ingestion), `test_s3.py` (S3 ingestion with moto mocks per D012).

3. **Reconstruct storage tests** — `test_storage/conftest.py` (fixtures with tmp_path for Parquet files, sample records), `test_queries.py` (DuckDB queries — 43KB pyc, tests top_talkers, traffic_summary, denied_flows, traffic_by_protocol), `test_writer.py` (Parquet writing — 41KB pyc, tests zstd compression, file naming per D014).

4. **Run all tests** and fix reconstruction issues — `uv run pytest tests/test_ingestion/ tests/test_storage/ -x -v`.

## Must-Haves

- [ ] Parser tests cover valid v2 lines, malformed lines (return None per D008), NODATA/SKIPDATA (D009)
- [ ] Dedup tests verify 7-field key composition (D010)
- [ ] Local ingestion tests are async (pytest-asyncio)
- [ ] S3 tests use moto mocks (D012)
- [ ] Storage tests verify Parquet round-trip and DuckDB queries
- [ ] All tests in these modules pass

## Verification

- `uv run pytest tests/test_ingestion/ -x -v 2>&1 | tail -5` → all pass
- `uv run pytest tests/test_storage/ -x -v 2>&1 | tail -5` → all pass

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: Run specific test module to isolate failures
- Failure state exposed: Pytest verbose output shows per-test pass/fail

## Inputs

- `tests/test_ingestion/__pycache__/*.pyc` (conftest + 4 tests, 3–41KB)
- `tests/test_storage/__pycache__/*.pyc` (conftest + 2 tests, 5.5–43KB)
- Reconstructed src files from T02–T07 (ingestion + storage modules)
- `tools/inspect_pyc.py` from T01

## Expected Output

- `tests/test_ingestion/conftest.py`, `test_parser.py`, `test_dedup.py`, `test_local.py`, `test_s3.py`
- `tests/test_storage/conftest.py`, `test_queries.py`, `test_writer.py`
- Test results: all pass in both modules
