# S03: Log Ingestion

**Goal:** Implement VPC Flow Log v2 parser, IngestionResult model, deduplication logic, and local file ingestion with async I/O.
**Demo:** Implement VPC Flow Log v2 parser, IngestionResult model, deduplication logic, and local file ingestion with async I/O.

## Must-Haves


## Tasks

- [x] **T01: 03-log-ingestion 01** `est:5min`
  - Implement VPC Flow Log v2 parser, IngestionResult model, deduplication logic, and local file ingestion with async I/O.

Purpose: This is the core data ingestion pipeline for local files. Users point the tool at VPC Flow Log files on disk and get back normalized, deduplicated flow records with full ingestion metadata.

Output: Working local file parser producing NormalizedFlowLog records, with IngestionResult tracking stats, dedup removing duplicates, and malformed lines producing warnings rather than crashes.
- [x] **T02: 03-log-ingestion 02** `est:6min`
  - Implement S3-based VPC Flow Log ingestion with prefix scanning, gzip decompression, and deduplication using aioboto3.

Purpose: Users need to ingest VPC Flow Logs directly from S3 buckets where AWS delivers them. This extends the local ingestion from Plan 01 to support the full S3 workflow: prefix scan to discover objects, streaming reads, transparent gzip decompression, and the same parsing/dedup pipeline.

Output: Working S3 ingestion function producing the same IngestionResult as local ingestion, with moto-based integration tests proving the full S3 flow.

## Files Likely Touched

- `pyproject.toml`
- `src/policyfoundry/ingestion/__init__.py`
- `src/policyfoundry/ingestion/parser.py`
- `src/policyfoundry/ingestion/result.py`
- `src/policyfoundry/ingestion/dedup.py`
- `src/policyfoundry/ingestion/local.py`
- `src/policyfoundry/exceptions.py`
- `tests/test_ingestion/__init__.py`
- `tests/test_ingestion/conftest.py`
- `tests/test_ingestion/test_parser.py`
- `tests/test_ingestion/test_dedup.py`
- `tests/test_ingestion/test_local.py`
- `pyproject.toml`
- `src/policyfoundry/ingestion/s3.py`
- `src/policyfoundry/ingestion/__init__.py`
- `tests/test_ingestion/conftest.py`
- `tests/test_ingestion/test_s3.py`
