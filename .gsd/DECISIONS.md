# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001/S01 | convention | Pyright strict scope | src/ only — tests excluded | Tests use dict[str, Any] fixtures incompatible with strict mode | No |
| D002 | M001/S01 | convention | datetime.UTC usage | datetime.UTC alias per pyupgrade UP017 | Pyupgrade recommendation | No |
| D003 | M001/S01 | pattern | PipelineState TypedDict style | typing.TypedDict with total=False | Partial state construction for LangGraph compatibility | No |
| D004 | M001/S01 | pattern | Exception details default | Empty dict (not None) | Safe attribute access without None checks | No |
| D005 | M001/S02 | pattern | Comma-separated env vars | NoDecode + field_validator | Avoids JSON env var parsing complexity | No |
| D006 | M001/S02 | arch | Nested config models | BaseModel (not BaseSettings) | Only root PolicyFoundryConfig is BaseSettings | No |
| D007 | M001/S02 | pattern | YAML source handling | Only added to priority chain if file exists on disk | Prevents FileNotFoundError on missing configs | No |
| D008 | M001/S03 | pattern | Flow log parser error handling | Pure function returns None on failure, never raises | Graceful degradation for malformed lines | No |
| D009 | M001/S03 | pattern | NODATA/SKIPDATA handling | Silently skipped (not counted as errors) | AWS metadata lines, not real errors | No |
| D010 | M001/S03 | data | Dedup key composition | 7 fields (src_ip, dst_ip, src_port, dst_port, protocol, timestamp, action) | Excludes bytes_transferred and packets_count as they vary | No |
| D011 | M001/S03 | pattern | flow_direction default | INBOUND for all v2 lines | v2 format lacks direction info | No |
| D012 | M001/S04 | library | AWS async approach | boto3 + asyncio.to_thread (not aioboto3) | moto/aiobotocore version incompatibility | Yes — if moto fixes compatibility |
| D013 | M001/S04 | pattern | DuckDB connection management | Per-query connections (open, run, close) | No persistent connection management needed | No |
| D014 | M001/S04 | pattern | Parquet filename format | YYYYMMDDTHHMMSSffffff_{8charhash}.parquet | Microsecond precision prevents collisions | No |
| D015 | M001/S05 | pattern | NetworkEndpoint validation | model_validator(mode=after) for at-least-one-identifier | Enforces cidr OR security_group_id OR tag present | No |
| D016 | M001/S05 | pattern | Translator pattern | Stateless AwsSgTranslator with only static methods | No instance state needed | No |
| D017 | M001/S05 | pattern | Validation strategy | Collect all errors (not short-circuit) | Users see every issue at once | No |
| D018 | M001/S06 | library | Structured output approach | instructor.from_litellm(acompletion, mode=JSON) | Async structured output with LiteLLM | No |
| D019 | M001/S06 | pattern | Ollama model prefix | ollama_chat/ prefix for chat endpoint | Better structured JSON than completion endpoint | No |
| D020 | M001/S06 | pattern | Health check scope | Only for Ollama provider (skip cloud) | Cloud providers have different availability patterns | No |
| D021 | M001/S07 | arch | Pipeline DI pattern | LangGraph context_schema with PipelineContext dataclass | Type-safe dependency injection into stage functions | No |
| D022 | M001/S07 | pattern | Stage function return type | dict[str, Any] | Satisfies pyright strict mode with LangGraph dynamic types | No |
| D023 | M001/S07 | pattern | LLM list output wrapper | PolicyProposalList/RuleDecisionList wrapper BaseModel | Instructor needs single response_model for lists | No |
| D024 | M001/S07 | pattern | Empty proposals handling | Skip LLM call entirely when no proposals | Token-efficient short-circuit | No |
| D025 | M001/S07 | pattern | Temperature settings | 0.1 for Analyze/Assess/Decide (precision), 0.3 for Generate (balanced creativity) | Security analysis needs precision; rule generation needs some creativity | No |
| D026 | M001/S08 | pattern | Validate step approach | Non-LLM: filters via adapter.validate() | Saves tokens and prevents deciding on impossible rules | No |
| D027 | M001/S09 | arch | Typer async strategy | Sync commands with internal asyncio.run() | Typer 0.24.1 does not natively await async commands in CliRunner — verified empirically | No |
| D028 | M001/S09 | arch | Source reconstruction prerequisite | Decompile .pyc → .py before any S09 implementation | All 92 source files deleted; bytecode is only truth; must reconstruct to edit or extend | No |
| D029 | M001/S09 | arch | S09 risk elevation to HIGH | Source reconstruction is blocking prerequisite with uncertain decompiler support for CPython 3.13 | Changes slice risk profile from medium to high | No |
| D030 | M001/S09 | pattern | CLI error handling strategy | Catch PolicyFoundryError at command boundary, render with Rich console | Actionable messages not stack traces; --debug flag for full tracebacks | No |
| D031 | M001/S09 | arch | LLM dependency is Instructor not LangChain-LiteLLM | instructor[litellm]>=1.14.5 via from_litellm(acompletion) | Actual installed dep differs from original research which assumed langchain-litellm | No |
| D032 | M001/S09 | arch | Bytecode reconstruction method | dis module via .venv/bin/python3 (CPython 3.13) + manual reconstruction | decompyle3 does not support CPython 3.13; dis from same-version Python works; verified empirically | No |
| D033 | M001/S09 | pattern | CLI integration test mock boundary | Mock LLMClient and FirewallAdapter; keep real config, ingestion, storage, output | Tests prove module composition through CLI without requiring real LLM or AWS | No |
| D034 | M001/S09 | convention | S09 task count (13 tasks) | Justified by 92-file bytecode reconstruction prerequisite | 48 src + 44 test files must be recovered before 3 implementation tasks (D028, D029) | No |
| D035 | M001/S09 | fix | TrafficAnalysis field types corrected | anomalies: list[dict], bandwidth_outliers: list[dict], unique_sources/destinations: Field(ge=0) | T06 reconstruction typed anomalies/bandwidth_outliers as list[str] and omitted ge=0 on unique_sources/unique_destinations; test bytecode proves dicts were expected and -1 must be rejected | No |
| D036 | M001/S09 | config | pytest asyncio_mode = "auto" | Added [tool.pytest.ini_options] asyncio_mode = "auto" to pyproject.toml | Storage tests in bytecode are async without @pytest.mark.asyncio decorators; auto mode required for pytest-asyncio 1.3.0 | No |
| D037 | M001/S09 | fix | LLMClient retry decorator needs reraise=True | Added reraise=True to @retry on _call_with_retry | Without reraise, tenacity 9.x wraps exhausted retries in RetryError instead of re-raising the original transient exception; the except _TRANSIENT_EXCEPTIONS handler in complete() never fires. Test bytecode proves PipelineError with LLM_CALL_FAILED is expected on retry exhaustion. | No |
| D038 | M002 | arch | Excel analysis as new mode, not new tool | Extend existing `analyze --source excel` command | User confirmed: one CLI tool with multiple source modes, not separate tools | No |
| D039 | M002 | arch | Separate LangGraph pipeline for Excel traffic | New `build_excel_pipeline()` graph, not modifying M001 VPC pipeline | Different input shape (aggregated flows vs DuckDB queries) warrants separate graph; shared LLMClient and adapter interface | No |
| D040 | M002 | arch | NullAdapter for no-FW mode | NullAdapter returns empty rules; assess stage infers from traffic patterns | Future M003 will add real FW adapter; NullAdapter keeps the pipeline contract intact | Yes — when M003 adds real FW querying |
| D041 | M002 | pattern | Auto-detect + config override for column mapping | Try header-name matching first, fall back to user-provided ColumnMapping | Handles common cases automatically; escape hatch for non-standard exports | No |
| D042 | M002 | pattern | Subnet grouping by AI, not heuristic | Pre-processing identifies subnet candidates; LLM makes final grouping decision | Heuristic /24 boundaries may not match organizational subnetting; AI can reason about context | No |
| D043 | M002/S01 | pattern | Neutral field naming in ExcelTrafficRecord | ip1/port1/ip2/port2 (not src/dst) | Direction inference is S02's job; raw Excel columns are positional ("IP1", "Port1"), not directional | No |
| D044 | M002/S01 | pattern | Synonym dictionary for column auto-detect | Exact match after normalize (lowercase, strip, collapse spaces) — no fuzzy/NLP | Deterministic, testable, covers common vendor naming patterns; config override handles edge cases | No |
| D045 | M002/S02 | pattern | DirectionLabel(StrEnum) with UNKNOWN instead of reusing adapters.schema.Direction | New DirectionLabel enum: INBOUND/OUTBOUND/UNKNOWN | adapters.schema.Direction only has INBOUND/OUTBOUND; S02 needs UNKNOWN for ambiguous flows (both-ephemeral-port cases). Downstream S03 can map DirectionLabel→Direction when creating UniversalRules. | No |
| D046 | M002/S02 | pattern | Direction inference signal priority order | well-known port → interface zone → flag 'O' → UNKNOWN | Strongest signal first: well-known port < 1024 (or in KNOWN_SERVICE_PORTS) is most reliable; interface zone "inet" next; flag "O" weakest positive signal; UNKNOWN fallback for ~770 ambiguous records | No |
| D047 | M002/S02 | pattern | Aggregation key excludes ephemeral ports | Key = (src_ip, dst_ip, service_port, protocol, direction) | Ephemeral source ports vary per connection; including them would prevent dedup. Only the service port (server-side) is meaningful for rule proposals. Sample ports collected for diagnostics. | No |
| D048 | M002/S03 | pattern | Shared Rich renderers made public | Rename _render_* to render_* in rich_output.py for cross-pipeline reuse | Excel and M01 pipelines share identical output shapes (TrafficAnalysis, SecurityAssessment, etc.) — extracting shared renderers avoids duplication. Excel formatter adds only an Excel-specific summary panel. | No |
| D049 | M002/S03 | pattern | Pre-summarizer before LLM context | Python-computed statistics (~2-3K tokens) instead of raw flow serialization (~40K tokens) | 600 flows × 267 chars/flow exceeds practical LLM context windows. Pre-summarize direction breakdown, top talkers, port distribution in Python; send compact stats to LLM. | No |
| D050 | M002/S03 | pattern | ExcelPipelineContext carries flow data, not file path | aggregated_flows + subnet_groups in context dataclass (not data_dir like M01) | M01 queries DuckDB at runtime via data_dir; Excel pipeline has in-memory AggregatedFlow/SubnetGroup lists from S02 — no filesystem queries needed. | No |
| D051 | M002/S04 | pattern | Export entries skip SKIP decisions | flatten_to_entries excludes decisions with action="SKIP" | Change request forms should only contain rules to be created — skipped proposals are not actionable. Keeps exported forms clean. | No |
| D052 | M002/S04 | pattern | Custom template column matching | Case-insensitive header scan on row 1, match against known synonym dict | Deterministic, covers common form layouts. Complex templates (merged cells, multi-row headers) documented as unsupported with clear ExportError. | No |
| D053 | M002/S04 | library | PDF generation library | fpdf2 (pure Python, ~1MB, table() context manager) | weasyprint requires Cairo/Pango system libs (breaks pip-install story). reportlab is heavier than needed. fpdf2 has built-in table support sufficient for structured forms. | No |
| D054 | M002/S05 | arch | Full pipeline replaces ingestion-only handler | `_run_excel_analyze` replaces `_run_excel_ingestion` — runs ingest → pipeline → output → export | S01 wired ingestion-only as placeholder; S05 replaces with complete flow. Single function handles the entire Excel workflow. | No |
| D055 | M002/S05 | pattern | Export file naming convention | Source file stem + `_change_request.{ext}` | `traffic.xlsx` → `traffic_change_request.xlsx` / `.pdf`. Output goes to same directory as input. Simple and predictable. | No |
| D056 | M002/S05 | pattern | Comma-separated export formats | `--export xlsx,pdf` produces both files in one run | Avoids running the pipeline twice. Parsed with split + strip + lowercase. Unknown formats warn instead of error. | No |
| D057 | M002/S05 | pattern | Template validation at CLI boundary | `--template` requires `--export xlsx` — fails with TEMPLATE_WITHOUT_EXPORT before touching the pipeline | Fail fast with clear error message instead of silently ignoring the template flag. | No |
