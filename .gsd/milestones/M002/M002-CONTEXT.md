# M002: Excel Traffic Analysis & Change Request Forms — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

## Project Description

Add an Excel-based traffic analysis mode to the existing PolicyFoundry CLI. Users provide a firewall traffic export spreadsheet, and the tool runs a multi-stage LangGraph pipeline to produce justified, risk-scored firewall rule proposals — exportable as formal change request forms (Excel and PDF).

## Why This Milestone

Security teams routinely export traffic logs from firewalls as Excel files. Today, a human analyst manually reads thousands of rows, groups traffic patterns, decides what rules are needed, writes justifications, and fills out change request forms. This is tedious, error-prone, and slow. M002 automates the entire workflow: Excel in → AI analysis → change request form out.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `policyfoundry analyze --source excel --file traffic.xlsx` and see a Rich terminal report with proposed FW rules, risk levels, and justifications
- Run `policyfoundry analyze --source excel --file traffic.xlsx --export xlsx` and get a filled-in FW change request form as an Excel file
- Run `policyfoundry analyze --source excel --file traffic.xlsx --export pdf` and get a formatted PDF change request document
- Use `--template custom.xlsx` to fill in their organization's specific form layout
- See subnet-grouped rules (not per-IP) where traffic patterns support it

### Entry point / environment

- Entry point: `policyfoundry analyze --source excel` CLI command (extends existing command)
- Environment: local dev, Docker container
- Live dependencies involved: Ollama (or other LLM provider via LiteLLM) — no firewall connection in this milestone

## Completion Class

- Contract complete means: all pipeline stages produce correct structured output from Excel input, tests verify each stage independently
- Integration complete means: end-to-end CLI command produces Rich output, JSON, Excel export, and PDF export from the sample traffic file
- Operational complete means: none for this milestone (no new services)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `policyfoundry analyze --source excel --file referance/samples/test-FW501_20260219_All_App1-updated.xlsx` produces a Rich report with aggregated rule proposals
- The same command with `--export xlsx` produces a readable, filled-in change request form
- The same command with `--export pdf` produces a formatted PDF document
- The pipeline uses multiple LangGraph agent stages (not a single LLM call)
- Rules show subnet grouping where appropriate (the 133 destination IPs in the sample should collapse)

## Risks and Unknowns

- **Excel format variability** — Different FW vendors export wildly different column layouts. Auto-detection must be robust, and fallback to config override must work.
- **LLM context window limits** — 600 aggregated flow tuples may still be too large for a single prompt. May need chunking or summarization before the analyze stage.
- **Direction inference accuracy** — The flag values (U/UI/UIO) are vendor-specific. Inferring direction correctly requires understanding the specific FW export format.
- **PDF generation quality** — Python PDF libraries vary in output quality. Need to pick the right library and handle formatting edge cases.
- **Subnet grouping heuristics** — Over-aggressive grouping (e.g. /16 when /24 is more appropriate) produces rules that are too permissive. The AI must balance specificity vs. manageability.

## Existing Codebase / Prior Art

- `src/policyfoundry/main.py` — Typer CLI with `analyze` command. Must extend `--source` to accept `excel` and add `--file`, `--export`, `--template` options.
- `src/policyfoundry/ingestion/` — VPC Flow Log parsers. Excel ingestion is a new parallel path, not a modification of existing parsers.
- `src/policyfoundry/pipeline/graph.py` — LangGraph StateGraph builder. Need a new graph (or adapted graph) for Excel traffic analysis.
- `src/policyfoundry/pipeline/stages/` — Existing 5-stage pipeline. New stages will follow the same pattern (async function, Runtime[PipelineContext], structured output).
- `src/policyfoundry/pipeline/llm.py` — LLMClient with Instructor. Reused as-is.
- `src/policyfoundry/pipeline/schema.py` — TrafficAnalysis, PolicyProposal, RuleDecision models. May extend or create new models for Excel analysis.
- `src/policyfoundry/adapters/base.py` — FirewallAdapter ABC. Need a NullAdapter for no-FW mode.
- `src/policyfoundry/adapters/safety.py` — ReadOnlyAdapter. Reused as-is.
- `src/policyfoundry/output/rich_output.py` — Rich formatter. Must extend for new rule proposal format.
- `src/policyfoundry/output/json_output.py` — JSON formatter. Must extend for new output.
- `referance/samples/test-FW501_20260219_All_App1-updated.xlsx` — Sample Excel file with 83,633 rows, 10 columns (Protocol, Interface1, HostName1, IP1, Port1, Interface2, HostName2, IP2, Port2, Flag).

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R101–R112: All active M002 requirements
- R112: Flexible adapter interface — critical for M003 future work
- PIPE-01 through PIPE-06: Validated pipeline patterns to follow

## Scope

### In Scope

- Excel traffic log parsing with auto-detect column mapping
- Config override for custom column mappings
- Traffic flow aggregation and deduplication
- Direction inference from flags, interfaces, and port analysis
- Subnet-based CIDR grouping of individual IPs
- Multi-stage LangGraph pipeline (analyze → assess → generate → validate → decide)
- NullAdapter for no-FW mode (assess stage infers from patterns)
- Rich terminal output with proposed rules
- JSON export of pipeline results
- Excel (.xlsx) change request form export
- PDF change request form export
- Custom template support via `--template` flag
- CLI integration via `--source excel --file <path>`

### Out of Scope / Non-Goals

- Querying live firewall rules (M003)
- Modifying existing M001 VPC Flow Log pipeline
- Auto-apply of suggested rules
- Real-time streaming analysis
- Non-Excel input formats (CSV, JSON traffic logs) — may add later but not in scope

## Technical Constraints

- Must extend existing CLI, not create a separate tool
- Must use LangGraph for pipeline orchestration (same rigor as M001)
- Must use Instructor + LiteLLM for structured LLM output (reuse existing LLMClient)
- openpyxl for Excel reading, openpyxl + reportlab/weasyprint for Excel/PDF export
- Adapter interface must remain backward-compatible with AWS SG adapter from M001

## Integration Points

- Existing `policyfoundry analyze` command — extended with new `--source excel` mode
- Existing `PolicyFoundryConfig` — extended with Excel-specific config (column mappings)
- Existing `LLMClient` — reused directly, no changes needed
- Existing `FirewallAdapter` ABC — NullAdapter implements the same interface

## Open Questions

- Exact PDF library choice (reportlab vs weasyprint vs fpdf2) — decide during S04 research
- Whether the change request form needs a "request metadata" header section (requester name, date, ticket number) — decide during S04 planning

## Sample Data Profile

From `referance/samples/test-FW501_20260219_All_App1-updated.xlsx`:
- 83,633 data rows, 1 sheet, 10 columns
- All TCP traffic, interfaces: inet ↔ zoneA
- 7 unique source IPs, 133 unique destination IPs
- Top ports: 80 (77,873 flows), 443 (4,461 flows), 5274 (529 flows)
- Flags: UIO (82,017), UI (1,600), U (16)
- Collapses to ~603 unique (src, dst, port, proto) tuples
- Hostnames are auto-generated (hostname1..hostname435, name1..name79221)
- Values have trailing whitespace, some IPs have "(no DNS resolution)" annotations
