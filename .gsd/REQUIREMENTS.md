# Requirements

This file is the explicit capability and coverage contract for the project.

Use it to track what is actively in scope, what has been validated by completed work, what is intentionally deferred, and what is explicitly out of scope.

Guidelines:
- Keep requirements capability-oriented, not a giant feature wishlist.
- Requirements should be atomic, testable, and stated in plain language.
- Every **Active** requirement should be mapped to a slice, deferred, blocked with reason, or moved out of scope.
- Each requirement should have one accountable primary owner and may have supporting slices.
- Research may suggest requirements, but research does not silently make them binding.
- Validation means the requirement was actually proven by completed work and verification, not just discussed.

## Active

### R401 — No silent failures in output rendering or export
- Class: failure-visibility
- Status: active
- Description: Output rendering errors and export failures must surface visible diagnostics, not be swallowed by bare `except Exception` blocks. Template export with no matching columns must raise an error, not produce an empty file with a success message.
- Why it matters: Silent failures mean the user gets wrong or missing output and has no way to know. A success message on empty export is actively misleading.
- Source: execution
- Primary owning slice: M003-2heki1/S02
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issues #1, #2, #5, #8. Eight bare `except Exception` blocks in rich_output.py and excel_rich_output.py; silent return in template fill; swallowed ImportError in registry; orphaned decisions dropped silently.

### R402 — LLM prompts reference correct data model field names
- Class: quality-attribute
- Status: active
- Description: LLM prompt text must accurately describe the data models being sent. Field names referenced in prompts must match the actual Pydantic model fields.
- Why it matters: The generate prompt tells the LLM that `shared_patterns` contains a `counterpart_ip` key — this key never exists (actual keys are `dst_ip`/`src_ip`). This causes the LLM to hallucinate or ignore subnet data.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issue #3.

### R403 — Pipeline errors report the actual failing stage
- Class: failure-visibility
- Status: active
- Description: When the Excel pipeline fails, the error must report which stage actually failed, not always report `"starting"`.
- Why it matters: The error handler reads `current_stage` from `initial_state` (always `"starting"`) instead of the evolved state. Every failure reports the wrong stage, making debugging blind.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issue #4.

### R404 — Token usage tracks per-stage metrics for all LLM calls
- Class: operability
- Status: active
- Description: All LLM-calling pipeline stages must pass the `stage=` parameter to `llm_client.complete()` so that token usage is tracked per-stage, not all reported as `"unknown"`.
- Why it matters: Without stage labels, the token usage breakdown in output is useless — every call shows as "unknown" stage.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issue #6. Affects all 4 Excel stages AND all 4 VPC stages (8 calls total).

### R405 — Dropped/rejected data is logged, not silently discarded
- Class: failure-visibility
- Status: active
- Description: When proposals are rejected during validation or decisions reference missing proposals, the drop must be logged with context. Zero local error handling in pipeline stages must be addressed with stage-specific error wrapping.
- Why it matters: Silent drops make it impossible to diagnose why expected rules don't appear in output.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: M003-2heki1/S02
- Validation: mapped
- Notes: Covers PR review issues #7, #9. Validate stage silently drops rejected proposals; all pipeline stages have zero local error handling.

### R406 — Type safety for control-flow fields and model consistency
- Class: quality-attribute
- Status: active
- Description: `RuleDecision.action` must be an enum (not bare `str`) since it drives control flow (`"SKIP"` check). `SubnetGroup.member_count` must have a consistency validator ensuring it equals `len(member_ips)`.
- Why it matters: Bare string for action means typos silently change behavior. Divergent member_count produces incorrect subnet grouping metadata.
- Source: execution
- Primary owning slice: M003-2heki1/S03
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issues #10, #11.

### R407 — Code correctness in subnet dedup and construction patterns
- Class: quality-attribute
- Status: active
- Description: Fix incorrect `dict[str, Any](usage_raw)` construction pattern and subnet dedup logic that can incorrectly drop groups before the merge step.
- Why it matters: The dict construction is confusing and non-standard. The subnet dedup `break`/`else: continue` pattern may silently drop valid groups.
- Source: execution
- Primary owning slice: M003-2heki1/S03
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issues #12, #13.

### R501 — .env file loading integrated into config priority chain
- Class: core-capability
- Status: active
- Description: PolicyFoundry loads secrets and configuration from `.env` files in the project directory using pydantic-settings' native DotEnvSettingsSource. Priority: init → env vars → .env → keychain → local YAML → global YAML.
- Why it matters: Users need a standard way to set API keys without exporting env vars or risking secrets in YAML config files.
- Source: user
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: pydantic-settings has native `env_file` support — no new dependency needed.

### R502 — OS credential store integration (macOS Keychain, Windows Credential Manager)
- Class: core-capability
- Status: active
- Description: API keys and secrets can be stored in the OS credential store (macOS Keychain, Windows Credential Manager) via the `keyring` library. The config system checks the credential store as part of the merge chain.
- Why it matters: Secrets in plaintext files (YAML, .env) can be committed accidentally. OS credential stores are encrypted, access-controlled, and never in the repo.
- Source: user
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: macOS + Windows only. Linux users fall back to .env / env vars. `keyring` is an optional dependency.

### R503 — Secret management CLI commands (set/get/delete)
- Class: core-capability
- Status: active
- Description: `policyfoundry secret set/get/delete` subcommands allow users to manage secrets in the OS credential store from the terminal.
- Why it matters: Users need a discoverable way to store and manage secrets without touching config files.
- Source: user
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: Masked output for get. Prompts for secret value on set (no command-line argument for the value itself).

### R504 — Graceful fallback when keyring package not installed
- Class: quality-attribute
- Status: active
- Description: When `keyring` is not installed, PolicyFoundry skips the credential store layer silently and falls back to .env / env vars / YAML. No import errors, no warnings unless the user explicitly tries `policyfoundry secret` commands.
- Why it matters: keyring is an optional dependency — the tool must work without it.
- Source: inferred
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: Optional dependency pattern via try/except ImportError.

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

### R103 — Traffic flow aggregation
- Class: core-capability
- Status: validated
- Description: Raw traffic flows are aggregated into unique tuples with flow counts, collapsing thousands of individual records into manageable groups for analysis.
- Why it matters: Without aggregation, the pipeline would process 83K individual flows instead of ~600 meaningful tuples — exceeding LLM context limits and producing per-connection rules instead of grouped policies.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: validated
- Notes: Verified by 12 aggregation tests proving dedup, counting, service port keying, and ephemeral port exclusion. 83K raw flows collapse to ~603 aggregated tuples.

### R104 — Direction inference
- Class: core-capability
- Status: validated
- Description: The tool infers traffic direction (inbound/outbound) from flags, interfaces, and well-known port analysis using a multi-signal heuristic.
- Why it matters: Direction determines source vs destination in firewall rules. Incorrect inference produces wrong rules. The vendor-specific flag values (U/UI/UIO) require careful interpretation.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: validated
- Notes: Verified by 27 parametrised direction inference tests covering all signal combinations (well-known port, interface zone, flag, both-ephemeral fallback). 4-signal heuristic with UNKNOWN fallback for ambiguous cases.

### R105 — Subnet grouping
- Class: core-capability
- Status: validated
- Description: Individual IP addresses sharing traffic patterns are grouped into CIDR subnets for more manageable firewall rules.
- Why it matters: 133 individual IPs collapsing to subnet-based rules produces cleaner, more maintainable firewall policies.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S03
- Validation: validated
- Notes: Verified by 13 subnet grouping tests proving /24 candidates, min 2 IPs, pattern matching, custom prefix lengths. Subnet candidates passed to LLM for final grouping decision (D042).

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

### R108 — Rich terminal output showing proposed FW rules
- Class: core-capability
- Status: validated
- Description: Proposed firewall rules are displayed in the terminal as Rich tables with color-coded risk levels, source/dest/port details, and justification summaries.
- Why it matters: The user needs to see and evaluate the suggestions before exporting.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: validated
- Notes: Verified by 4 CLI integration tests (exit code, pipeline summary panel, decisions section, token usage) + 2 end-to-end composition tests. Excel-specific summary panel with direction breakdown and subnet candidates, followed by shared renderers for analysis, proposals, decisions, and token usage.

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
- Source: inferred
- Primary owning slice: M001/S09
- Validation: validated
- Notes: Verified by 5 CLI integration tests.

### OUT-02 — User can export analysis results as machine-readable JSON
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S09
- Validation: validated
- Notes: Verified by 4 CLI integration tests.

### SAFE-01 — Tool operates in suggest-only mode — no firewall changes are applied
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S09
- Validation: validated
- Notes: Verified by 7 tests (6 unit + 1 CLI integration).

### SAFE-02 — Each pipeline run tracks LLM token usage and estimated cost
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S09
- Validation: validated
- Notes: Verified in both Rich and JSON output.

### INFRA-01 — Terraform configuration bootstraps AWS test environment
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S10
- Validation: validated
- Notes: infra/terraform/ with 4 HCL files.

### INFRA-02 — Dockerfile and docker-compose.yml for containerized usage
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S10
- Validation: validated
- Notes: Present and structurally valid.

### INGEST-01 — User can parse AWS VPC Flow Logs from local files
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S03
- Validation: validated

### INGEST-02 — User can parse AWS VPC Flow Logs from S3 buckets via boto3
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S03
- Validation: validated

### INGEST-03 — Parsed logs are normalized to unified 10-field schema
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S03
- Validation: validated

### INGEST-04 — Malformed log lines are skipped with warnings; duplicate records are deduplicated
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S03
- Validation: validated

### INGEST-05 — Normalized logs are stored as Parquet files and queryable via DuckDB
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S04
- Validation: validated

### ADAPT-01 — User can fetch current AWS Security Group rules and view them in universal format
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S05
- Validation: validated

### ADAPT-02 — Rules are represented in a vendor-neutral universal schema
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S05
- Validation: validated

### ADAPT-03 — Proposed rule changes are validated against AWS SG constraints
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S05
- Validation: validated

### PIPE-01 — User can run a 5-stage LangGraph AI pipeline
- Class: core-capability
- Status: validated
- Source: inferred
- Primary owning slice: M001/S07
- Validation: validated

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
- Primary owning slice: future
- Supporting slices: none
- Validation: unmapped
- Notes: Originally M003 provisional. Bumped to future milestone — M003 is now PR fixes, M004 is secrets.

### R202 — Analyze existing FW policies for gaps and redundancies
- Class: core-capability
- Status: deferred
- Description: Analyze an existing firewall policy set for overly permissive rules, redundancies, and security gaps without traffic data.
- Why it matters: Policy hygiene independent of traffic analysis.
- Source: user
- Primary owning slice: future
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to future milestone.

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
| R401 | failure-visibility | active | M003-2heki1/S02 | none | mapped |
| R402 | quality-attribute | active | M003-2heki1/S01 | none | mapped |
| R403 | failure-visibility | active | M003-2heki1/S01 | none | mapped |
| R404 | operability | active | M003-2heki1/S01 | none | mapped |
| R405 | failure-visibility | active | M003-2heki1/S01 | M003-2heki1/S02 | mapped |
| R406 | quality-attribute | active | M003-2heki1/S03 | none | mapped |
| R407 | quality-attribute | active | M003-2heki1/S03 | none | mapped |
| R501 | core-capability | active | M004 | none | unmapped |
| R502 | core-capability | active | M004 | none | unmapped |
| R503 | core-capability | active | M004 | none | unmapped |
| R504 | quality-attribute | active | M004 | none | unmapped |
| R101 | core-capability | validated | M002/S01 | none | validated |
| R102 | core-capability | validated | M002/S01 | none | validated |
| R103 | core-capability | validated | M002/S02 | none | validated |
| R104 | core-capability | validated | M002/S02 | none | validated |
| R105 | core-capability | validated | M002/S02 | M002/S03 | validated |
| R106 | core-capability | validated | M002/S03 | none | validated |
| R107 | core-capability | validated | M002/S03 | M002/S04 | validated |
| R108 | core-capability | validated | M002/S05 | none | validated |
| R109 | core-capability | validated | M002/S04 | none | validated |
| R110 | core-capability | validated | M002/S04 | none | validated |
| R111 | core-capability | validated | M002/S04 | none | validated |
| R112 | core-capability | validated | M002/S03 | none | validated |
| R201 | core-capability | deferred | future | none | unmapped |
| R202 | core-capability | deferred | future | none | unmapped |
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

- Active requirements: 11 (7 for M003-2heki1, 4 for M004)
- Mapped to slices: 7 (M003-2heki1)
- Validated: 34 (22 from M001, 12 from M002)
- Deferred: 2
- Out of scope: 2
- Unmapped active requirements: 4 (M004 provisional)
