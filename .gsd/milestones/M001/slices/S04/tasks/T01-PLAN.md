# T01: 04-storage-layer 01

**Slice:** S04 — **Milestone:** M001

## Description

Implement the storage layer: Parquet file persistence with zstd compression, cross-run deduplication, and DuckDB-backed named analytics query functions.

Purpose: Enables persisting ingested flow logs and querying them for traffic analysis -- the foundation for Pipeline Stage 1 (Analyze) which needs pre-aggregated traffic statistics.

Output: Working async write_records, purge_data, top_talkers, denied_flows, traffic_by_protocol, traffic_summary functions with full test coverage.

## Must-Haves

- [ ] "Normalized flow logs are written to Parquet files with zstd compression"
- [ ] "Parquet files contain all 12 NormalizedFlowLog fields plus dedup_hash column"
- [ ] "Ingestion metadata (source_files, timestamp, record_count) is embedded in Parquet file metadata"
- [ ] "Cross-run deduplication removes records already stored in existing Parquet files"
- [ ] "top_talkers(n) returns top N source IPs by total bytes"
- [ ] "denied_flows() returns denied flow records grouped by src/dst/port/protocol"
- [ ] "traffic_by_protocol() returns traffic breakdown by protocol with percentages"
- [ ] "traffic_summary() returns overall stats (totals, uniques, date range)"
- [ ] "Queries return empty results when no Parquet files exist (no crash)"
- [ ] "purge_data() deletes all stored Parquet files"

## Files

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
