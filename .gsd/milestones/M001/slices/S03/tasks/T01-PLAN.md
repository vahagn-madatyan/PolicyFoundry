# T01: 03-log-ingestion 01

**Slice:** S03 — **Milestone:** M001

## Description

Implement VPC Flow Log v2 parser, IngestionResult model, deduplication logic, and local file ingestion with async I/O.

Purpose: This is the core data ingestion pipeline for local files. Users point the tool at VPC Flow Log files on disk and get back normalized, deduplicated flow records with full ingestion metadata.

Output: Working local file parser producing NormalizedFlowLog records, with IngestionResult tracking stats, dedup removing duplicates, and malformed lines producing warnings rather than crashes.

## Must-Haves

- [ ] "User can parse a local VPC Flow Log file and see normalized records with all 12 NormalizedFlowLog fields populated"
- [ ] "Malformed log lines are skipped with a warning message identifying the line number and content snippet (not a crash)"
- [ ] "Duplicate records within a single ingestion run are deduplicated so each flow appears exactly once"
- [ ] "IANA protocol numbers (6, 17, 1) map correctly to ProtocolEnum (TCP, UDP, ICMP)"
- [ ] "VPC ACCEPT/REJECT map correctly to ActionEnum ALLOW/DENY"
- [ ] "AWS sentinel values ('-', 'NODATA') map to None or 0 appropriately"
- [ ] "IngestionResult provides total_lines, duplicates_removed, errors_skipped, source_files, and warnings"

## Files

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
