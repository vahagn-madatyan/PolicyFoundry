# S04: Storage Layer

**Goal:** Implement the storage layer: Parquet file persistence with zstd compression, cross-run deduplication, and DuckDB-backed named analytics query functions.
**Demo:** Implement the storage layer: Parquet file persistence with zstd compression, cross-run deduplication, and DuckDB-backed named analytics query functions.

## Must-Haves


## Tasks

- [x] **T01: 04-storage-layer 01** `est:8min`
  - Implement the storage layer: Parquet file persistence with zstd compression, cross-run deduplication, and DuckDB-backed named analytics query functions.

Purpose: Enables persisting ingested flow logs and querying them for traffic analysis -- the foundation for Pipeline Stage 1 (Analyze) which needs pre-aggregated traffic statistics.

Output: Working async write_records, purge_data, top_talkers, denied_flows, traffic_by_protocol, traffic_summary functions with full test coverage.

## Files Likely Touched

- `pyproject.toml`
- `src/policyfoundry/storage/__init__.py`
- `src/policyfoundry/storage/models.py`
- `src/policyfoundry/storage/parquet_schema.py`
- `src/policyfoundry/storage/writer.py`
- `src/policyfoundry/storage/queries.py`
- `src/policyfoundry/config/models.py`
- `tests/test_storage/__init__.py`
- `tests/test_storage/conftest.py`
- `tests/test_storage/test_writer.py`
- `tests/test_storage/test_queries.py`
