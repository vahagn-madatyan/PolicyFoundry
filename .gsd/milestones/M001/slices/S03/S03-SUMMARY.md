---
id: S03
parent: M001
milestone: M001
provides:
  - "parse_vpc_flow_log_line: VPC Flow Log v2 line parser (pure function)"
  - "compute_dedup_key: SHA-256 deduplication on 7-field composite key"
  - "ingest_local_files: async local file ingestion with glob expansion"
  - "IngestionResult: Pydantic model with records, stats, and warnings"
  - "ParseError, S3AccessError exception subclasses"
  - "ingest_from_s3: async S3 ingestion with prefix scan, gzip decompression, dedup"
requires: []
affects: []
key_files: []
key_decisions:
  - "parse_vpc_flow_log_line is a pure function that never raises -- returns None on any failure"
  - "NODATA/SKIPDATA lines are silently skipped (not counted as errors) since they are AWS metadata"
  - "Dedup key uses 7 fields (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action) -- excludes bytes_transferred and packets_count"
  - "flow_direction defaults to INBOUND for all v2 lines (v2 format lacks direction info)"
  - "Non-version-2 lines log warning but still attempt parse (graceful degradation)"
  - "Used boto3 + asyncio.to_thread instead of aioboto3 due to moto/aiobotocore version incompatibility"
  - "S3 access errors (bucket not found, permission denied) produce warnings and partial results, never crash"
  - "Source files tracked as s3://bucket/key format for consistent provenance"
patterns_established:
  - "Pure function parser: never raises, returns None on failure, caller decides how to handle"
  - "Sentinel handling: AWS '-' maps to 0 for numeric fields, None for optional string fields"
  - "Async ingestion: aiofiles for non-blocking file I/O with line-by-line streaming"
  - "Dedup pattern: SHA-256 hash of pipe-delimited composite key, checked against seen-set"
  - "boto3 + asyncio.to_thread: sync SDK wrapped for async compatibility and testability with moto"
  - "Graceful S3 error handling: ClientError caught at both object and bucket level, warnings collected"
  - "Shared dedup pattern: same seen-hashes set used across all S3 objects in one ingestion run"
observability_surfaces: []
drill_down_paths: []
duration: 6min
verification_result: passed
completed_at: 2026-03-08
blocker_discovered: false
---
# S03: Log Ingestion

**# Phase 3 Plan 1: Log Ingestion Core Summary**

## What Happened

# Phase 3 Plan 1: Log Ingestion Core Summary

**VPC Flow Log v2 parser with async local file ingestion, SHA-256 deduplication, and IngestionResult tracking**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-09T05:32:58Z
- **Completed:** 2026-03-09T05:37:50Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- VPC Flow Log v2 parser handling all field mappings (IANA protocols, action codes, sentinel values, timestamps)
- Async local file ingestion with glob expansion, missing-file resilience, and malformed-line warnings
- SHA-256 deduplication using 7-field composite key removes duplicates within an ingestion run
- IngestionResult Pydantic model tracks records, total_lines, duplicates_removed, errors_skipped, source_files, and warnings
- 43 ingestion-specific tests (120 total), pyright strict clean, ruff lint clean

## Task Commits

Each task was committed atomically:

1. **Task 1: VPC Flow Log parser, IngestionResult model, dedup, and test scaffolding**
   - `e39f426` (test: RED -- failing tests for parser, dedup, result)
   - `3bc1833` (feat: GREEN -- parser, dedup, result implementation)
2. **Task 2: Local file ingestion with async I/O, glob expansion, and deduplication**
   - `7791832` (test: RED -- failing tests for local ingestion)
   - `9b2736e` (feat: GREEN -- local ingestion implementation)

_TDD tasks each have RED + GREEN commits._

## Files Created/Modified
- `src/policyfoundry/ingestion/parser.py` - VPC Flow Log v2 line parser (pure function, never raises)
- `src/policyfoundry/ingestion/result.py` - IngestionResult Pydantic model with records and stats
- `src/policyfoundry/ingestion/dedup.py` - SHA-256 dedup key computation on 7-field composite
- `src/policyfoundry/ingestion/local.py` - Async local file ingestion with glob expansion
- `src/policyfoundry/ingestion/__init__.py` - Public API exports
- `src/policyfoundry/exceptions.py` - Added ParseError, S3AccessError subclasses
- `pyproject.toml` - Added aiofiles, pytest-asyncio, asyncio_mode=auto
- `tests/test_ingestion/conftest.py` - Shared fixtures (valid/header/nodata/skipdata/malformed lines)
- `tests/test_ingestion/test_parser.py` - 20 parser tests covering all field mappings and edge cases
- `tests/test_ingestion/test_dedup.py` - 10 dedup tests for consistency and collision resistance
- `tests/test_ingestion/test_local.py` - 13 integration tests for local ingestion

## Decisions Made
- parse_vpc_flow_log_line is a pure function that never raises -- returns None on any failure
- NODATA/SKIPDATA lines are silently skipped (not counted as errors) since they are AWS metadata
- Dedup key uses 7 fields (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action) -- excludes bytes_transferred and packets_count
- flow_direction defaults to INBOUND for all v2 lines (v2 format lacks direction info)
- Non-version-2 lines log warning but still attempt parse (graceful degradation)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Local file ingestion pipeline complete and tested end-to-end
- Parser, dedup, and IngestionResult ready for S3 ingestion (Plan 02) to reuse
- All public APIs exported from ingestion __init__.py for downstream consumers

## Self-Check: PASSED

All 12 files verified present. All 4 commits verified in git history.

---
*Phase: 03-log-ingestion*
*Completed: 2026-03-08*

# Phase 3 Plan 2: S3 Ingestion Summary

**S3 VPC Flow Log ingestion with prefix scanning, transparent gzip decompression, and cross-object deduplication using boto3**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-09T05:41:40Z
- **Completed:** 2026-03-09T05:48:03Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- S3 prefix scanning via boto3 paginator discovers all VPC Flow Log objects under a given prefix
- Transparent gzip decompression for .gz extension objects with BadGzipFile error handling
- Cross-object deduplication using shared seen-hashes set within a single ingestion run
- Graceful S3 access error handling: bucket not found and permission denied produce warnings, never crash
- aws_profile forwarded to boto3.Session for AWS credential chain support
- 12 new moto-based S3 tests, 132 total tests passing, pyright strict clean, ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: S3 ingestion with prefix scan, gzip decompression, and moto tests**
   - `663378e` (test: RED -- failing tests for S3 ingestion)
   - `bba8ad9` (feat: GREEN -- S3 ingestion implementation)

_TDD task has RED + GREEN commits._

## Files Created/Modified
- `src/policyfoundry/ingestion/s3.py` - Async S3 ingestion with prefix scan, streaming, gzip support
- `tests/test_ingestion/test_s3.py` - 12 moto-based tests covering all S3 ingestion behaviors
- `src/policyfoundry/ingestion/__init__.py` - Added ingest_from_s3 export
- `pyproject.toml` - Added boto3, moto[s3], boto3-stubs[s3] dependencies

## Decisions Made
- Used boto3 + asyncio.to_thread instead of aioboto3 due to moto/aiobotocore version incompatibility (aiobotocore 2.25.1 fails with moto 5.1.22 on async response body handling). boto3 wrapped in asyncio.to_thread provides the same async public API with full moto test compatibility.
- S3 access errors at both bucket and object level caught separately -- bucket-level errors abort the run with warning, object-level errors skip the problematic object and continue with remaining objects.
- Source files tracked as s3://bucket/key URI format for consistent provenance with local file paths.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Switched from aioboto3 to boto3 + asyncio.to_thread**
- **Found during:** Task 1 (TDD RED/GREEN)
- **Issue:** moto 5.1.22 and aiobotocore 2.25.1 are incompatible -- aiobotocore's async endpoint handler tries to `await` on synchronous bytes returned by moto's response mock, causing `TypeError: object bytes can't be used in 'await' expression`
- **Fix:** Replaced aioboto3 with boto3, wrapped S3 I/O calls in `asyncio.to_thread()` to maintain async public API. Removed aioboto3 dependency, added boto3 as direct dependency, added boto3-stubs[s3] for pyright typing.
- **Files modified:** src/policyfoundry/ingestion/s3.py, pyproject.toml, uv.lock
- **Verification:** All 12 S3 tests pass with moto mock_aws, pyright strict clean
- **Committed in:** bba8ad9 (GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary change for test infrastructure compatibility. Public API identical (async function returning IngestionResult). No scope creep.

## Issues Encountered
- moto + aiobotocore compatibility: aiobotocore 2.25.1 cannot be used with moto 5.1.22 for testing. Resolved by using boto3 (sync) with asyncio.to_thread wrapper.

## User Setup Required
None - no external service configuration required. AWS credentials resolved via boto3 default chain at runtime.

## Next Phase Readiness
- Full ingestion pipeline complete: local files (Plan 01) and S3 (Plan 02)
- Both produce identical IngestionResult format -- downstream consumers don't need to know the source
- All 4 phase requirements (INGEST-01 through INGEST-04) covered across Plans 01 and 02
- Parser, dedup, result, and both ingestion functions exported from ingestion __init__.py

## Self-Check: PASSED
