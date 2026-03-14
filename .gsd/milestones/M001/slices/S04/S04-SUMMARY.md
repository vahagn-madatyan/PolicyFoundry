---
id: S04
parent: M001
milestone: M001
provides:
  - Parquet file persistence with zstd compression and embedded provenance metadata
  - Cross-run deduplication via DuckDB hash comparison on write
  - Named analytics functions (top_talkers, denied_flows, traffic_by_protocol, traffic_summary)
  - Pydantic result models for all query and write operations
  - purge_data function for data lifecycle management
requires: []
affects: []
key_files: []
key_decisions:
  - "Used pytz runtime dependency for DuckDB timestamp handling (DuckDB requires it for timezone-aware timestamps)"
  - "Per-query DuckDB connections (open, run, close) -- no persistent connection management per CONTEXT.md"
  - "Cross-run dedup uses IN clause for <= 1000 hashes, temporary table + JOIN for larger sets"
  - "Parquet filename format: YYYYMMDDTHHMMSSffffff_{8charhash}.parquet (microsecond precision prevents collisions)"
patterns_established:
  - "Explicit PyArrow schema (FLOW_LOG_SCHEMA) for all Parquet writes -- never infer schema"
  - "asyncio.to_thread wrapping for all synchronous PyArrow/DuckDB I/O"
  - "type: ignore comments for pyarrow-stubs gaps in pyright strict mode"
  - "Empty directory check before DuckDB glob queries to prevent IOException"
observability_surfaces: []
drill_down_paths: []
duration: 8min
verification_result: passed
completed_at: 2026-03-09
blocker_discovered: false
---
# S04: Storage Layer

**# Phase 4 Plan 1: Storage Layer Summary**

## What Happened

# Phase 4 Plan 1: Storage Layer Summary

**Parquet persistence with zstd compression, cross-run deduplication via DuckDB, and four named analytics query functions returning Pydantic result models**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-09T20:08:15Z
- **Completed:** 2026-03-09T20:16:10Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Parquet file writer with zstd compression, explicit 13-column schema, and embedded provenance metadata (source files, timestamp, record count)
- Cross-run deduplication that queries existing Parquet files for matching dedup hashes before writing, with optimized large-set handling
- Four DuckDB-backed analytics functions: top_talkers, denied_flows, traffic_by_protocol, traffic_summary -- all returning typed Pydantic models
- Graceful handling of empty data directories and corrupt Parquet files in all query functions
- Full TDD test coverage: 39 tests (18 writer + 21 queries) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Parquet writer with result models, schema, cross-run dedup, and purge** - `d9bd3fd` (feat)
2. **Task 2: DuckDB analytics query functions and storage public API** - `bcd3742` (feat)

_Both tasks used TDD: tests written first (RED), then implementation (GREEN)._

## Files Created/Modified
- `src/policyfoundry/storage/models.py` - Pydantic result models (WriteResult, TopTalkerResult, DeniedFlowResult, TrafficByProtocolResult, TrafficSummary)
- `src/policyfoundry/storage/parquet_schema.py` - Explicit PyArrow schema mapping all 12 NormalizedFlowLog fields + dedup_hash
- `src/policyfoundry/storage/writer.py` - Async write_records with cross-run dedup, purge_data
- `src/policyfoundry/storage/queries.py` - top_talkers, denied_flows, traffic_by_protocol, traffic_summary
- `src/policyfoundry/storage/__init__.py` - Public API re-exports for all storage functions and models
- `src/policyfoundry/config/models.py` - Added data_dir field to OutputConfig
- `pyproject.toml` - Added pyarrow, duckdb, pytz dependencies; pyarrow-stubs dev dependency
- `tests/test_storage/conftest.py` - Shared fixtures: sample_records, data_dir, pre_written_parquet
- `tests/test_storage/test_writer.py` - Writer, schema, metadata, dedup, purge, naming tests
- `tests/test_storage/test_queries.py` - All four analytics functions + empty dir + corrupt file tests

## Decisions Made
- Used pytz as a runtime dependency because DuckDB requires it for timezone-aware Parquet timestamp operations (was missing from environment)
- Followed per-query DuckDB connection pattern as specified in CONTEXT.md -- no persistent connections
- Cross-run dedup uses direct IN clause for small hash sets and temporary table + JOIN for sets > 1000 to avoid Pitfall 6
- File naming uses microsecond precision (YYYYMMDDTHHMMSSffffff) to prevent collision between rapid runs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing pytz dependency for DuckDB timestamp operations**
- **Found during:** Task 2 (DuckDB analytics queries)
- **Issue:** DuckDB throws InvalidInputException when querying timestamp columns without pytz installed
- **Fix:** Added pytz as runtime dependency via `uv add pytz`
- **Files modified:** pyproject.toml, uv.lock
- **Verification:** All timestamp-aware queries (traffic_summary date range) now work correctly
- **Committed in:** bcd3742 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency)
**Impact on plan:** Essential for DuckDB timestamp handling. No scope creep.

## Issues Encountered
None beyond the pytz dependency.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Storage layer is fully operational with write, query, and purge capabilities
- Pipeline Stage 1 (Phase 7) can call analytics functions for traffic pattern analysis
- CLI (Phase 9) can expose purge_data and data summary commands
- DuckDB memory with large Parquet file counts remains a deferred concern (documented in STATE.md)

## Self-Check: PASSED

All 10 files verified present. Both task commits (d9bd3fd, bcd3742) confirmed in git log.

---
*Phase: 04-storage-layer*
*Completed: 2026-03-09*
