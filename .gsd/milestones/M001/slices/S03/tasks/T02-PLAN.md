# T02: 03-log-ingestion 02

**Slice:** S03 — **Milestone:** M001

## Description

Implement S3-based VPC Flow Log ingestion with prefix scanning, gzip decompression, and deduplication using aioboto3.

Purpose: Users need to ingest VPC Flow Logs directly from S3 buckets where AWS delivers them. This extends the local ingestion from Plan 01 to support the full S3 workflow: prefix scan to discover objects, streaming reads, transparent gzip decompression, and the same parsing/dedup pipeline.

Output: Working S3 ingestion function producing the same IngestionResult as local ingestion, with moto-based integration tests proving the full S3 flow.

## Must-Haves

- [ ] "User can parse VPC Flow Logs from an S3 bucket (given valid AWS credentials) and see normalized records identical in format to local file output"
- [ ] "S3 prefix scan discovers all objects under a given prefix, handling pagination beyond 1000 objects"
- [ ] "Gzip-compressed S3 objects (.gz extension) are decompressed transparently"
- [ ] "Duplicate records within an S3 ingestion run are deduplicated"
- [ ] "S3 access errors (bucket not found, permission denied) skip the problematic object and continue with remaining objects"
- [ ] "AWS credentials are resolved via boto3 default chain, honoring SourcesConfig.aws_profile if set"

## Files

- `pyproject.toml`
- `src/policyfoundry/ingestion/s3.py`
- `src/policyfoundry/ingestion/__init__.py`
- `tests/test_ingestion/conftest.py`
- `tests/test_ingestion/test_s3.py`
