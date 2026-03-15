# S01: Excel Ingestion & Column Auto-Detection — Research

**Date:** 2026-03-12

## Summary

S01 delivers the Excel ingestion layer: parse the sample traffic export, auto-detect its 10 columns by header name, normalize records into Pydantic models, and expose a config override path for non-standard layouts. The sample file (83,633 rows, 10 columns, all TCP, 7 src IPs → 133 dst IPs) is clean and consistent — all string columns have trailing whitespace, HostName2 contains DNS annotations ("10.x.x.x (no DNS resolution)"), and ports are native ints. openpyxl's read_only mode parses the full file in ~1.7s with constant memory.

The existing codebase has a clear ingestion pattern (`ingestion/` package with schema, parser, result models) and a config pattern (nested BaseModel inside PolicyFoundryConfig). S01 creates a parallel Excel path alongside the VPC flow log path — same package, new modules, no modifications to existing code. The boundary outputs are well-defined: `ExcelTrafficRecord`, `ColumnMapping`, `ExcelIngestionResult`, and `detect_columns()`.

The main risk is column name variability across FW vendors. Our auto-detect needs to match common synonyms (e.g. "Source IP" / "SrcIP" / "IP1" / "src_ip") while keeping the fallback override trivial. The sample file uses a specific naming pattern ("IP1", "Port1", "Interface1") that's clear but not standard — other vendors use "Source Address", "Src Port", etc.

## Recommendation

Build three new modules in `src/policyfoundry/ingestion/`:
- `excel_schema.py` — `ExcelTrafficRecord`, `ColumnMapping`, `ExcelIngestionResult` Pydantic models
- `column_detect.py` — `detect_columns(headers) -> ColumnMapping` using a synonym dictionary approach
- `excel.py` — `ingest_excel_file(path, column_mapping=None) -> ExcelIngestionResult` using openpyxl read_only mode

Add `ExcelConfig` as a nested BaseModel in `config/models.py` (following D006 pattern). Wire the CLI `analyze` command with `--source excel --file <path>` but only the parsing + summary display — pipeline integration is S03/S05.

Use synonym-based matching for auto-detect: each semantic column (protocol, src_ip, src_port, etc.) has a ranked list of known header names. Score each header against all semantic columns, pick the best match. Require all 10 columns matched or fail with an actionable error listing unmatched headers.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Excel parsing | openpyxl 3.1.5 (already in dev deps) | read_only mode handles 83K rows in 1.7s, constant memory |
| Data models | Pydantic v2 (already a core dep) | Consistent with codebase; validators handle cleanup (strip, DNS annotations) |
| Config nesting | pydantic-settings BaseModel nesting (D006) | Proven pattern for nested config; env var overrides work automatically |
| CLI options | Typer (already a core dep) | Extend existing `analyze` command; Typer handles option parsing |

## Existing Code and Patterns

- `src/policyfoundry/ingestion/schema.py` — `NormalizedFlowLog` Pydantic model with 12 fields. Excel records are a different shape (no timestamp, no action, adds interfaces/hostnames/flag). New model needed, not an extension.
- `src/policyfoundry/ingestion/result.py` — `IngestionResult` pattern: records list + stats + warnings. Follow this pattern for `ExcelIngestionResult`.
- `src/policyfoundry/ingestion/parser.py` — Pure function, returns None on failure (D008). Follow same graceful-degradation pattern for row parsing.
- `src/policyfoundry/config/models.py` — Nested BaseModel pattern (D006). `ExcelConfig` should be a BaseModel nested under `PolicyFoundryConfig`, not a BaseSettings.
- `src/policyfoundry/main.py` — `analyze` command uses sync wrapper with `asyncio.run()` (D027). Excel ingestion is sync (openpyxl), so no async complexity needed for parsing.
- `src/policyfoundry/exceptions.py` — `IngestionError` exists. Use for Excel parse failures. May add specific subclass like `ExcelParseError`.
- `tests/conftest.py` — Shared fixtures pattern. Add Excel-specific fixtures in a new `tests/test_ingestion/conftest.py` or dedicated test file.

## Constraints

- **openpyxl is a dev dependency only** — currently listed under `[dependency-groups] dev`. Must move to main `dependencies` since it's needed at runtime for the `analyze --source excel` command.
- **read_only workbooks must be explicitly closed** — openpyxl docs are clear: `wb.close()` required. Use context manager or try/finally.
- **Ports are native ints in Excel** — openpyxl returns them as `int`, not strings. No parsing needed, but type handling must account for mixed int/str columns.
- **All string values have trailing whitespace** — Must `.strip()` every string cell. This is consistent across all 83K rows.
- **HostName2 contains DNS annotations** — "10.194.184.42 (no DNS resolution)" appears in 4,412 of 83,633 rows. Must extract just the hostname/IP portion.
- **Sample has only 1 sheet** — But other exports may have multiple. Should accept sheet name as optional parameter.
- **Header row is always row 1** — Assumption for auto-detect. May need `header_row` config option for files with metadata rows above headers.

## Common Pitfalls

- **Forgetting `wb.close()` in read_only mode** — Leaves file handles open. Use try/finally pattern, not context manager (openpyxl workbook isn't a proper context manager in read_only mode in all versions).
- **Not stripping whitespace before IP validation** — Every string cell in the sample has trailing spaces. An `ipaddress.ip_address("10.38.73.2     ")` will raise ValueError. Strip first.
- **Treating HostName2 as a hostname when it's a DNS annotation** — "10.194.184.42 (no DNS resolution)" is not a hostname. Must parse out the IP or strip the annotation. The model should store the cleaned value.
- **Over-engineering auto-detect** — Temptation to use NLP or fuzzy matching. Synonym dictionary with exact match after lowercasing/normalizing is sufficient and deterministic.
- **Conflating ExcelTrafficRecord with NormalizedFlowLog** — They're different schemas. Excel records have interface/hostname/flag fields that NormalizedFlowLog doesn't. Don't force them into the same model.
- **Forgetting that Port1 can be a well-known port (server) or ephemeral (client)** — Port1 is just "the port associated with IP1" — direction inference is S02's job, not S01's. S01 should name fields neutrally (ip1/port1/ip2/port2, not src/dst).

## Open Risks

- **Column name collision in auto-detect** — If a non-standard export uses headers that match multiple semantic columns (e.g. "Address" could be src or dst), the synonym matcher must handle ambiguity gracefully. Mitigation: require all 10 columns matched; on ambiguity, fail with clear error and suggest config override.
- **Large files with different data types** — The sample is clean (all ints for ports, all strings for the rest). Real-world exports might have formula cells, merged cells, or mixed types. openpyxl read_only mode handles formulas differently (returns cached value with `data_only=True`). May need `data_only=True` flag.
- **Sheet selection** — Sample has one sheet. Multi-sheet exports exist. Default to first sheet, allow sheet name/index override in config.

## Sample Data Profile

| Property | Value |
|----------|-------|
| Rows | 83,633 (data) + 1 (header) |
| Columns | 10 |
| Headers | Protocol, Interface1, HostName1, IP1, Port1, Interface2, HostName2, IP2, Port2, Flag |
| Protocol | TCP only (100%) |
| Interface1 | inet only |
| Interface2 | zoneA only |
| Unique IP1 (source) | 7 IPs in 10.x.x.x range |
| Unique IP2 (dest) | 133 IPs across 9 /24 subnets |
| Port1 top | 80 (77,873), 443 (4,461), 5274 (529) |
| Port2 unique | 14,202 (ephemeral range) |
| Flags | UIO (82,017), UI (1,600), U (16) |
| HostName1 | hostnameN pattern (hostname1..hostname435) |
| HostName2 | nameN (79,221) or "IP (no DNS resolution)" (4,412) |
| String whitespace | All string columns have trailing whitespace |
| Port types | Native int (openpyxl `n` type) |
| Parse time | ~1.7s read_only mode |

## Requirements Covered

| Requirement | Coverage | Notes |
|-------------|----------|-------|
| R101 — Excel ingestion with auto-detect | Primary owner | Auto-detect, normalization, whitespace/annotation cleanup |
| R102 — Config override for custom mappings | Primary owner | ExcelConfig with ColumnMapping in PolicyFoundryConfig |

## Boundary Outputs (S01 → S02, S05)

Per the roadmap boundary map, S01 must produce:

1. `ingestion/excel.py` → `ingest_excel_file(path, column_mapping=None) -> ExcelIngestionResult`
2. `ingestion/excel_schema.py` → `ExcelTrafficRecord` model (protocol, ip1, port1, interface1, hostname1, ip2, port2, interface2, hostname2, flag)
3. `ingestion/excel_schema.py` → `ColumnMapping` model (maps semantic names to column indices)
4. `ingestion/excel_schema.py` → `ExcelIngestionResult` model (records, column_mapping, stats, warnings)
5. `ingestion/column_detect.py` → `detect_columns(headers: list[str]) -> ColumnMapping`
6. `config/models.py` → `ExcelConfig` nested model added to `PolicyFoundryConfig`

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| openpyxl | vamseeachanta/workspace-hub@openpyxl | Available (35 installs) — low relevance, basic usage sufficient |
| Excel analysis | davila7/claude-code-templates@excel analysis | Available (706 installs) — not relevant, we're building parsing not analysis |
| Pydantic | (core competency) | Already in codebase — no skill needed |
| Typer CLI | (core competency) | Already in codebase — no skill needed |

No skills recommended for installation — the technologies involved are well-understood and our usage is straightforward.

## Sources

- Sample file inspection via openpyxl: 83,633 rows, 10 columns, trailing whitespace, DNS annotations confirmed empirically
- openpyxl read_only mode docs: constant memory, requires explicit close(), returns ReadOnlyCell (source: [openpyxl docs](https://openpyxl.readthedocs.io/en/stable/optimized.html))
- Existing codebase patterns: D006 (nested BaseModel), D008 (graceful parsing), D027 (sync CLI with asyncio.run)
- Boundary map from M002-ROADMAP.md: 6 specific outputs defined
