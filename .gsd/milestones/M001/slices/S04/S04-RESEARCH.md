# Phase 4: Storage Layer - Research

**Researched:** 2026-03-09
**Domain:** Parquet file persistence + DuckDB analytics queries
**Confidence:** HIGH

## Summary

Phase 4 persists normalized flow logs (NormalizedFlowLog records from Phase 3) as Parquet files with zstd compression and exposes named analytics functions backed by DuckDB. The core libraries are PyArrow (for Parquet writing) and DuckDB (for querying). Both are mature, well-documented, and fully compatible with Python 3.13.

The main engineering challenges are: (1) mapping Pydantic model fields (especially IPv4Address/IPv6Address and StrEnum types) to PyArrow column types, (2) embedding custom key-value metadata in Parquet files for provenance, (3) implementing cross-run deduplication by querying existing Parquet files before writing, and (4) wrapping synchronous PyArrow/DuckDB calls with asyncio.to_thread to satisfy the project's async I/O requirement.

**Primary recommendation:** Use PyArrow >= 19.0 for Parquet writing with an explicit pa.schema (not inferred), and DuckDB >= 1.4 for glob-pattern queries across all Parquet files in the data directory. Convert NormalizedFlowLog fields to primitive types (strings for IPs, string values for enums) before building the Arrow table.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- One Parquet file per ingestion run, named by timestamp + source hash
- Default data directory: `~/.policyfoundry/data/` (configurable via config.yaml)
- zstd compression (matches roadmap success criteria)
- Embed ingestion metadata (source_files, ingestion_timestamp, record_count) in Parquet file metadata for provenance queries
- Named analytics functions only (no raw SQL passthrough): `top_talkers(n)`, `denied_flows()`, `traffic_by_protocol()`, `traffic_summary()`
- Query results return Pydantic models (TopTalkerResult, TrafficSummary, etc.)
- Per-query DuckDB connections: open, run, close. No persistent connection management
- DuckDB reads all Parquet files in the data directory via glob pattern
- Dedup on write: before writing to Parquet, query existing Parquet files via DuckDB for matching dedup keys
- Store `dedup_hash` as a column in Parquet files (SHA-256, reuses Phase 3's `compute_dedup_key` function)
- Silently skip duplicates + include `cross_run_duplicates_removed` count in write result
- Append-only: new ingestion runs add new Parquet files, never modify existing ones
- No retention/TTL policy for v1
- No file compaction for v1
- Provide a `purge_data()` function to delete all stored Parquet files

### Claude's Discretion
- PyArrow vs fastparquet for Parquet writing implementation
- Exact DuckDB query SQL and optimization
- Pydantic result model field naming and structure
- File naming format details (timestamp precision, hash length)
- Error handling for corrupt Parquet files during reads

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INGEST-05 | Normalized logs are stored as Parquet files and queryable via DuckDB for analytics | PyArrow write_table with zstd compression + DuckDB glob queries provide full implementation path. Cross-run dedup via DuckDB EXISTS check before write. Named analytics functions return Pydantic models. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyarrow | >= 19.0 | Parquet file writing with zstd compression | De facto standard for Parquet in Python. Faster writes than fastparquet, better feature coverage, broader ecosystem support. Required for custom file metadata embedding. PyArrow 23.0.1 is current latest. |
| duckdb | >= 1.4 | Analytics queries against Parquet files | Purpose-built for analytical queries on Parquet. Native glob pattern support, automatic filter pushdown and column pruning. DuckDB 1.5.0 is current latest. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiofiles | >= 25.1.0 | Async file operations (already in project) | Directory creation, file deletion in purge_data() |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyArrow | fastparquet | fastparquet is 180KB vs PyArrow 48MB, but slower writes, no custom file metadata API, less Parquet format coverage. PyArrow is the clear choice for this project. |
| DuckDB | pandas + manual Parquet reads | DuckDB provides SQL analytics, glob patterns, filter pushdown out of the box. Manual reads would require building all of this. |

**Recommendation (Claude's Discretion):** Use PyArrow. It is faster, supports custom key-value metadata embedding (required for provenance), handles zstd compression natively, and DuckDB reads PyArrow-written Parquet files without compatibility issues.

**Installation:**
```bash
uv add pyarrow duckdb
```

**Dev dependency for type stubs:**
```bash
uv add --dev pyarrow-stubs
```

Note: `pyarrow-stubs` provides type annotations for pyright strict mode. DuckDB ships with inline type stubs.

## Architecture Patterns

### Recommended Project Structure
```
src/policyfoundry/storage/
├── __init__.py          # Public API: write_records, query functions, purge_data
├── writer.py            # Parquet writer: schema mapping, metadata, dedup-on-write
├── queries.py           # Named analytics functions: top_talkers, denied_flows, etc.
├── models.py            # Pydantic result models: TopTalkerResult, TrafficSummary, etc.
└── parquet_schema.py    # PyArrow schema definition derived from NormalizedFlowLog
```

### Pattern 1: Pydantic-to-PyArrow Schema Mapping
**What:** Define an explicit PyArrow schema that maps NormalizedFlowLog fields to Arrow types. Do NOT rely on type inference.
**When to use:** Always when writing Parquet files from Pydantic models.
**Why:** IPv4Address, IPv6Address, StrEnum, and Optional fields cannot be auto-inferred by PyArrow. Explicit schema ensures consistent column types across all Parquet files.

```python
import pyarrow as pa

# Explicit schema mapping NormalizedFlowLog fields
FLOW_LOG_SCHEMA = pa.schema([
    pa.field("timestamp", pa.timestamp("us", tz="UTC")),
    pa.field("src_ip", pa.string()),           # IPv4/6Address -> str
    pa.field("dst_ip", pa.string()),           # IPv4/6Address -> str
    pa.field("src_port", pa.int32()),
    pa.field("dst_port", pa.int32()),
    pa.field("protocol", pa.string()),         # StrEnum -> str value
    pa.field("action", pa.string()),           # StrEnum -> str value
    pa.field("bytes_transferred", pa.int64()),
    pa.field("rule_id", pa.string()),          # Optional[str] -> nullable string
    pa.field("app_name", pa.string()),         # Optional[str] -> nullable string
    pa.field("flow_direction", pa.string()),   # StrEnum -> str value
    pa.field("packets_count", pa.int64()),
    pa.field("dedup_hash", pa.string()),       # SHA-256 hex digest (64 chars)
])
```

### Pattern 2: Records to Arrow Table Conversion
**What:** Convert list of NormalizedFlowLog records to a PyArrow Table using column-oriented dict construction.
**When to use:** Before every Parquet write.

```python
import pyarrow as pa
import pyarrow.parquet as pq
from policyfoundry.ingestion.dedup import compute_dedup_key

def records_to_table(
    records: list[NormalizedFlowLog],
) -> pa.Table:
    """Convert NormalizedFlowLog records to a PyArrow Table."""
    columns: dict[str, list] = {field.name: [] for field in FLOW_LOG_SCHEMA}
    for record in records:
        columns["timestamp"].append(record.timestamp)
        columns["src_ip"].append(str(record.src_ip))
        columns["dst_ip"].append(str(record.dst_ip))
        columns["src_port"].append(record.src_port)
        columns["dst_port"].append(record.dst_port)
        columns["protocol"].append(record.protocol.value)
        columns["action"].append(record.action.value)
        columns["bytes_transferred"].append(record.bytes_transferred)
        columns["rule_id"].append(record.rule_id)
        columns["app_name"].append(record.app_name)
        columns["flow_direction"].append(record.flow_direction.value)
        columns["packets_count"].append(record.packets_count)
        columns["dedup_hash"].append(compute_dedup_key(record))
    return pa.table(columns, schema=FLOW_LOG_SCHEMA)
```

### Pattern 3: Parquet File Metadata Embedding
**What:** Attach ingestion provenance as Parquet file-level key-value metadata.
**When to use:** Every Parquet write.

```python
import json

metadata = {
    b"policyfoundry_source_files": json.dumps(source_files).encode(),
    b"policyfoundry_ingestion_timestamp": ingestion_ts.isoformat().encode(),
    b"policyfoundry_record_count": str(record_count).encode(),
}
table = table.replace_schema_metadata({
    **metadata,
    **(table.schema.metadata or {}),
})
pq.write_table(table, file_path, compression="zstd")
```

### Pattern 4: Per-Query DuckDB Connection (User Decision)
**What:** Open a DuckDB in-memory connection, run the query, close it. No persistent connections.
**When to use:** Every analytics query call.
**Tradeoff note:** Per-query connections add overhead vs. reusing a connection. For a CLI tool with infrequent queries, this overhead is negligible. The pattern is simpler and avoids connection lifecycle management.

```python
import duckdb

async def _run_query(sql: str, data_dir: str) -> list[tuple]:
    """Run a DuckDB query against all Parquet files in data_dir."""
    def _execute() -> list[tuple]:
        glob_pattern = f"{data_dir}/*.parquet"
        con = duckdb.connect()
        try:
            result = con.execute(sql, [glob_pattern]).fetchall()
            return result
        finally:
            con.close()
    return await asyncio.to_thread(_execute)
```

### Pattern 5: Async Wrappers via asyncio.to_thread
**What:** Wrap synchronous PyArrow and DuckDB calls with asyncio.to_thread.
**When to use:** All storage I/O operations (project constraint: all I/O must be async).
**Why:** Neither PyArrow nor DuckDB have native async APIs. asyncio.to_thread runs the blocking call on a thread pool executor without blocking the event loop.

```python
import asyncio
import pyarrow.parquet as pq

async def write_parquet_async(table: pa.Table, path: str) -> None:
    await asyncio.to_thread(pq.write_table, table, path, compression="zstd")
```

### Pattern 6: Cross-Run Dedup on Write
**What:** Before writing new records, query existing Parquet files for matching dedup_hash values and filter out duplicates.
**When to use:** Every write operation.

```python
def _get_existing_hashes(data_dir: str, new_hashes: set[str]) -> set[str]:
    """Query existing Parquet files for dedup hashes matching new records."""
    glob_pattern = f"{data_dir}/*.parquet"
    con = duckdb.connect()
    try:
        # Check if any parquet files exist first
        import glob as glob_mod
        if not glob_mod.glob(glob_pattern):
            return set()
        # Use IN clause with the new hashes for efficient filtering
        hash_list = ", ".join(f"'{h}'" for h in new_hashes)
        sql = f"SELECT DISTINCT dedup_hash FROM read_parquet(?) WHERE dedup_hash IN ({hash_list})"
        result = con.execute(sql, [glob_pattern]).fetchall()
        return {row[0] for row in result}
    finally:
        con.close()
```

### Anti-Patterns to Avoid
- **Inferring PyArrow schema from Pydantic model:** PyArrow cannot auto-infer IPv4Address, IPv6Address, or StrEnum types. Always use an explicit schema.
- **Storing IP addresses as binary:** Store as strings for DuckDB query readability and WHERE clause compatibility.
- **Keeping DuckDB connections open across calls:** User decision mandates per-query connections. Even if overhead is higher, consistency with decision is more important.
- **Using pandas as intermediary:** No need for pandas. Convert Pydantic -> dict columns -> pa.Table directly. Avoids unnecessary dependency.
- **Raw SQL passthrough in query functions:** User decision mandates named functions only. All SQL lives inside the query module, never exposed to callers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parquet file format | Custom binary serialization | PyArrow write_table | Parquet is a complex columnar format with row groups, pages, statistics, and compression. |
| Columnar analytics | In-memory aggregation loops | DuckDB SQL queries | DuckDB has vectorized execution, automatic filter pushdown, and column pruning for Parquet. |
| zstd compression | Manual zstd binding | PyArrow compression="zstd" | Built-in, tested, configurable compression level. |
| Parquet metadata | Sidecar metadata files | PyArrow replace_schema_metadata | Parquet natively supports key-value metadata. No separate index file needed. |
| File glob matching | os.walk + filtering | DuckDB read_parquet('*.parquet') | DuckDB natively handles glob patterns with parallel reading. |

**Key insight:** The PyArrow + DuckDB combination handles the entire write-query lifecycle. The storage layer is primarily glue code: converting Pydantic models to Arrow tables and wrapping DuckDB SQL in named Python functions.

## Common Pitfalls

### Pitfall 1: PyArrow Schema Mismatch Across Files
**What goes wrong:** If different ingestion runs produce Parquet files with slightly different schemas (e.g., one file has int32 for a port, another has int64), DuckDB will error when reading them together via glob.
**Why it happens:** Schema inference varies based on data content if not explicitly specified.
**How to avoid:** Always use the same explicit pa.schema for every write. Define it once in parquet_schema.py.
**Warning signs:** DuckDB errors like "Schema mismatch" or "Column type mismatch" when querying.

### Pitfall 2: IPv4/IPv6Address Type Conversion
**What goes wrong:** PyArrow cannot serialize Python ipaddress.IPv4Address or IPv6Address objects directly. Writing fails with a type error.
**Why it happens:** These are not primitive Python types that PyArrow recognizes.
**How to avoid:** Convert to str(record.src_ip) before building the Arrow table. The explicit schema maps these to pa.string().
**Warning signs:** ArrowInvalid or ArrowTypeError during table construction.

### Pitfall 3: StrEnum Value vs Name
**What goes wrong:** Storing StrEnum member names instead of values (e.g., "TCP" vs "ProtocolEnum.TCP").
**Why it happens:** Using str(enum_member) instead of enum_member.value. For StrEnum both are the same, but explicitly using .value is clearer and safer.
**How to avoid:** Always use record.protocol.value, record.action.value, etc.
**Warning signs:** Query results contain "ProtocolEnum.TCP" instead of "TCP".

### Pitfall 4: Empty Data Directory on First Query
**What goes wrong:** DuckDB raises an error when the glob pattern matches zero files (e.g., first run before any data is written).
**Why it happens:** `read_parquet('~/.policyfoundry/data/*.parquet')` fails if no .parquet files exist.
**How to avoid:** Check for existing Parquet files before running DuckDB queries. Return empty results if no files exist.
**Warning signs:** IOException or "No files found" error from DuckDB.

### Pitfall 5: Timestamp Timezone Handling
**What goes wrong:** Timestamps stored without timezone info (naive datetime) are ambiguous when read back. DuckDB treats them as local time by default.
**Why it happens:** NormalizedFlowLog timestamps may or may not have tzinfo depending on the source.
**How to avoid:** Use pa.timestamp("us", tz="UTC") in the schema. Ensure timestamps are UTC-aware before writing. The existing parser produces timestamps from Unix epoch, which should be treated as UTC.
**Warning signs:** Query results show unexpected timestamp shifts.

### Pitfall 6: Large IN Clause for Cross-Run Dedup
**What goes wrong:** If an ingestion run has 100K+ records, building a SQL IN clause with 100K hash values creates an enormous SQL string.
**Why it happens:** Naive dedup implementation puts all new hashes in a single IN clause.
**How to avoid:** Use a temporary DuckDB table to load new hashes, then JOIN against existing Parquet data for dedup. Or batch the IN clause into chunks.
**Warning signs:** Slow query performance, DuckDB parser errors on very large SQL strings.

### Pitfall 7: File Naming Collisions
**What goes wrong:** Two rapid ingestion runs produce files with the same timestamp, causing overwrites.
**Why it happens:** Timestamp precision too coarse (e.g., seconds).
**How to avoid:** Use microsecond-precision timestamps + source hash in filenames. Format: `{iso_timestamp}_{source_hash_8chars}.parquet`.
**Warning signs:** Record counts don't match expectations after multiple runs.

### Pitfall 8: Pyright Strict Mode with PyArrow
**What goes wrong:** PyArrow has incomplete type stubs. Pyright strict mode flags many PyArrow calls as errors.
**Why it happens:** PyArrow's C++ core makes full type annotation difficult.
**How to avoid:** Install pyarrow-stubs (dev dependency). Use type: ignore comments sparingly for known gaps. Use cast() where needed.
**Warning signs:** Pyright errors on pa.table(), pq.write_table(), etc.

## Code Examples

### Complete Parquet Write Flow
```python
# Source: PyArrow official docs + project conventions
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.ingestion.schema import NormalizedFlowLog


async def write_records(
    records: list[NormalizedFlowLog],
    data_dir: Path,
    source_files: list[str],
) -> WriteResult:
    """Write normalized records to a new Parquet file with dedup."""
    data_dir.mkdir(parents=True, exist_ok=True)

    # Compute dedup hashes for all new records
    record_hashes = [(r, compute_dedup_key(r)) for r in records]

    # Cross-run dedup: find existing hashes
    new_hashes = {h for _, h in record_hashes}
    existing = await asyncio.to_thread(
        _get_existing_hashes, str(data_dir), new_hashes
    )
    cross_run_dupes = 0
    unique_records = []
    for record, hash_val in record_hashes:
        if hash_val in existing:
            cross_run_dupes += 1
        else:
            unique_records.append((record, hash_val))

    if not unique_records:
        return WriteResult(
            records_written=0,
            cross_run_duplicates_removed=cross_run_dupes,
            file_path=None,
        )

    # Build Arrow table
    table = _build_table(unique_records)

    # Add provenance metadata
    now = datetime.now(tz=UTC)
    metadata = {
        b"policyfoundry_source_files": json.dumps(source_files).encode(),
        b"policyfoundry_ingestion_timestamp": now.isoformat().encode(),
        b"policyfoundry_record_count": str(len(unique_records)).encode(),
    }
    table = table.replace_schema_metadata({
        **metadata, **(table.schema.metadata or {})
    })

    # Generate filename
    source_hash = hashlib.sha256(
        "|".join(sorted(source_files)).encode()
    ).hexdigest()[:8]
    ts_str = now.strftime("%Y%m%dT%H%M%S%f")
    file_path = data_dir / f"{ts_str}_{source_hash}.parquet"

    # Write with zstd compression
    await asyncio.to_thread(
        pq.write_table, table, str(file_path), compression="zstd"
    )

    return WriteResult(
        records_written=len(unique_records),
        cross_run_duplicates_removed=cross_run_dupes,
        file_path=str(file_path),
    )
```

### DuckDB Analytics Query Example
```python
# Source: DuckDB official docs + project conventions
import asyncio
import duckdb

from policyfoundry.storage.models import TopTalkerResult


async def top_talkers(n: int, data_dir: str) -> list[TopTalkerResult]:
    """Return top N source IPs by total bytes transferred."""
    def _query() -> list[TopTalkerResult]:
        glob_pattern = f"{data_dir}/*.parquet"
        # Check files exist
        import glob as glob_mod
        if not glob_mod.glob(glob_pattern):
            return []

        con = duckdb.connect()
        try:
            rows = con.execute(
                """
                SELECT
                    src_ip,
                    SUM(bytes_transferred) AS total_bytes,
                    COUNT(*) AS flow_count
                FROM read_parquet(?)
                GROUP BY src_ip
                ORDER BY total_bytes DESC
                LIMIT ?
                """,
                [glob_pattern, n],
            ).fetchall()
            return [
                TopTalkerResult(
                    src_ip=row[0],
                    total_bytes=row[1],
                    flow_count=row[2],
                )
                for row in rows
            ]
        finally:
            con.close()

    return await asyncio.to_thread(_query)
```

### Pydantic Result Model Example
```python
# Source: Project convention (Pydantic v2 for all domain models)
from pydantic import BaseModel


class TopTalkerResult(BaseModel):
    """A top talker entry: source IP ranked by bytes transferred."""
    src_ip: str
    total_bytes: int
    flow_count: int


class DeniedFlowResult(BaseModel):
    """A denied flow entry with source, destination, and protocol details."""
    src_ip: str
    dst_ip: str
    dst_port: int
    protocol: str
    deny_count: int


class TrafficByProtocolResult(BaseModel):
    """Traffic breakdown by protocol."""
    protocol: str
    total_bytes: int
    flow_count: int
    percentage: float


class TrafficSummary(BaseModel):
    """Overall traffic summary statistics."""
    total_records: int
    total_bytes: int
    unique_sources: int
    unique_destinations: int
    allowed_count: int
    denied_count: int
    date_range_start: str | None = None
    date_range_end: str | None = None
```

### WriteResult Model
```python
from pydantic import BaseModel


class WriteResult(BaseModel):
    """Result of a Parquet write operation."""
    records_written: int
    cross_run_duplicates_removed: int
    file_path: str | None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| fastparquet for Parquet I/O | PyArrow (dominant) | ~2020 onwards | PyArrow is faster, more features, better maintained |
| DuckDB duckdb.query() | duckdb.connect().execute() | DuckDB 0.9+ | Explicit connection management preferred for parameterized queries |
| Snappy compression default | zstd becoming new default | 2023-2024 | 15-20% better compression, < 1% read speed impact |
| DuckDB filename parameter | Virtual filename column (automatic) | DuckDB 1.3.0 | `filename` column auto-available in read_parquet glob queries |
| Manual union_by_name | Still needed for schema differences | Current | Use consistent schema to avoid needing this |

**Deprecated/outdated:**
- `pq.write_to_dataset()` with partition_cols: Overkill for this use case. Simple write_table per file is sufficient.
- `duckdb.from_parquet_file()`: Older API. Use `con.execute("SELECT ... FROM read_parquet(?)")` with parameterized queries.

## Open Questions

1. **pyarrow-stubs coverage for pyright strict**
   - What we know: pyarrow-stubs exists on PyPI and covers common APIs
   - What's unclear: Whether it covers all APIs used (replace_schema_metadata, write_table with all kwargs)
   - Recommendation: Install and test during implementation. Use targeted `type: ignore` comments for gaps.

2. **DuckDB memory usage with many small Parquet files**
   - What we know: DuckDB defaults to 80% of system RAM. Parquet reading uses column pruning and filter pushdown.
   - What's unclear: At what file count performance degrades (100s? 1000s?)
   - Recommendation: For v1 this is unlikely to be an issue. Add SET memory_limit if needed later. STATE.md already flags this as a research concern.

3. **Cross-run dedup performance at scale**
   - What we know: IN clause with 100K+ values creates large SQL. DuckDB can handle moderate IN clauses efficiently.
   - What's unclear: Exact threshold where temporary table JOIN becomes necessary.
   - Recommendation: Start with IN clause approach (simpler). Add batching or temp table if performance issues emerge. Document the tradeoff.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_storage/ -x -q` |
| Full suite command | `uv run pytest --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-05a | Records written to Parquet with zstd compression | unit | `uv run pytest tests/test_storage/test_writer.py::TestWriteRecords -x` | No -- Wave 0 |
| INGEST-05b | Parquet files contain correct schema and all 12+1 fields | unit | `uv run pytest tests/test_storage/test_writer.py::TestParquetSchema -x` | No -- Wave 0 |
| INGEST-05c | Ingestion metadata embedded in Parquet file metadata | unit | `uv run pytest tests/test_storage/test_writer.py::TestFileMetadata -x` | No -- Wave 0 |
| INGEST-05d | Cross-run dedup removes duplicate records on write | unit | `uv run pytest tests/test_storage/test_writer.py::TestCrossRunDedup -x` | No -- Wave 0 |
| INGEST-05e | top_talkers(n) returns correct results from Parquet | unit | `uv run pytest tests/test_storage/test_queries.py::TestTopTalkers -x` | No -- Wave 0 |
| INGEST-05f | denied_flows() returns correct results from Parquet | unit | `uv run pytest tests/test_storage/test_queries.py::TestDeniedFlows -x` | No -- Wave 0 |
| INGEST-05g | traffic_by_protocol() returns correct results | unit | `uv run pytest tests/test_storage/test_queries.py::TestTrafficByProtocol -x` | No -- Wave 0 |
| INGEST-05h | traffic_summary() returns correct results | unit | `uv run pytest tests/test_storage/test_queries.py::TestTrafficSummary -x` | No -- Wave 0 |
| INGEST-05i | Queries return empty results when no Parquet files exist | unit | `uv run pytest tests/test_storage/test_queries.py::TestEmptyDataDir -x` | No -- Wave 0 |
| INGEST-05j | Queries against multi-MB Parquet files return < 5s | smoke | `uv run pytest tests/test_storage/test_queries.py::TestPerformance -x` | No -- Wave 0 |
| INGEST-05k | purge_data() deletes all Parquet files | unit | `uv run pytest tests/test_storage/test_writer.py::TestPurgeData -x` | No -- Wave 0 |
| INGEST-05l | Corrupt Parquet files handled gracefully | unit | `uv run pytest tests/test_storage/test_queries.py::TestCorruptFiles -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_storage/ -x -q`
- **Per wave merge:** `uv run pytest --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_storage/__init__.py` -- package init
- [ ] `tests/test_storage/conftest.py` -- shared fixtures (tmp_path data dir, sample records, pre-written Parquet files)
- [ ] `tests/test_storage/test_writer.py` -- covers INGEST-05a through 05d, 05k
- [ ] `tests/test_storage/test_queries.py` -- covers INGEST-05e through 05j, 05l
- [ ] Framework install: `uv add pyarrow duckdb` -- required before tests can run

## Sources

### Primary (HIGH confidence)
- [PyArrow Parquet docs](https://arrow.apache.org/docs/python/parquet.html) - write_table API, compression options, metadata embedding
- [PyArrow write_table reference](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html) - Full function signature, zstd support confirmed
- [DuckDB Parquet overview](https://duckdb.org/docs/stable/data/parquet/overview) - Glob patterns, filter pushdown, column pruning, virtual filename column
- [DuckDB Python API](https://duckdb.org/docs/stable/clients/python/overview) - Connection creation, execute, fetchall, result conversion
- [DuckDB Parquet metadata](https://duckdb.org/docs/stable/data/parquet/metadata) - parquet_kv_metadata() for querying provenance
- [PyPI pyarrow](https://pypi.org/project/pyarrow/) - Version 23.0.1 current, Python 3.13 compatible
- [PyPI duckdb](https://pypi.org/project/duckdb/) - Version 1.5.0 current, Python 3.13 compatible

### Secondary (MEDIUM confidence)
- [DuckDB memory management](https://duckdb.org/2024/07/09/memory-management) - Default 80% RAM, SET memory_limit configuration
- [PyArrow custom metadata guide](https://www.mungingdata.com/pyarrow/arbitrary-metadata-parquet-table/) - replace_schema_metadata pattern verified against official docs
- [ZSTD compression levels](https://medium.com/@vincent_daniel/optimizing-parquet-compression-in-apache-iceberg-why-zstd-is-the-smart-default-4c777e6a114c) - Default level 3, range 1-22, recommended 3-9

### Tertiary (LOW confidence)
- [pyarrow-stubs availability](https://pypi.org/project/pyarrow/) - Exists on PyPI but coverage completeness unverified
- [PyArrow async pattern](https://github.com/apache/arrow/issues/3151) - No native async; asyncio.to_thread is community-standard pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyArrow and DuckDB are the de facto standard for this use case, versions verified on PyPI
- Architecture: HIGH - Patterns derived from official docs and verified against project conventions
- Pitfalls: HIGH - Most pitfalls documented from official docs and known type system limitations
- Validation: HIGH - Test structure follows established project patterns

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable libraries, 30-day window)