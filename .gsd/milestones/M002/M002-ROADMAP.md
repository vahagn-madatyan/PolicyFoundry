# M002: Excel Traffic Analysis & Change Request Forms

**Vision:** Users point PolicyFoundry at an Excel firewall traffic export and get back a set of justified, risk-scored firewall rule proposals — displayed as Rich terminal output and exportable as formal change request forms (Excel and PDF). The analysis runs through a rigorous multi-stage LangGraph pipeline with multiple agents cross-checking each other's work. The adapter interface stays flexible for future live FW integration.

## Success Criteria

- User can run `policyfoundry analyze --source excel --file traffic.xlsx` and see a Rich report with proposed FW rules, subnet grouping, risk levels, and justifications
- User can run `--format json` and receive complete JSON with all pipeline stage results
- User can run `--export xlsx` and get a filled-in FW change request form as Excel
- User can run `--export pdf` and get a formatted PDF change request document
- User can provide `--template custom.xlsx` to use their organization's form layout
- The pipeline uses at least 4 LangGraph agent stages (not a single LLM call)
- Auto-detect correctly maps the sample Excel's 10 columns without user configuration
- 83K raw flows collapse into subnet-grouped rules (not 133 individual IP rules)
- Each proposed rule has AI-generated business justification and risk classification
- Token usage and cost are displayed in the output footer (reusing M001 infrastructure)
- The tool gracefully handles Excel files with different column layouts via config override

## Key Risks / Unknowns

- **LLM context window limits with aggregated data** — 600 flow tuples serialized as JSON may exceed context windows on smaller models. May need chunking or top-N filtering before the analyze stage.
- **Direction inference accuracy** — Flag values (U/UI/UIO) are vendor-specific. Incorrect direction inference produces wrong rules. Must validate against the sample data and provide override mechanisms.
- **PDF generation quality** — Python PDF libraries have varying quality. The change request form must look professional enough to submit to a security team.
- **Excel format variability** — Real-world traffic exports from different vendors may have completely different column names, ordering, and data formats.

## Proof Strategy

- **LLM context limits** → Retire in S03 by running the full pipeline against the 83K-row sample file and confirming all stages complete without token errors.
- **Direction inference** → Retire in S02 by validating inferred directions against manual analysis of the sample data (IP1:Port1=443 on inet is server side, IP2:Port2=ephemeral on zoneA is client side → traffic flows zoneA→inet).
- **PDF quality** → Retire in S04 by generating a PDF from the sample data and visually inspecting it.
- **Excel format variability** → Retire in S01 by implementing auto-detect that works on the sample file, plus config override for non-standard layouts.

## Verification Classes

- **Contract verification:** pytest unit/integration tests for Excel parsing, aggregation, direction inference, pipeline stages, export formatters
- **Integration verification:** CLI integration tests exercising `policyfoundry analyze --source excel` end-to-end with mocked LLM
- **Operational verification:** none (no new services)
- **UAT / human verification:** User runs CLI against sample Excel file, visually confirms Rich output quality and exported form readability

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 5 slices complete with passing verification
- `policyfoundry analyze --source excel --file <sample.xlsx>` produces a Rich report with proposed rules
- `--format json` produces valid JSON with all pipeline stage data
- `--export xlsx` produces a filled-in Excel change request form
- `--export pdf` produces a formatted PDF change request document
- `--template custom.xlsx` correctly fills a user-provided template
- Pipeline uses multi-stage LangGraph with at least 4 agent stages
- Rules show subnet grouping where traffic patterns support it
- Each rule has AI-generated justification and risk level
- NullAdapter works for no-FW mode; adapter interface is compatible with M001's FirewallAdapter ABC
- All success criteria re-verified against the live CLI (not just test assertions)

## Requirement Coverage

- **Covers:** R101, R102, R103, R104, R105, R106, R107, R108, R109, R110, R111, R112
- **Partially covers:** none
- **Leaves for later:** R201, R202 (M003 — live FW integration)
- **Orphan risks:** none

## Slices

- [ ] **S01: Excel Ingestion & Column Auto-Detection** `risk:medium` `depends:[]`
  > After this: `policyfoundry analyze --source excel --file traffic.xlsx` parses the sample Excel, auto-detects all 10 columns, and prints a summary showing "Parsed 83,633 flows from 10 columns" with detected column mapping — verified by unit tests and CLI output.

- [ ] **S02: Traffic Pre-Processing** `risk:medium` `depends:[S01]`
  > After this: 83K raw flows collapse into ~600 aggregated tuples with direction labels (inbound/outbound) and subnet grouping candidates (e.g. 133 IPs → 10.195.228.0/24) — verified by unit tests and Rich summary table displayed in terminal.

- [ ] **S03: Analysis Pipeline** `risk:high` `depends:[S02]`
  > After this: Full LangGraph pipeline (Analyze → Assess → Generate → Validate → Decide) produces risk-scored FW rule proposals with AI-generated justifications from Excel traffic data — displayed as Rich terminal report with token usage footer. NullAdapter handles no-FW mode.

- [ ] **S04: Change Request Form Export** `risk:medium` `depends:[S03]`
  > After this: `--export xlsx` produces a filled Excel change request form and `--export pdf` produces a formatted PDF, both containing all proposed rules with source, dest, port, protocol, direction, action, justification, and risk. `--template custom.xlsx` fills a user-provided template.

- [ ] **S05: CLI Integration & End-to-End** `risk:low` `depends:[S03, S04]`
  > After this: Complete end-to-end: `policyfoundry analyze --source excel --file traffic.xlsx --export xlsx` produces both Rich terminal output and a filled change request form. Integration tests prove all layers compose. All success criteria re-verified.

## Boundary Map

### S01 → S02

Produces:
- `ingestion/excel.py` → `ingest_excel_file(path, column_mapping=None) -> ExcelIngestionResult` — parses Excel, returns normalized traffic records
- `ingestion/excel_schema.py` → `ExcelTrafficRecord` Pydantic model (protocol, src_ip, src_port, dst_ip, dst_port, src_interface, dst_interface, src_hostname, dst_hostname, flag)
- `ingestion/excel_schema.py` → `ColumnMapping` Pydantic model for auto-detected or user-configured column positions
- `ingestion/excel_schema.py` → `ExcelIngestionResult` Pydantic model (records, column_mapping, stats, warnings)
- `ingestion/column_detect.py` → `detect_columns(headers: list[str]) -> ColumnMapping` — auto-detection from header names

Consumes:
- nothing (first slice)

### S01 → S05

Produces:
- `config/models.py` → `ExcelConfig` nested model added to `PolicyFoundryConfig` (column_mapping overrides)

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `analysis/aggregator.py` → `aggregate_flows(records: list[ExcelTrafficRecord]) -> list[AggregatedFlow]` — collapses raw flows into unique tuples with counts
- `analysis/direction.py` → `infer_direction(flow: ExcelTrafficRecord) -> Direction` — determines inbound/outbound from flags, interfaces, ports
- `analysis/subnet.py` → `group_to_subnets(flows: list[AggregatedFlow]) -> list[SubnetGroup]` — CIDR grouping of IPs with shared patterns
- `analysis/models.py` → `AggregatedFlow`, `SubnetGroup`, `DirectionLabel` Pydantic models

Consumes from S01:
- `ExcelTrafficRecord` model and `ExcelIngestionResult`

### S03 → S04

Produces:
- `pipeline/excel_graph.py` → `build_excel_pipeline() -> CompiledStateGraph` — LangGraph graph for Excel analysis
- `pipeline/excel_runner.py` → `async run_excel_pipeline(llm_client, records, adapter=None) -> ExcelPipelineState`
- `pipeline/excel_state.py` → `ExcelPipelineState` TypedDict with flow data, analysis, assessment, proposals, decisions
- `pipeline/excel_stages/` → analyze, assess, generate, validate, decide stage functions for Excel traffic
- `pipeline/excel_schema.py` → Pydantic output models for Excel-specific stages (may reuse/extend M001 models)
- `adapters/null.py` → `NullAdapter(FirewallAdapter)` — returns empty rules, pass-through validation

Consumes from S02:
- `AggregatedFlow`, `SubnetGroup` models and aggregation/direction/subnet functions

### S03 → S05

Produces:
- `output/excel_rich_output.py` → `format_excel_rich(state: ExcelPipelineState, console=None) -> None` — Rich terminal report
- `output/excel_json_output.py` → `format_excel_json(state: ExcelPipelineState) -> str` — JSON serialization

Consumes from S02:
- Pipeline produces structured output from aggregated flow data

### S04 → S05

Produces:
- `export/change_request.py` → `export_xlsx(state, output_path, template_path=None) -> Path` — Excel change request form
- `export/change_request.py` → `export_pdf(state, output_path) -> Path` — PDF change request form
- `export/models.py` → `ChangeRequestEntry` Pydantic model (source, dest, port, protocol, direction, action, justification, risk)
- `export/templates/default.xlsx` — built-in change request form template

Consumes from S03:
- `ExcelPipelineState` with decisions, proposals, and risk classifications

### S05 (terminal slice)

Produces:
- Updated `main.py` → `analyze` command extended with `--source excel`, `--file`, `--export`, `--template` options
- `tests/test_cli/test_excel_analyze.py` → CLI integration tests for the full Excel workflow
- End-to-end verification against sample data

Consumes from S01–S04:
- All modules listed above, composed through the CLI command
