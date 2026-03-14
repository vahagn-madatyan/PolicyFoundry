# Phase 3: Log Ingestion - Research

**Researched:** 2026-03-08
**Domain:** AWS VPC Flow Log parsing, S3 streaming, async I/O, deduplication
**Confidence:** HIGH

## Summary

Phase 3 implements VPC Flow Log ingestion from local files and S3, normalizing records to the existing 12-field `NormalizedFlowLog` Pydantic model. The VPC v2 default format is a 14-column space-delimited text format with IANA protocol numbers and Unix epoch timestamps. The parser must map these 14 fields to the 12-field schema, handle AWS sentinel values (`-`, `NODATA`, `SKIPDATA`), and skip malformed lines with actionable warnings. S3 ingestion streams objects line-by-line via `aioboto3` to avoid full downloads to disk, with transparent gzip decompression based on file extension.

The core challenge is clean mapping between VPC log semantics and the `NormalizedFlowLog` schema: IANA protocol numbers (6, 17, 1) must map to `ProtocolEnum` strings, VPC `ACCEPT`/`REJECT` must map to `ActionEnum` values (noting `REJECT` maps to `DENY`), and the `flow_direction` field has no VPC v2 equivalent (must default or be inferred). Deduplication uses an in-memory hash set of the 7-field dedup key per ingestion run.

**Primary recommendation:** Use `aioboto3` for async S3 streaming (the project mandates async I/O) and `aiofiles` for async local file reads. Keep the parser as a pure function that takes a line and returns `NormalizedFlowLog | None`, making it independently testable. Use `moto[s3]` for S3 integration tests.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Support v2 default format only (14-column space-delimited text)
- Text format only -- no Parquet-format VPC Flow Log input
- Drop extra VPC fields (vpc-id, subnet-id, interface-id) silently -- NormalizedFlowLog's 12 fields are the contract
- Map AWS sentinels ('-', 'NODATA') to None for optional fields, 0 for numeric fields (ports, bytes, packets)
- Validate version field: warn on non-v2 but still attempt parsing (graceful degradation)
- Prefix scan: user provides s3_bucket + s3_prefix via SourcesConfig, tool lists all objects under that prefix
- Auto-detect compression by file extension: .gz files decompressed transparently, plain text read directly
- Stream line-by-line from S3 using boto3 streaming body -- no full file download to disk
- AWS credentials via boto3 default chain (env vars -> ~/.aws/credentials -> IAM role), honoring SourcesConfig.aws_profile if set
- Dedup key: hash of (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action) -- the 5-tuple + timestamp + action
- In-memory per batch: deduplicate within each ingestion run using a set of hashes; cross-run dedup deferred to Phase 4
- Summary count only: log once at end ("Deduplicated N records from M total")
- IngestionResult dataclass with .records, .total_lines, .duplicates_removed, .errors_skipped, .source_files
- No error threshold -- always continue, never abort on malformed lines
- Warn for every malformed line: line number, content snippet, and parse error reason
- File-level errors (not found, permission denied, S3 access denied): skip that file, continue with remaining, track in IngestionResult
- Warn on version mismatch but attempt parsing anyway

### Claude's Discretion
- Exact async implementation patterns (aiofiles, aioboto3, or sync boto3 in thread pool)
- Line parsing implementation details and field mapping logic
- IngestionResult field naming and Pydantic vs dataclass choice
- Logging framework usage (structlog, stdlib logging, or Rich console)
- Local file glob expansion implementation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INGEST-01 | User can parse AWS VPC Flow Logs from local files | VPC v2 format documented with 14-column layout; aiofiles for async reads; glob expansion via pathlib |
| INGEST-02 | User can parse AWS VPC Flow Logs from S3 buckets via boto3 | aioboto3 streaming with iter_lines(); prefix scan via list_objects_v2; gzip auto-detect by extension |
| INGEST-03 | Parsed logs are normalized to unified schema | Field mapping documented: IANA protocol numbers, ACCEPT/REJECT -> ActionEnum, Unix epoch -> datetime, sentinel handling |
| INGEST-04 | Malformed log lines skipped with warnings; duplicates deduplicated | In-memory hash set dedup on 7-field key; per-line error capture with line number and snippet |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aioboto3 | >=13.0 | Async S3 client for streaming reads | Native async boto3 wrapper; project mandates async I/O; supports iter_lines() for line streaming |
| aiofiles | >=24.1 | Async local file I/O | Thread-pool-backed async file reads; supports `async for line in f` iteration |
| moto[s3] | >=5.0 | S3 mock for testing | Standard AWS mocking library; works with aioboto3 via mock_aws context manager |
| pytest-asyncio | >=0.24 | Async test support | Required for testing async ingestion functions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| types-aiobotocore[s3] | latest | Type stubs for S3 client | Pyright strict mode compliance |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aioboto3 | sync boto3 + asyncio.to_thread | Simpler dependency but loses streaming; must download full object to thread then parse |
| aiofiles | asyncio.to_thread(open(...).read) | No extra dependency but loses line-by-line async iteration |
| moto | pytest-aioboto3 + aiomoto | More specialized but niche; moto 5.x mock_aws works with aioboto3 directly |

**Installation:**
```bash
uv add aioboto3 aiofiles
uv add --group dev "moto[s3]" pytest-asyncio types-aiobotocore[s3]
```

## Architecture Patterns

### Recommended Project Structure
```
src/policyfoundry/ingestion/
    __init__.py          # exports: ingest_logs, IngestionResult
    schema.py            # NormalizedFlowLog (exists)
    parser.py            # VPC Flow Log line parser (pure function)
    local.py             # Local file ingestion (aiofiles)
    s3.py                # S3 ingestion (aioboto3)
    dedup.py             # Deduplication logic
    result.py            # IngestionResult model
tests/test_ingestion/
    __init__.py
    conftest.py          # Shared fixtures: sample VPC log lines, mock S3 setup
    test_parser.py       # Unit tests for line parsing
    test_local.py        # Local file ingestion tests
    test_s3.py           # S3 ingestion tests (moto)
    test_dedup.py        # Deduplication tests
```

### Pattern 1: Pure Line Parser Function
**What:** A stateless function that takes a single VPC Flow Log line (string) and returns `NormalizedFlowLog | None` with structured error info on failure.
**When to use:** Every log line from any source (local or S3).
**Example:**
```python
# Source: AWS VPC Flow Log documentation + NormalizedFlowLog schema

import hashlib
from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address

from policyfoundry.ingestion.schema import (
    ActionEnum,
    FlowDirection,
    NormalizedFlowLog,
    ProtocolEnum,
)

# VPC v2 default format: 14 space-delimited columns
# version account-id interface-id srcaddr dstaddr srcport dstport
# protocol packets bytes start end action log-status
VPC_V2_FIELD_COUNT = 14

# IANA protocol number -> ProtocolEnum
PROTOCOL_MAP: dict[int, ProtocolEnum] = {
    1: ProtocolEnum.ICMP,
    6: ProtocolEnum.TCP,
    17: ProtocolEnum.UDP,
}

# VPC action -> ActionEnum
ACTION_MAP: dict[str, ActionEnum] = {
    "ACCEPT": ActionEnum.ALLOW,
    "REJECT": ActionEnum.DENY,
}


def parse_vpc_flow_log_line(
    line: str,
    *,
    line_number: int,
    file_path: str,
) -> NormalizedFlowLog | None:
    """Parse a single VPC Flow Log v2 line into NormalizedFlowLog.

    Returns None if the line is malformed (caller handles warning).
    """
    ...
```

### Pattern 2: Async Generator for Streaming Ingestion
**What:** Async generator that yields `NormalizedFlowLog` records one at a time, allowing the caller to accumulate or process incrementally.
**When to use:** Both local and S3 ingestion paths.
**Example:**
```python
import aiofiles
from collections.abc import AsyncIterator

async def stream_local_file(
    file_path: str,
) -> AsyncIterator[NormalizedFlowLog | tuple[int, str, str]]:
    """Yield parsed records or (line_number, snippet, error) tuples."""
    async with aiofiles.open(file_path, mode="r") as f:
        line_number = 0
        async for line in f:
            line_number += 1
            stripped = line.strip()
            if not stripped or stripped.startswith("version"):
                continue  # skip empty lines and header
            result = parse_vpc_flow_log_line(
                stripped, line_number=line_number, file_path=file_path
            )
            if result is not None:
                yield result
            else:
                yield (line_number, stripped[:80], "parse error")
```

### Pattern 3: IngestionResult as Pydantic Model
**What:** Use Pydantic BaseModel (not dataclass) for IngestionResult, consistent with project convention.
**When to use:** Return type from all ingestion functions.
**Example:**
```python
from pydantic import BaseModel, Field

class IngestionResult(BaseModel):
    """Result of a log ingestion run with full context for CLI display."""

    records: list[NormalizedFlowLog] = Field(default_factory=list)
    total_lines: int = 0
    duplicates_removed: int = 0
    errors_skipped: int = 0
    source_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

### Pattern 4: S3 Prefix Scan + Stream
**What:** List all objects under a prefix, then stream each object line-by-line.
**When to use:** S3 ingestion path.
**Example:**
```python
import aioboto3
import gzip
import io

async def ingest_from_s3(
    bucket: str,
    prefix: str,
    *,
    aws_profile: str | None = None,
) -> AsyncIterator[NormalizedFlowLog | tuple[int, str, str]]:
    """Stream VPC Flow Log records from all objects under an S3 prefix."""
    session = aioboto3.Session(profile_name=aws_profile)
    async with session.client("s3") as client:
        paginator = client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                response = await client.get_object(Bucket=bucket, Key=key)
                async with response["Body"] as stream:
                    data = await stream.read()
                    # Decompress if .gz
                    if key.endswith(".gz"):
                        data = gzip.decompress(data)
                    lines = data.decode("utf-8").splitlines()
                    for i, line in enumerate(lines, 1):
                        # parse each line...
                        pass
```

### Anti-Patterns to Avoid
- **Downloading entire S3 objects to disk:** Use streaming reads. For gzip files, read to memory and decompress (VPC log files are typically small enough per-object, the streaming constraint is about not writing temp files to disk).
- **Raising exceptions on malformed lines:** Always return None/error tuple and let the caller accumulate warnings. Never abort ingestion.
- **Mutable global state for dedup:** Pass the seen-hashes set explicitly or encapsulate in an ingestion context. Do not use module-level mutable state.
- **Blocking I/O in async functions:** Never use `open()` directly in async code; always use `aiofiles.open()` or `asyncio.to_thread()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S3 pagination | Manual next-token loop | `client.get_paginator("list_objects_v2")` | Handles truncation, 1000-object batches automatically |
| Gzip decompression | Manual zlib streaming | `gzip.decompress()` for full bytes, `gzip.open()` for local files | Handles headers, checksums, edge cases |
| IP address validation | Regex patterns | `ipaddress.IPv4Address` / `IPv6Address` | Validates range, handles edge cases, already used in schema |
| AWS credential chain | Manual env/file parsing | boto3/aioboto3 default credential chain | Handles all auth methods, profiles, IAM roles |
| File glob expansion | Manual os.walk + fnmatch | `pathlib.Path.glob()` or `glob.glob()` | Recursive glob, platform-independent |
| Hash computation for dedup | Custom string concatenation | `hashlib.sha256(key_string.encode()).hexdigest()` | Consistent, fast, collision-resistant |

**Key insight:** VPC Flow Log parsing is simple enough to hand-roll (it is just `line.split()` with field mapping), but the sentinel handling, protocol mapping, and error reporting make it worth building carefully with clear separation between parsing and ingestion orchestration.

## Common Pitfalls

### Pitfall 1: VPC Flow Log Header Line
**What goes wrong:** The first line of a VPC Flow Log file is a header containing field names, not data. Parsing it as data produces garbage.
**Why it happens:** Header looks like: `version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status`
**How to avoid:** Skip lines where the first field is not a digit (version number), or explicitly check if the line starts with "version".
**Warning signs:** First record in output has nonsensical values.

### Pitfall 2: IANA Protocol Numbers vs Protocol Names
**What goes wrong:** VPC Flow Logs use IANA numeric protocol numbers (6 for TCP, 17 for UDP, 1 for ICMP), not protocol names. Mapping to `ProtocolEnum` requires a lookup table.
**Why it happens:** The IANA protocol field is an integer, but `ProtocolEnum` expects string values like "TCP".
**How to avoid:** Build a `PROTOCOL_MAP: dict[int, ProtocolEnum]` with at least {1: ICMP, 6: TCP, 17: UDP}. For unknown protocol numbers, decide: skip the line or use a fallback.
**Warning signs:** All records show `None` or error for protocol field.

### Pitfall 3: ACCEPT/REJECT vs ALLOW/DENY/DROP
**What goes wrong:** VPC Flow Logs use `ACCEPT` and `REJECT`, but `ActionEnum` has `ALLOW`, `DENY`, and `DROP`. Direct string comparison fails.
**Why it happens:** Different naming conventions between AWS and the normalized schema.
**How to avoid:** Map `ACCEPT -> ALLOW`, `REJECT -> DENY`. `DROP` has no VPC equivalent.
**Warning signs:** Pydantic validation errors on the `action` field.

### Pitfall 4: flow_direction Has No VPC v2 Equivalent
**What goes wrong:** `NormalizedFlowLog` requires `flow_direction` (INBOUND/OUTBOUND) but VPC v2 default format does not include direction information.
**Why it happens:** Flow direction was added in VPC v3+ custom formats. The v2 default 14-field format does not include it.
**How to avoid:** Default to a sensible value. Options: (a) always set to `INBOUND` as a placeholder, (b) make `flow_direction` optional in the schema (schema change), or (c) attempt inference from port numbers (unreliable). Recommendation: default to `INBOUND` with a note that direction is inferred/unknown from v2 logs.
**Warning signs:** Pydantic validation fails because `flow_direction` is required but not provided.

### Pitfall 5: log-status NODATA and SKIPDATA Lines
**What goes wrong:** Lines with `log-status` of `NODATA` or `SKIPDATA` have `-` for most fields. Attempting to parse them as regular flow records fails.
**Why it happens:** These are metadata lines indicating no traffic or data loss, not actual flow records.
**How to avoid:** Check `log-status` (column 14) first. If not `OK`, skip the line silently (these are not malformed, just informational).
**Warning signs:** Flood of "malformed line" warnings for lines that are actually valid metadata.

### Pitfall 6: S3 Pagination for Large Prefix Scans
**What goes wrong:** `list_objects_v2` returns at most 1000 objects per call. Without pagination, large log directories are silently truncated.
**Why it happens:** AWS API default limit.
**How to avoid:** Always use the paginator: `client.get_paginator("list_objects_v2")`.
**Warning signs:** Ingestion stops at exactly 1000 files.

### Pitfall 7: Gzip Detection by Extension Only
**What goes wrong:** Some S3 objects may be gzipped but not have a `.gz` extension, or vice versa.
**Why it happens:** S3 object keys don't enforce naming conventions.
**How to avoid:** Per user decision, detect by extension (`.gz`). This is an acceptable trade-off. Wrap gzip.decompress in a try/except to handle misdetection gracefully.
**Warning signs:** `gzip.BadGzipFile` exception on non-gzipped files with `.gz` extension.

### Pitfall 8: Dedup Hash Collisions on Sentinel Values
**What goes wrong:** If sentinel values (0 for ports, None for optional fields) are included in the hash key, many unrelated records may hash identically.
**Why it happens:** ICMP traffic has port 0 for both src and dst; many flows share the same 0-port values.
**How to avoid:** The dedup key (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action) includes enough fields to distinguish. Ensure sentinel-mapped values are in the key (0 is a valid port value for the hash).
**Warning signs:** Unexpectedly high dedup removal counts.

## Code Examples

Verified patterns from official sources:

### VPC v2 Default Format Field Positions
```python
# Source: https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html
# VPC Flow Log v2 default format: 14 space-delimited fields
# Position:  0        1           2             3        4        5       6
#            version  account-id  interface-id  srcaddr  dstaddr  srcport dstport
# Position:  7         8        9      10     11   12      13
#            protocol  packets  bytes  start  end  action  log-status

# Example line:
# 2 123456789012 eni-1235b8ca123456789 172.31.16.139 172.31.16.21 20641 22 6 20 4249 1418530010 1418530070 ACCEPT OK

IDX_VERSION = 0
IDX_ACCOUNT_ID = 1
IDX_INTERFACE_ID = 2
IDX_SRCADDR = 3
IDX_DSTADDR = 4
IDX_SRCPORT = 5
IDX_DSTPORT = 6
IDX_PROTOCOL = 7
IDX_PACKETS = 8
IDX_BYTES = 9
IDX_START = 10
IDX_END = 11
IDX_ACTION = 12
IDX_LOG_STATUS = 13
```

### Sentinel Value Handling
```python
# Source: AWS VPC Flow Log docs - sentinel values
# '-' means not applicable or could not be computed
# For numeric fields: map to 0
# For optional string fields: map to None

def parse_int_or_sentinel(value: str, default: int = 0) -> int:
    """Parse integer field, returning default for AWS sentinel '-'."""
    if value == "-":
        return default
    return int(value)

def parse_optional_str(value: str) -> str | None:
    """Parse optional string field, returning None for AWS sentinels."""
    if value in ("-", "NODATA"):
        return None
    return value
```

### S3 Streaming with aioboto3
```python
# Source: aioboto3 docs + boto3 S3 paginator docs
import aioboto3

async def list_s3_objects(
    bucket: str, prefix: str, *, profile: str | None = None
) -> list[str]:
    """List all object keys under an S3 prefix."""
    session = aioboto3.Session(profile_name=profile)
    keys: list[str] = []
    async with session.client("s3") as client:
        paginator = client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
    return keys
```

### Dedup Hash Computation
```python
import hashlib

def compute_dedup_key(record: NormalizedFlowLog) -> str:
    """Compute deduplication hash from the 7-field key."""
    key_parts = (
        str(record.src_ip),
        str(record.dst_ip),
        str(record.src_port),
        str(record.dst_port),
        record.protocol.value,
        record.timestamp.isoformat(),
        record.action.value,
    )
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()
```

### Moto S3 Test Fixture
```python
# Source: moto docs + pytest-asyncio patterns
import pytest
import pytest_asyncio
from moto import mock_aws

@pytest.fixture
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy AWS credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

@pytest_asyncio.fixture
async def s3_bucket_with_logs(aws_credentials: None):
    """Create a mock S3 bucket with sample VPC Flow Log files."""
    with mock_aws():
        import aioboto3
        session = aioboto3.Session()
        async with session.client("s3", region_name="us-east-1") as client:
            await client.create_bucket(Bucket="test-logs")
            sample_log = (
                "version account-id interface-id srcaddr dstaddr "
                "srcport dstport protocol packets bytes start end action log-status\n"
                "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
                "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
            )
            await client.put_object(
                Bucket="test-logs",
                Key="vpc-logs/2024/01/log1.txt",
                Body=sample_log.encode(),
            )
            yield client
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| boto3 sync + threading | aioboto3 native async | aioboto3 matured 2023+ | True async S3 operations; no thread pool overhead |
| `@mock_s3` decorator (moto) | `@mock_aws` / `mock_aws()` context manager | moto 5.x (2024) | Unified decorator for all AWS services |
| Manual S3 pagination | `get_paginator()` async iteration | aioboto3 paginator support | Clean async for pattern for multi-page results |
| `open()` with thread pool | `aiofiles.open()` | aiofiles stable since 2022 | Native async file iteration |

**Deprecated/outdated:**
- `@mock_s3` decorator: replaced by `@mock_aws` in moto 5.x
- `flowlogs-reader` library: exists but is sync-only and pulls from CloudWatch Logs, not S3; not suitable for this use case

## Open Questions

1. **flow_direction default for VPC v2 logs**
   - What we know: VPC v2 default format has no direction field. `NormalizedFlowLog.flow_direction` is required (no default).
   - What's unclear: Whether to modify the schema to make it optional, or default to a value.
   - Recommendation: Default to `FlowDirection.INBOUND` in the parser with a comment that v2 logs lack direction info. Do not modify the schema -- downstream consumers may depend on direction being present. Future VPC v5+ custom formats can provide real direction.

2. **Unknown IANA protocol numbers**
   - What we know: `ProtocolEnum` only supports TCP, UDP, ICMP. VPC logs may contain other protocols (e.g., GRE=47, IGMP=2).
   - What's unclear: Whether to skip lines with unknown protocols or extend the enum.
   - Recommendation: Skip lines with unknown protocols and log a warning. Do not extend `ProtocolEnum` -- this phase focuses on common traffic. Phase 7 pipeline only analyzes TCP/UDP/ICMP traffic patterns.

3. **aioboto3 iter_lines() vs read-then-split for S3**
   - What we know: aioboto3's StreamingBody supports `iter_lines()` for async line iteration, but for gzipped files the entire object must be read and decompressed anyway.
   - What's unclear: Whether `iter_lines()` is reliable across all aiobotocore versions for large files.
   - Recommendation: For plain text S3 objects, use `iter_lines()` for true streaming. For `.gz` objects, read full body with `await stream.read()`, decompress with `gzip.decompress()`, then split lines. This is pragmatic -- individual VPC log files are typically 1-50MB uncompressed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_ingestion/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-01 | Parse local VPC Flow Log file, all 12 fields populated | unit + integration | `uv run pytest tests/test_ingestion/test_parser.py tests/test_ingestion/test_local.py -x` | No -- Wave 0 |
| INGEST-02 | Parse VPC Flow Logs from S3 bucket via aioboto3 | integration (moto) | `uv run pytest tests/test_ingestion/test_s3.py -x` | No -- Wave 0 |
| INGEST-03 | Normalization: IANA protocol mapping, action mapping, timestamp conversion, sentinel handling | unit | `uv run pytest tests/test_ingestion/test_parser.py -x` | No -- Wave 0 |
| INGEST-04 | Malformed lines skipped with warnings; deduplication by hash key | unit | `uv run pytest tests/test_ingestion/test_parser.py tests/test_ingestion/test_dedup.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_ingestion/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ingestion/__init__.py` -- package marker
- [ ] `tests/test_ingestion/conftest.py` -- shared fixtures (sample log lines, mock S3 bucket, VPC log file content)
- [ ] `tests/test_ingestion/test_parser.py` -- covers INGEST-01, INGEST-03, INGEST-04 (line parsing)
- [ ] `tests/test_ingestion/test_local.py` -- covers INGEST-01 (local file ingestion)
- [ ] `tests/test_ingestion/test_s3.py` -- covers INGEST-02 (S3 ingestion with moto)
- [ ] `tests/test_ingestion/test_dedup.py` -- covers INGEST-04 (deduplication)
- [ ] Dependencies: `uv add aioboto3 aiofiles` and `uv add --group dev "moto[s3]" pytest-asyncio`
- [ ] pytest-asyncio mode config: add `asyncio_mode = "auto"` to pyproject.toml pytest options

## Sources

### Primary (HIGH confidence)
- [AWS VPC Flow Log Records](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html) - v2 default format fields, sentinel values, log-status
- [IANA Protocol Numbers](https://www.iana.org/assignments/protocol-numbers/protocol-numbers.txt) - TCP=6, UDP=17, ICMP=1
- [aioboto3 PyPI](https://pypi.org/project/aioboto3/) - v15.5.0, async boto3 wrapper
- [aiofiles PyPI](https://pypi.org/project/aiofiles/) - v25.1.0, async file I/O
- [moto docs](http://docs.getmoto.org/en/latest/docs/getting_started.html) - mock_aws usage, S3 support
- [aioboto3 usage docs](https://aioboto3.readthedocs.io/en/latest/usage.html) - S3 client patterns

### Secondary (MEDIUM confidence)
- [pytest-asyncio docs](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) - auto mode, fixture patterns
- [pytest-aioboto3](https://github.com/phillipuniverse/pytest-aioboto3) - moto + aioboto3 fixture patterns
- [botocore StreamingBody reference](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/response.html) - iter_lines() method

### Tertiary (LOW confidence)
- aioboto3 iter_lines() reliability for large files -- based on GitHub issues, not official docs; recommend testing empirically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - aioboto3, aiofiles, moto are well-established and documented
- Architecture: HIGH - parser/ingestion separation is a standard pattern; VPC format is well-documented
- Pitfalls: HIGH - VPC sentinel values, IANA mapping, flow_direction gap are documented and verified
- S3 streaming details: MEDIUM - aioboto3 iter_lines() behavior less documented than sync boto3

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain; AWS VPC Flow Log format rarely changes)