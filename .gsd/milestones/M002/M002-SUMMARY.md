---
id: M002
provides:
  - Excel traffic log ingestion with synonym-based column auto-detection (10 columns, 83K rows)
  - Config override for custom column mappings via ExcelConfig in PolicyFoundryConfig
  - Traffic pre-processing — direction inference (4-signal heuristic), flow aggregation (~603 tuples from 83K), subnet grouping (/24 candidates)
  - 5-stage LangGraph pipeline for Excel traffic analysis (Analyze → Assess → Generate → Validate → Decide)
  - NullAdapter implementing FirewallAdapter ABC for no-FW pipeline mode
  - Pre-summarizer compressing 600 flows into ~2-3K tokens for LLM context windows
  - AI-generated business justifications and risk classifications per proposed rule
  - Rich terminal output with Excel-specific summary panel + shared renderers
  - JSON export of full pipeline state
  - Excel (.xlsx) change request form export with default and custom template support
  - PDF change request document export via fpdf2
  - CLI integration — `policyfoundry analyze --source excel --file <path> --export xlsx,pdf --template <path>`
key_decisions:
  - D038 — Excel analysis as new mode extending existing `analyze --source excel` command
  - D039 — Separate LangGraph pipeline for Excel (different input shape vs M01 VPC pipeline)
  - D040 — NullAdapter for no-FW mode; assess stage infers from traffic patterns
  - D041 — Auto-detect + config override for column mapping
  - D043 — Neutral field naming (ip1/port1 not src/dst) — direction inference deferred to S02
  - D045 — DirectionLabel(StrEnum) with UNKNOWN instead of reusing adapters.schema.Direction
  - D046 — Direction inference signal priority: well-known port → interface zone → flag → UNKNOWN
  - D047 — Aggregation key excludes ephemeral ports
  - D049 — Pre-summarizer before LLM context (~2-3K tokens vs ~40K raw)
  - D050 — ExcelPipelineContext carries inline flow data (not data_dir like M01)
  - D051 — Export entries skip SKIP decisions (only actionable rules)
  - D053 — fpdf2 for PDF generation (pure Python, no system lib deps)
  - D054 — Full pipeline replaces ingestion-only handler
  - D056 — Comma-separated --export formats for single-run dual export
patterns_established:
  - Excel-specific Pydantic models parallel to VPC flow log models (separate schema, not extending NormalizedFlowLog)
  - Synonym dictionary pattern for deterministic column auto-detection
  - Multi-signal heuristic with clear fallback chain for direction inference
  - Pre-summarization as a separate pure function consumed by pipeline stages
  - Pipeline-specific summary panels alongside shared section renderers for output formatting
  - export/ package with models.py for flattening logic and change_request.py for file generation
  - CLI source branching pattern for multiple ingestion modes
observability_surfaces:
  - ExcelParseError with error_code and details dict (unmatched_fields, available_headers)
  - ExcelIngestionResult.warnings list captures per-row skip reasons
  - PipelineError with error_code="PIPELINE_STAGE_FAILED", stage name in details, chained original exception
  - ExportError with error_code (XLSX_EXPORT_FAILED, PDF_EXPORT_FAILED, TEMPLATE_LOAD_FAILED) and details dict
  - Structured CLI error panels for all failure modes (MISSING_FILE_OPTION, TEMPLATE_WITHOUT_EXPORT, EMPTY_EXCEL_FILE, PIPELINE_STAGE_FAILED)
  - Token usage tracked per-stage via LLMClient (reuses M01 infrastructure)
  - format_excel_json() serializes full pipeline state for inspection
requirement_outcomes:
  - id: R101
    from_status: active
    to_status: validated
    proof: 54 tests (schema, column detection, parsing) + CLI parsing 83,633 rows with all 10 columns auto-detected
  - id: R102
    from_status: active
    to_status: validated
    proof: TestColumnMappingOverride tests proving config override works with standard and non-standard headers
  - id: R103
    from_status: active
    to_status: validated
    proof: 12 aggregation tests proving dedup, counting, service port keying, ephemeral port exclusion; 83K→~603 tuples
  - id: R104
    from_status: active
    to_status: validated
    proof: 27 parametrized direction inference tests covering all signal combinations (well-known port, interface zone, flag, both-ephemeral fallback)
  - id: R105
    from_status: active
    to_status: validated
    proof: 13 subnet grouping tests proving /24 candidates, min 2 IPs, pattern matching, custom prefix lengths
  - id: R106
    from_status: active
    to_status: validated
    proof: 5-node LangGraph graph compiles, 27 stage unit tests + 9 pipeline integration tests with mock LLM
  - id: R107
    from_status: active
    to_status: validated
    proof: Generate stage produces PolicyProposal with justification; Decide stage assigns risk classification and action. Verified by mock LLM structured output tests.
  - id: R108
    from_status: active
    to_status: validated
    proof: 4 CLI integration tests (exit code, summary panel, decisions, token usage) + 2 end-to-end composition tests
  - id: R109
    from_status: active
    to_status: validated
    proof: 11 xlsx export tests (default styled workbook, custom template fill, empty proposals, error handling)
  - id: R110
    from_status: active
    to_status: validated
    proof: 16 PDF export tests (structure, metadata, data rows, empty proposals, error handling)
  - id: R111
    from_status: active
    to_status: validated
    proof: 2 template tests verify case-insensitive header matching and data insertion into user-provided templates
  - id: R112
    from_status: active
    to_status: validated
    proof: NullAdapter implements FirewallAdapter ABC, 15 contract tests, registered in AdapterRegistry, pipeline defaults to NullAdapter
duration: 5 slices across 11 tasks
verification_result: passed
completed_at: 2026-03-16
---

# M002: Excel Traffic Analysis & Change Request Forms

**Complete Excel-to-change-request pipeline: auto-detect column mapping, direction inference, flow aggregation, 5-stage LangGraph analysis with AI justifications and risk scoring, Rich/JSON output, and xlsx/pdf change request form export — all wired through `policyfoundry analyze --source excel`.**

## What Happened

Built the full Excel traffic analysis workflow in 5 slices, each delivering a vertically testable increment:

**S01 — Excel Ingestion.** Created the `ingestion/` Excel path: `ExcelTrafficRecord` with 10 fields using neutral naming (ip1/port1 not src/dst — direction is S02's job), synonym-based column auto-detection via `detect_columns()`, and `ingest_excel_file()` using openpyxl read_only mode. Handles whitespace stripping, DNS annotation cleanup, port type coercion (Excel stores numbers as float). Added `ExcelConfig` to `PolicyFoundryConfig` for column mapping overrides. Wired `--source excel --file` into the CLI. All 10 columns auto-detected from the sample file's headers, 83,633 rows parsed with 0 skipped. 54 tests.

**S02 — Traffic Pre-Processing.** Built the `analysis/` package with four tightly coupled modules. Direction inference uses a 4-signal heuristic (well-known port → interface zone → flag → UNKNOWN fallback). Flow aggregation groups by (src_ip, dst_ip, service_port, protocol, direction), excluding ephemeral ports, collapsing 83K rows to ~603 tuples. Subnet grouping identifies /24 candidates where 2+ IPs share traffic patterns. All pure stateless functions. 67 tests.

**S03 — Analysis Pipeline.** The core intelligence layer. NullAdapter implements FirewallAdapter ABC for no-FW mode. Pre-summarizer compresses 600 flows into ~2-3K tokens (vs ~40K raw) for LLM context safety. Five LangGraph stages: Analyze (interpret traffic stats), Assess (infer likely existing rules from patterns), Generate (propose rules with CIDR/subnet guidance), Validate (adapter constraint check), Decide (CREATE/SKIP with risk classification). Excel-specific prompts, ExcelPipelineContext with inline flow data (not DuckDB like M01). Refactored M01's private Rich renderers to public for cross-pipeline reuse. 82 tests across adapter, summarizer, stages, pipeline, and output.

**S04 — Change Request Export.** `export/` package with `ChangeRequestEntry` model and `flatten_to_entries()` that pairs proposals with decisions, filtering SKIP actions. `export_xlsx()` supports default styled workbook (metadata header, bold blue headers, proportional columns) and custom template mode (case-insensitive column matching via synonym dict). `export_pdf()` uses fpdf2 with metadata header and styled table. Both handle empty proposals gracefully. 40 tests.

**S05 — CLI Integration.** Replaced the S01 ingestion-only handler with `_run_excel_analyze()` composing all S01–S04 modules: ingest → pipeline → output → optional export. Added `--export` (supports `xlsx`, `pdf`, or `xlsx,pdf`) and `--template` CLI options. Comma-separated formats produce both files in one run. 19 CLI integration tests covering Rich output, JSON output, export creation, template fill, error handling, and end-to-end composition.

## Cross-Slice Verification

Each success criterion from the milestone roadmap verified with specific evidence:

| Criterion | Evidence |
|---|---|
| `policyfoundry analyze --source excel --file traffic.xlsx` shows Rich report | S05: 4 CLI integration tests (exit code 0, pipeline summary panel, decisions section, token usage footer) |
| `--format json` produces complete JSON | S05: 3 JSON tests (exit code 0, valid JSON with all keys, token_usage present) |
| `--export xlsx` produces filled change request form | S04: 11 xlsx tests; S05: xlsx creation, data content, template fill tests |
| `--export pdf` produces formatted PDF document | S04: 16 PDF tests; S05: PDF magic bytes verification |
| `--template custom.xlsx` fills user-provided template | S04: 2 template tests (header matching, data insertion); S05: template fill integration test |
| Pipeline uses ≥4 LangGraph stages | S03: 5-node graph (Analyze→Assess→Generate→Validate→Decide), 27 stage + 9 pipeline tests |
| Auto-detect maps sample Excel's 10 columns | S01: 54 tests, 83,633 rows parsed, 0 skipped, all 10 columns auto-detected |
| 83K flows collapse into subnet-grouped rules | S02: ~603 aggregated tuples, /24 subnet candidates; S03: subnet groups passed to LLM for final decision |
| Each rule has AI justification and risk | S03: Generate produces justification, Decide assigns risk (verified by structured output tests) |
| Token usage displayed in output footer | S05: token_usage verified in both Rich and JSON output tests |
| Graceful handling of different column layouts | S01: ExcelConfig override tested with non-standard headers |
| NullAdapter for no-FW mode | S03: 15 contract tests, pipeline defaults to NullAdapter |

**Full test suite:** 623 tests pass (611 unit/integration + 12 e2e), zero failures.

**CLI verification:** `policyfoundry analyze --source excel` shows all options (--file, --export, --template, --format, --debug) in help output.

## Requirement Changes

- R101: active → validated — 54 tests + CLI demo parsing 83,633 rows with all 10 columns auto-detected
- R102: active → validated — Config override tests with standard and non-standard headers
- R103: active → validated — 12 aggregation tests; 83K→~603 tuples with flow counts
- R104: active → validated — 27 parametrized direction inference tests covering all signal combinations
- R105: active → validated — 13 subnet grouping tests; /24 candidates with shared pattern detection
- R106: active → validated — 5-node LangGraph graph, 27 stage + 9 pipeline integration tests
- R107: active → validated — Generate produces justification, Decide assigns risk classification
- R108: active → validated — 4 CLI integration tests + 2 end-to-end composition tests
- R109: active → validated — 11 xlsx export tests (default, template, empty, errors)
- R110: active → validated — 16 PDF export tests (structure, metadata, data, empty, errors)
- R111: active → validated — 2 template tests (header matching, data insertion)
- R112: active → validated — NullAdapter with 15 contract tests, registered in AdapterRegistry

## Forward Intelligence

### What the next milestone should know
- The Excel pipeline and M01 VPC pipeline are fully parallel — separate graphs, separate contexts, separate output formatters. They share LLMClient, FirewallAdapter ABC, and the shared Rich renderers (D048). M003 should follow this pattern if adding another analysis mode.
- NullAdapter is the default when no adapter is specified. M003's live FW integration replaces NullAdapter with a real adapter — the Assess stage already has prompts that handle both empty and populated existing rules.
- The export/ package is generic enough to work with any pipeline state that produces `decisions` and `proposals` lists. M03 could reuse it for VPC analysis exports with minimal adaptation.
- `DirectionLabel.UNKNOWN` applies to ~770 records. The pipeline handles UNKNOWN gracefully, but M03 should consider whether real FW context can resolve these ambiguous cases.

### What's fragile
- **LLM prompt quality is untested with real models** — all testing uses mock LLM with predetermined structured output. Real model output may not match Pydantic schemas perfectly (though Instructor handles retries). First real-model run will be the true quality test.
- **Assess stage inference heuristic** — "assume high-volume traffic is already permitted" is prompt-based. Poor LLM reasoning could produce bad inferences about existing rules.
- **Synonym dictionary completeness** — column auto-detect covers the sample file's headers plus common synonyms, but novel vendor header names will fall through to UNKNOWN (config override is the escape hatch).
- **Custom template assumptions** — single-row headers in row 1 only. Merged cells, multi-row headers, or headers not in row 1 will silently fail.
- **PDF is Helvetica-only** — no Unicode/CJK glyph support.

### Authoritative diagnostics
- `pytest tests/test_cli/test_excel_analyze.py -v` — fastest CLI integration check (19 tests)
- `pytest tests/ --ignore=tests/e2e -q` — full unit/integration suite (611 tests, ~21s)
- `ExcelParseError.details` — contains `unmatched_fields` and `available_headers` when column detection fails
- `ExportError.error_code` + `.details` — immediate context on any export failure
- `format_excel_json(state)` — dumps full pipeline state as JSON for inspection

### What assumptions changed
- **Pre-summarizer token budget** — assumed ~3K max, actual output well under that for 600 flows. Context window risk fully retired.
- **Direction inference accuracy** — the 4-signal heuristic works well for the sample data. Only ~770 records (both-ephemeral ports) fall to UNKNOWN, which is the expected proportion.
- **fpdf2 chosen over reportlab/weasyprint** (D053) — pure Python, no system deps, sufficient for structured forms. This was an open question at milestone start.

## Files Created/Modified

- `src/policyfoundry/ingestion/excel_schema.py` — ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult models
- `src/policyfoundry/ingestion/column_detect.py` — detect_columns() with SYNONYM_MAP
- `src/policyfoundry/ingestion/excel.py` — ingest_excel_file() parser
- `src/policyfoundry/ingestion/__init__.py` — Updated exports
- `src/policyfoundry/config/models.py` — Added ExcelConfig
- `src/policyfoundry/exceptions.py` — Added ExcelParseError, ExportError
- `src/policyfoundry/analysis/__init__.py` — Package exports
- `src/policyfoundry/analysis/models.py` — DirectionLabel, DirectionResult, AggregatedFlow, SubnetGroup
- `src/policyfoundry/analysis/direction.py` — infer_direction() heuristic
- `src/policyfoundry/analysis/aggregator.py` — aggregate_flows()
- `src/policyfoundry/analysis/subnet.py` — group_to_subnets()
- `src/policyfoundry/adapters/null.py` — NullAdapter
- `src/policyfoundry/adapters/registry.py` — Added null adapter as built-in
- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState TypedDict
- `src/policyfoundry/pipeline/excel_summarizer.py` — Pre-summarizer
- `src/policyfoundry/pipeline/excel_graph.py` — ExcelPipelineContext + build_excel_pipeline()
- `src/policyfoundry/pipeline/excel_runner.py` — run_excel_pipeline()
- `src/policyfoundry/pipeline/excel_stages/` — 5 stage modules (analyze, assess, generate, validate, decide)
- `src/policyfoundry/pipeline/excel_prompts/` — 4 prompt modules (analyze, assess, generate, decide)
- `src/policyfoundry/output/rich_output.py` — Refactored renderers to public
- `src/policyfoundry/output/excel_rich_output.py` — format_excel_rich()
- `src/policyfoundry/output/excel_json_output.py` — format_excel_json()
- `src/policyfoundry/output/models.py` — Added ExcelPipelineResult
- `src/policyfoundry/export/__init__.py` — Package init
- `src/policyfoundry/export/models.py` — ChangeRequestEntry, flatten_to_entries
- `src/policyfoundry/export/change_request.py` — export_xlsx(), export_pdf()
- `src/policyfoundry/main.py` — Extended analyze command with --export, --template, full Excel pipeline
- `pyproject.toml` — Added openpyxl (main), fpdf2 dependencies
- `tests/test_ingestion/test_excel_schema.py` — 17 tests
- `tests/test_ingestion/test_column_detect.py` — 13 tests
- `tests/test_ingestion/test_excel.py` — 24 tests
- `tests/test_analysis/test_models.py` — 15 tests
- `tests/test_analysis/test_direction.py` — 27 tests
- `tests/test_analysis/test_aggregator.py` — 12 tests
- `tests/test_analysis/test_subnet.py` — 13 tests
- `tests/test_adapters/test_null_adapter.py` — 15 tests
- `tests/test_pipeline/test_excel_summarizer.py` — 16 tests
- `tests/test_pipeline/test_excel_stages.py` — 27 tests
- `tests/test_pipeline/test_excel_pipeline.py` — 9 tests
- `tests/test_output/test_excel_output.py` — 15 tests
- `tests/test_export/test_models.py` — 13 tests
- `tests/test_export/test_xlsx_export.py` — 11 tests
- `tests/test_export/test_pdf_export.py` — 16 tests
- `tests/test_cli/test_excel_analyze.py` — 19 tests
