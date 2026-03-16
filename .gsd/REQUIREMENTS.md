# Requirements

## Active

### ~~R101~~ → Validated (see Validated section)

### ~~R102~~ → Validated (see Validated section)

### ~~R103~~ → Validated (see Validated section)

### ~~R104~~ → Validated (see Validated section)

### ~~R105~~ → Validated (see Validated section)

### ~~R106~~ → Validated (see Validated section)

### ~~R107~~ → Validated (see Validated section)

### R108 — Rich terminal output showing proposed FW rules

- Class: core-capability
- Status: active
- Description: Proposed firewall rules are displayed in the terminal as Rich tables with color-coded risk levels, source/dest/port details, and justification summaries.
- Why it matters: The user needs to see and evaluate the suggestions before exporting.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: unmapped
- Notes: Extends the existing Rich output infrastructure from M001.

### ~~R109~~ → Validated (see Validated section)

### ~~R110~~ → Validated (see Validated section)

### ~~R111~~ → Validated (see Validated section)

### ~~R112~~ → Validated (see Validated section)

## Validated

### R101 — Excel traffic log ingestion with auto-detect column mapping

- Class: core-capability
- Status: validated
- Description: User can provide an Excel (.xlsx) file containing firewall traffic logs. The tool auto-detects column meanings from header names and normalizes the data for pipeline consumption.
- Why it matters: This is the primary input path for M002. Without flexible Excel parsing, the tool can't handle real-world traffic exports from different firewall vendors.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: validated
- Notes: Verified by 54 tests (schema, column detection, parsing) plus CLI demo parsing 83,633 rows with all 10 columns auto-detected. Handles whitespace stripping and DNS annotation cleanup.

### R102 — Config override for custom column mappings

- Class: core-capability
- Status: validated
- Description: User can provide a column mapping configuration (via config YAML or CLI flag) to override auto-detection when headers are non-standard.
- Why it matters: Different firewall vendors export different column layouts. Auto-detect covers common cases; config override covers the rest.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: validated
- Notes: Verified by TestColumnMappingOverride tests proving config override works with both standard and non-standard headers. ExcelConfig nested in PolicyFoundryConfig.

### R106 — Multi-stage LangGraph pipeline for Excel traffic analysis

- Class: core-capability
- Status: validated
- Description: A rigorous multi-stage LangGraph pipeline with multiple agent stages analyzes traffic, infers likely existing rules, generates proposals, validates them, and produces final risk-scored recommendations.
- Why it matters: This is the core intelligence. Multiple stages ensure cross-checking — not a single LLM call producing unchecked output.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: validated
- Notes: 5-node LangGraph (Analyze → Assess → Generate → Validate → Decide) verified by 27 stage unit tests + 9 pipeline integration tests with mock LLM. All stages compose end-to-end. NullAdapter default preserves adapter interface for M003.

### R107 — AI-generated business justification and risk per proposed rule

- Class: core-capability
- Status: validated
- Description: Each proposed firewall rule includes an AI-generated business justification explaining why the rule is needed and a risk classification (LOW/MEDIUM/HIGH/CRITICAL).
- Why it matters: Change request forms require justification text and risk assessment. The AI produces these so the user doesn't have to write them manually.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S04
- Validation: validated
- Notes: Generate stage produces PolicyProposal with justification field; Decide stage assigns risk classification and action (CREATE/SKIP). Verified by mock LLM structured output tests.

### R109 — FW change request form export to Excel (.xlsx)

- Class: core-capability
- Status: validated
- Description: User can export proposed rules as a filled-in Excel change request form with columns: source, destination, port, protocol, direction, action, justification, risk.
- Why it matters: Excel is the standard format for submitting change requests to network/security teams.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: validated
- Notes: 11 tests verify default styled workbook (metadata rows 1-5, header row 6, data rows), custom template fill with case-insensitive column matching, empty proposals, and error handling.

### R110 — FW change request form export to PDF

- Class: core-capability
- Status: validated
- Description: User can export proposed rules as a formatted PDF change request document.
- Why it matters: Some approval workflows require PDF documents rather than spreadsheets.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: validated
- Notes: 16 tests verify PDF structure (magic bytes), metadata header (title, date, run_id, source type, rule count), data rows (proposal IDs, actions, protocols), empty proposals ("No rules proposed."), and error handling with ExportError chaining.

### R111 — Custom template support for change request forms

- Class: core-capability
- Status: validated
- Description: User can provide their own Excel template via `--template` flag. The tool fills in rule data into the template's structure rather than using the built-in default.
- Why it matters: Every organization has their own change request form format. Custom templates let the tool fit into existing workflows.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: validated
- Notes: 2 template tests verify case-insensitive header matching (COLUMN_MAP synonym dict) and data insertion below existing headers. Supports single-row headers in row 1; complex templates (merged cells) not supported.

### R112 — Flexible adapter interface for future FW rule querying

- Class: core-capability
- Status: validated
- Description: The pipeline uses a NullAdapter when no real FW is available, but the adapter interface is ready for M003 where real FW rules will be queried and compared.
- Why it matters: Building the adapter seam now avoids a major refactor when live FW integration is added.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: validated
- Notes: NullAdapter implements FirewallAdapter ABC, registered in AdapterRegistry as built-in. 15 contract tests verify ABC compliance. Pipeline defaults to NullAdapter when no adapter provided. Assess stage infers from traffic patterns when rules are empty.

### OUT-01 — User can view analysis results in Rich terminal with color-coded risk tables and summary panels

- Class: core-capability
- Status: validated
- Description: Rich terminal output with color-coded risk tables verified by CLI integration tests.
- Why it matters: Primary user interface for reviewing analysis results.
- Source: inferred
- Primary owning slice: M001/S09
- Supporting slices: none
- Validation: validated
- Notes: Verified by 5 CLI integration tests.

### OUT-02 — User can export analysis results as machine-readable JSON

- Class: core-capability
- Status: validated
- Description: JSON export verified by test_analyze_json_output_is_valid_json.
- Why it matters: Machine-readable output for piping to other tools.
- Source: inferred
- Primary owning slice: M001/S09
- Supporting slices: none
- Validation: validated
- Notes: Verified by 4 CLI integration tests.

### SAFE-01 — Tool operates in suggest-only mode — no firewall changes are applied

- Class: core-capability
- Status: validated
- Description: ReadOnlyAdapter wraps all adapter access; SafetyError raised on write attempts.
- Why it matters: Safety-first approach; builds trust before auto-apply.
- Source: inferred
- Primary owning slice: M001/S09
- Supporting slices: none
- Validation: validated
- Notes: Verified by 7 tests (6 unit + 1 CLI integration).

### SAFE-02 — Each pipeline run tracks LLM token usage and estimated cost

- Class: core-capability
- Status: validated
- Description: TokenUsage with per-stage counts and cost displayed in both output formats.
- Why it matters: Cost visibility for LLM-powered analysis.
- Source: inferred
- Primary owning slice: M001/S09
- Supporting slices: none
- Validation: validated
- Notes: Verified in both Rich and JSON output.

### INFRA-01 — Terraform configuration bootstraps AWS test environment

- Class: core-capability
- Status: validated
- Description: Terraform HCL provisions VPC, Security Groups, Flow Logs.
- Why it matters: Reproducible test environment.
- Source: inferred
- Primary owning slice: M001/S10
- Supporting slices: none
- Validation: validated
- Notes: infra/terraform/ with 4 HCL files.

### INFRA-02 — Dockerfile and docker-compose.yml for containerized usage

- Class: core-capability
- Status: validated
- Description: Multi-stage Dockerfile and docker-compose.yml with Ollama sidecar.
- Why it matters: Containerized deployment.
- Source: inferred
- Primary owning slice: M001/S10
- Supporting slices: none
- Validation: validated
- Notes: Present and structurally valid.

### INGEST-01 — User can parse AWS VPC Flow Logs from local files

- Class: core-capability
- Status: validated
- Description: Async local file ingestion with glob expansion.
- Why it matters: Primary ingestion path for M001.
- Source: inferred
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: validated
- Notes: Verified by ingestion tests.

### INGEST-02 — User can parse AWS VPC Flow Logs from S3 buckets via boto3

- Class: core-capability
- Status: validated
- Description: S3 ingestion with prefix scan and gzip decompression.
- Why it matters: Production log source.
- Source: inferred
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: validated
- Notes: Verified by 12 moto-based tests.

### INGEST-03 — Parsed logs are normalized to unified 10-field schema

- Class: core-capability
- Status: validated
- Description: NormalizedFlowLog Pydantic model.
- Why it matters: Consistent schema for downstream processing.
- Source: inferred
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: validated
- Notes: Verified.

### INGEST-04 — Malformed log lines are skipped with warnings; duplicate records are deduplicated

- Class: core-capability
- Status: validated
- Description: SHA-256 dedup and malformed line handling.
- Why it matters: Data quality.
- Source: inferred
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: validated
- Notes: Verified.

### INGEST-05 — Normalized logs are stored as Parquet files and queryable via DuckDB

- Class: core-capability
- Status: validated
- Description: Parquet persistence with zstd compression and DuckDB analytics.
- Why it matters: Efficient storage and querying.
- Source: inferred
- Primary owning slice: M001/S04
- Supporting slices: none
- Validation: validated
- Notes: Verified.

### ADAPT-01 — User can fetch current AWS Security Group rules and view them in universal format

- Class: core-capability
- Status: validated
- Description: AWS SG adapter with boto3 client and rule translator.
- Why it matters: Rule visibility.
- Source: inferred
- Primary owning slice: M001/S05
- Supporting slices: none
- Validation: validated
- Notes: Verified.

### ADAPT-02 — Rules are represented in a vendor-neutral universal schema

- Class: core-capability
- Status: validated
- Description: UniversalRule with NetworkEndpoint.
- Why it matters: Vendor-neutral foundation.
- Source: inferred
- Primary owning slice: M001/S05
- Supporting slices: none
- Validation: validated
- Notes: Verified.

### ADAPT-03 — Proposed rule changes are validated against AWS SG constraints

- Class: core-capability
- Status: validated
- Description: 6-constraint validation in AwsSecurityGroupAdapter.
- Why it matters: Rules must be implementable.
- Source: inferred
- Primary owning slice: M001/S05
- Supporting slices: none
- Validation: validated
- Notes: Verified.

### PIPE-01 — User can run a 5-stage LangGraph AI pipeline

- Class: core-capability
- Status: validated
- Description: Analyze → Assess → Generate → Validate → Decide.
- Why it matters: Core intelligence pipeline.
- Source: inferred
- Primary owning slice: M001/S07
- Supporting slices: none
- Validation: validated
- Notes: 62 pipeline tests.

### PIPE-02 — Stage 1 (Analyze) interprets pre-aggregated traffic statistics

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S07
- Validation: validated

### PIPE-03 — Stage 2 (Assess) compares traffic patterns against current SG rules

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S07
- Validation: validated

### PIPE-04 — Stage 3 (Generate) produces vendor-neutral rule proposals with justification

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S07
- Validation: validated

### PIPE-05 — Stage 4 (Decide) assigns risk levels and determines CREATE/UPDATE/SKIP

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S07
- Validation: validated

### PIPE-06 — LLM calls route through LiteLLM with Ollama as default local provider

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S06
- Validation: validated

### CONF-01 — User can configure the tool via YAML file with environment variable overrides

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S02
- Validation: validated

### CONF-02 — User can set LLM provider, model, log sources, and target security groups in config

- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S02
- Validation: validated

## Deferred

### R201 — Query existing FW rules and compare against proposed rules

- Class: core-capability
- Status: deferred
- Description: Connect to a live firewall, fetch current rules, and compare against AI-proposed rules to identify gaps, redundancies, and conflicts.
- Why it matters: Comparing proposals against reality produces better recommendations and avoids duplicating existing rules.
- Source: user
- Primary owning slice: M003 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M003. M002 builds the flexible adapter seam to support this.

### R202 — Analyze existing FW policies for gaps and redundancies

- Class: core-capability
- Status: deferred
- Description: Analyze an existing firewall policy set for overly permissive rules, redundancies, and security gaps without traffic data.
- Why it matters: Policy hygiene independent of traffic analysis.
- Source: user
- Primary owning slice: M003 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M003.

## Out of Scope

### R301 — Auto-apply firewall rules

- Class: anti-feature
- Status: out-of-scope
- Description: Automatically applying proposed rules to a live firewall without human approval.
- Why it matters: Prevents accidental scope creep into dangerous auto-apply territory. Suggest-only is the product philosophy.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: May be revisited with graduated autonomy in a much later milestone.

### R302 — Real-time streaming traffic analysis

- Class: constraint
- Status: out-of-scope
- Description: Processing live traffic streams rather than batch Excel/log files.
- Why it matters: Prevents scope creep into streaming infrastructure. Batch is the current approach.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: none

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R101 | core-capability | validated | M002/S01 | none | validated |
| R102 | core-capability | validated | M002/S01 | none | validated |
| R103 | core-capability | active | M002/S02 | none | unmapped |
| R104 | core-capability | active | M002/S02 | none | unmapped |
| R105 | core-capability | active | M002/S02 | M002/S03 | unmapped |
| R106 | core-capability | validated | M002/S03 | none | validated |
| R107 | core-capability | validated | M002/S03 | M002/S04 | validated |
| R108 | core-capability | active | M002/S05 | none | unmapped |
| R109 | core-capability | validated | M002/S04 | none | validated |
| R110 | core-capability | validated | M002/S04 | none | validated |
| R111 | core-capability | validated | M002/S04 | none | validated |
| R112 | core-capability | validated | M002/S03 | none | validated |
| R201 | core-capability | deferred | M003 | none | unmapped |
| R202 | core-capability | deferred | M003 | none | unmapped |
| R301 | anti-feature | out-of-scope | none | none | n/a |
| R302 | constraint | out-of-scope | none | none | n/a |
| OUT-01 | core-capability | validated | M001/S09 | none | validated |
| OUT-02 | core-capability | validated | M001/S09 | none | validated |
| SAFE-01 | core-capability | validated | M001/S09 | none | validated |
| SAFE-02 | core-capability | validated | M001/S09 | none | validated |
| INFRA-01 | core-capability | validated | M001/S10 | none | validated |
| INFRA-02 | core-capability | validated | M001/S10 | none | validated |
| INGEST-01 | core-capability | validated | M001/S03 | none | validated |
| INGEST-02 | core-capability | validated | M001/S03 | none | validated |
| INGEST-03 | core-capability | validated | M001/S03 | none | validated |
| INGEST-04 | core-capability | validated | M001/S03 | none | validated |
| INGEST-05 | core-capability | validated | M001/S04 | none | validated |
| ADAPT-01 | core-capability | validated | M001/S05 | none | validated |
| ADAPT-02 | core-capability | validated | M001/S05 | none | validated |
| ADAPT-03 | core-capability | validated | M001/S05 | none | validated |
| PIPE-01 | core-capability | validated | M001/S07 | none | validated |
| PIPE-02 | core-capability | validated | M001/S07 | none | validated |
| PIPE-03 | core-capability | validated | M001/S07 | none | validated |
| PIPE-04 | core-capability | validated | M001/S07 | none | validated |
| PIPE-05 | core-capability | validated | M001/S07 | none | validated |
| PIPE-06 | core-capability | validated | M001/S06 | none | validated |
| CONF-01 | core-capability | validated | M001/S02 | none | validated |
| CONF-02 | core-capability | validated | M001/S02 | none | validated |

## Coverage Summary

- Active requirements: 4
- Mapped to slices: 4
- Validated: 30 (22 from M001, 2 from M002/S01, 3 from M002/S03, 3 from M002/S04)
- Deferred: 2 (M003)
- Out of scope: 2
- Unmapped active requirements: 0
