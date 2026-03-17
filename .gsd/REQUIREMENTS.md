# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R401 — Output rendering errors and export failures must surface visible diagnostics, not be swallowed by bare `except Exception` blocks. Template export with no matching columns must raise an error, not produce an empty file with a success message.
- Class: failure-visibility
- Status: active
- Description: Output rendering errors and export failures must surface visible diagnostics, not be swallowed by bare `except Exception` blocks. Template export with no matching columns must raise an error, not produce an empty file with a success message.
- Why it matters: Silent failures mean the user gets wrong or missing output and has no way to know. A success message on empty export is actively misleading.
- Source: execution
- Primary owning slice: M003-2heki1/S02
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issues #1, #2, #5, #8. Eight bare `except Exception` blocks in rich_output.py and excel_rich_output.py; silent return in template fill; swallowed ImportError in registry; orphaned decisions dropped silently.

### R406 — `RuleDecision.action` must be an enum (not bare `str`) since it drives control flow (`"SKIP"` check). `SubnetGroup.member_count` must have a consistency validator ensuring it equals `len(member_ips)`.
- Class: quality-attribute
- Status: active
- Description: `RuleDecision.action` must be an enum (not bare `str`) since it drives control flow (`"SKIP"` check). `SubnetGroup.member_count` must have a consistency validator ensuring it equals `len(member_ips)`.
- Why it matters: Bare string for action means typos silently change behavior. Divergent member_count produces incorrect subnet grouping metadata.
- Source: execution
- Primary owning slice: M003-2heki1/S03
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issues #10, #11.

### R407 — Fix incorrect `dict[str, Any](usage_raw)` construction pattern and subnet dedup logic that can incorrectly drop groups before the merge step.
- Class: quality-attribute
- Status: active
- Description: Fix incorrect `dict[str, Any](usage_raw)` construction pattern and subnet dedup logic that can incorrectly drop groups before the merge step.
- Why it matters: The dict construction is confusing and non-standard. The subnet dedup `break`/`else: continue` pattern may silently drop valid groups.
- Source: execution
- Primary owning slice: M003-2heki1/S03
- Supporting slices: none
- Validation: mapped
- Notes: Covers PR review issues #12, #13.

### R501 — PolicyFoundry loads secrets and configuration from `.env` files in the project directory using pydantic-settings' native DotEnvSettingsSource. Priority: init → env vars → .env → keychain → local YAML → global YAML.
- Class: core-capability
- Status: active
- Description: PolicyFoundry loads secrets and configuration from `.env` files in the project directory using pydantic-settings' native DotEnvSettingsSource. Priority: init → env vars → .env → keychain → local YAML → global YAML.
- Why it matters: Users need a standard way to set API keys without exporting env vars or risking secrets in YAML config files.
- Source: user
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: pydantic-settings has native `env_file` support — no new dependency needed.

### R502 — API keys and secrets can be stored in the OS credential store (macOS Keychain, Windows Credential Manager) via the `keyring` library. The config system checks the credential store as part of the merge chain.
- Class: core-capability
- Status: active
- Description: API keys and secrets can be stored in the OS credential store (macOS Keychain, Windows Credential Manager) via the `keyring` library. The config system checks the credential store as part of the merge chain.
- Why it matters: Secrets in plaintext files (YAML, .env) can be committed accidentally. OS credential stores are encrypted, access-controlled, and never in the repo.
- Source: user
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: macOS + Windows only. Linux users fall back to .env / env vars. `keyring` is an optional dependency.

### R503 — `policyfoundry secret set/get/delete` subcommands allow users to manage secrets in the OS credential store from the terminal.
- Class: core-capability
- Status: active
- Description: `policyfoundry secret set/get/delete` subcommands allow users to manage secrets in the OS credential store from the terminal.
- Why it matters: Users need a discoverable way to store and manage secrets without touching config files.
- Source: user
- Primary owning slice: M004 (provisional)
- Supporting slices: none
- Validation: unmapped
- Notes: Masked output for get. Prompts for secret value on set (no command-line argument for the value itself).

### R504 — When `keyring` is not installed, PolicyFoundry skips the credential store layer silently and falls back to .env / env vars / YAML. No import errors, no warnings unless the user explicitly tries `policyfoundry secret` commands.
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

### R101 — User can provide an Excel (.xlsx) file containing firewall traffic logs. The tool auto-detects column meanings from header names and normalizes the data for pipeline consumption.
- Class: core-capability
- Status: validated
- Description: User can provide an Excel (.xlsx) file containing firewall traffic logs. The tool auto-detects column meanings from header names and normalizes the data for pipeline consumption.
- Why it matters: This is the primary input path for M002. Without flexible Excel parsing, the tool can't handle real-world traffic exports from different firewall vendors.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: validated
- Notes: Verified by 54 tests (schema, column detection, parsing) plus CLI demo parsing 83,633 rows with all 10 columns auto-detected. Handles whitespace stripping and DNS annotation cleanup.

### R102 — User can provide a column mapping configuration (via config YAML or CLI flag) to override auto-detection when headers are non-standard.
- Class: core-capability
- Status: validated
- Description: User can provide a column mapping configuration (via config YAML or CLI flag) to override auto-detection when headers are non-standard.
- Why it matters: Different firewall vendors export different column layouts. Auto-detect covers common cases; config override covers the rest.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: validated
- Notes: Verified by TestColumnMappingOverride tests proving config override works with both standard and non-standard headers. ExcelConfig nested in PolicyFoundryConfig.

### R103 — Raw traffic flows are aggregated into unique tuples with flow counts, collapsing thousands of individual records into manageable groups for analysis.
- Class: core-capability
- Status: validated
- Description: Raw traffic flows are aggregated into unique tuples with flow counts, collapsing thousands of individual records into manageable groups for analysis.
- Why it matters: Without aggregation, the pipeline would process 83K individual flows instead of ~600 meaningful tuples — exceeding LLM context limits and producing per-connection rules instead of grouped policies.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: validated
- Notes: Verified by 12 aggregation tests proving dedup, counting, service port keying, and ephemeral port exclusion. 83K raw flows collapse to ~603 aggregated tuples.

### R104 — The tool infers traffic direction (inbound/outbound) from flags, interfaces, and well-known port analysis using a multi-signal heuristic.
- Class: core-capability
- Status: validated
- Description: The tool infers traffic direction (inbound/outbound) from flags, interfaces, and well-known port analysis using a multi-signal heuristic.
- Why it matters: Direction determines source vs destination in firewall rules. Incorrect inference produces wrong rules. The vendor-specific flag values (U/UI/UIO) require careful interpretation.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: validated
- Notes: Verified by 27 parametrised direction inference tests covering all signal combinations (well-known port, interface zone, flag, both-ephemeral fallback). 4-signal heuristic with UNKNOWN fallback for ambiguous cases.

### R105 — Individual IP addresses sharing traffic patterns are grouped into CIDR subnets for more manageable firewall rules.
- Class: core-capability
- Status: validated
- Description: Individual IP addresses sharing traffic patterns are grouped into CIDR subnets for more manageable firewall rules.
- Why it matters: 133 individual IPs collapsing to subnet-based rules produces cleaner, more maintainable firewall policies.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S03
- Validation: validated
- Notes: Verified by 13 subnet grouping tests proving /24 candidates, min 2 IPs, pattern matching, custom prefix lengths. Subnet candidates passed to LLM for final grouping decision (D042).

### R106 — A rigorous multi-stage LangGraph pipeline with multiple agent stages analyzes traffic, infers likely existing rules, generates proposals, validates them, and produces final risk-scored recommendations.
- Class: core-capability
- Status: validated
- Description: A rigorous multi-stage LangGraph pipeline with multiple agent stages analyzes traffic, infers likely existing rules, generates proposals, validates them, and produces final risk-scored recommendations.
- Why it matters: This is the core intelligence. Multiple stages ensure cross-checking — not a single LLM call producing unchecked output.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: validated
- Notes: 5-node LangGraph (Analyze → Assess → Generate → Validate → Decide) verified by 27 stage unit tests + 9 pipeline integration tests with mock LLM. All stages compose end-to-end. NullAdapter default preserves adapter interface for M003.

### R107 — Each proposed firewall rule includes an AI-generated business justification explaining why the rule is needed and a risk classification (LOW/MEDIUM/HIGH/CRITICAL).
- Class: core-capability
- Status: validated
- Description: Each proposed firewall rule includes an AI-generated business justification explaining why the rule is needed and a risk classification (LOW/MEDIUM/HIGH/CRITICAL).
- Why it matters: Change request forms require justification text and risk assessment. The AI produces these so the user doesn't have to write them manually.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S04
- Validation: validated
- Notes: Generate stage produces PolicyProposal with justification field; Decide stage assigns risk classification and action (CREATE/SKIP). Verified by mock LLM structured output tests.

### R108 — Proposed firewall rules are displayed in the terminal as Rich tables with color-coded risk levels, source/dest/port details, and justification summaries.
- Class: core-capability
- Status: validated
- Description: Proposed firewall rules are displayed in the terminal as Rich tables with color-coded risk levels, source/dest/port details, and justification summaries.
- Why it matters: The user needs to see and evaluate the suggestions before exporting.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: validated
- Notes: Verified by 4 CLI integration tests (exit code, pipeline summary panel, decisions section, token usage) + 2 end-to-end composition tests. Excel-specific summary panel with direction breakdown and subnet candidates, followed by shared renderers for analysis, proposals, decisions, and token usage.

### R109 — User can export proposed rules as a filled-in Excel change request form with columns: source, destination, port, protocol, direction, action, justification, risk.
- Class: core-capability
- Status: validated
- Description: User can export proposed rules as a filled-in Excel change request form with columns: source, destination, port, protocol, direction, action, justification, risk.
- Why it matters: Excel is the standard format for submitting change requests to network/security teams.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: validated
- Notes: 11 tests verify default styled workbook (metadata rows 1-5, header row 6, data rows), custom template fill with case-insensitive column matching, empty proposals, and error handling.

### R110 — User can export proposed rules as a formatted PDF change request document.
- Class: core-capability
- Status: validated
- Description: User can export proposed rules as a formatted PDF change request document.
- Why it matters: Some approval workflows require PDF documents rather than spreadsheets.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: validated
- Notes: 16 tests verify PDF structure (magic bytes), metadata header (title, date, run_id, source type, rule count), data rows (proposal IDs, actions, protocols), empty proposals ("No rules proposed."), and error handling with ExportError chaining.

### R111 — User can provide their own Excel template via `--template` flag. The tool fills in rule data into the template's structure rather than using the built-in default.
- Class: core-capability
- Status: validated
- Description: User can provide their own Excel template via `--template` flag. The tool fills in rule data into the template's structure rather than using the built-in default.
- Why it matters: Every organization has their own change request form format. Custom templates let the tool fit into existing workflows.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: validated
- Notes: 2 template tests verify case-insensitive header matching (COLUMN_MAP synonym dict) and data insertion below existing headers. Supports single-row headers in row 1; complex templates (merged cells) not supported.

### R112 — The pipeline uses a NullAdapter when no real FW is available, but the adapter interface is ready for M003 where real FW rules will be queried and compared.
- Class: core-capability
- Status: validated
- Description: The pipeline uses a NullAdapter when no real FW is available, but the adapter interface is ready for M003 where real FW rules will be queried and compared.
- Why it matters: Building the adapter seam now avoids a major refactor when live FW integration is added.
- Source: inferred
- Primary owning slice: M001/S02
- Supporting slices: none
- Validation: validated
- Notes: Present and structurally valid.

### R402 — LLM prompt text must accurately describe the data models being sent. Field names referenced in prompts must match the actual Pydantic model fields.
- Class: quality-attribute
- Status: validated
- Description: LLM prompt text must accurately describe the data models being sent. Field names referenced in prompts must match the actual Pydantic model fields.
- Why it matters: The generate prompt tells the LLM that `shared_patterns` contains a `counterpart_ip` key — this key never exists (actual keys are `dst_ip`/`src_ip`). This causes the LLM to hallucinate or ignore subnet data.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: none
- Validation: Generate prompt references dst_ip/src_ip with both grouping directions. 5 regression tests guard against counterpart_ip reappearing. rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/ returns empty.
- Notes: Covers PR review issue #3.

### R403 — When the Excel pipeline fails, the error must report which stage actually failed, not always report `"starting"`.
- Class: failure-visibility
- Status: validated
- Description: When the Excel pipeline fails, the error must report which stage actually failed, not always report `"starting"`.
- Why it matters: The error handler reads `current_stage` from `initial_state` (always `"starting"`) instead of the evolved state. Every failure reports the wrong stage, making debugging blind.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: none
- Validation: Both runners extract stage from exc.__cause__ PipelineError details, not initial_state. 8 runner tests verify correct stage extraction and prove "starting" is never used.
- Notes: Covers PR review issue #4.

### R404 — All LLM-calling pipeline stages must pass the `stage=` parameter to `llm_client.complete()` so that token usage is tracked per-stage, not all reported as `"unknown"`.
- Class: operability
- Status: validated
- Description: All LLM-calling pipeline stages must pass the `stage=` parameter to `llm_client.complete()` so that token usage is tracked per-stage, not all reported as `"unknown"`.
- Why it matters: Without stage labels, the token usage breakdown in output is useless — every call shows as "unknown" stage.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: none
- Validation: All 8 complete() calls (4 Excel + 4 VPC stages) pass stage= kwarg. 8 test assertions verify stage= in call_args for each stage. rg 'stage=' confirms all calls tagged.
- Notes: Covers PR review issue #6. Affects all 4 Excel stages AND all 4 VPC stages (8 calls total).

### R405 — When proposals are rejected during validation or decisions reference missing proposals, the drop must be logged with context. Zero local error handling in pipeline stages must be addressed with stage-specific error wrapping.
- Class: failure-visibility
- Status: validated
- Description: When proposals are rejected during validation or decisions reference missing proposals, the drop must be logged with context. Zero local error handling in pipeline stages must be addressed with stage-specific error wrapping.
- Why it matters: Silent drops make it impossible to diagnose why expected rules don't appear in output.
- Source: execution
- Primary owning slice: M003-2heki1/S01
- Supporting slices: M003-2heki1/S02
- Validation: Both validate stages log rejected proposals with proposal_id and reason (7 tests). All 10 stage functions wrap exceptions in PipelineError with details["stage"] (11 tests). Stage-level wrapping catches before runner catch-all per D064.
- Notes: Covers PR review issues #7, #9. Validate stage silently drops rejected proposals; all pipeline stages have zero local error handling.

## Deferred

### R201 — Connect to a live firewall, fetch current rules, and compare against AI-proposed rules to identify gaps, redundancies, and conflicts.
- Class: core-capability
- Status: deferred
- Description: Connect to a live firewall, fetch current rules, and compare against AI-proposed rules to identify gaps, redundancies, and conflicts.
- Why it matters: Comparing proposals against reality produces better recommendations and avoids duplicating existing rules.
- Source: user
- Primary owning slice: future
- Supporting slices: none
- Validation: unmapped
- Notes: Originally M003 provisional. Bumped to future milestone — M003 is now PR fixes, M004 is secrets.

### R202 — Analyze an existing firewall policy set for overly permissive rules, redundancies, and security gaps without traffic data.
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

### R301 — Automatically applying proposed rules to a live firewall without human approval.
- Class: anti-feature
- Status: out-of-scope
- Description: Automatically applying proposed rules to a live firewall without human approval.
- Why it matters: Prevents accidental scope creep into dangerous auto-apply territory. Suggest-only is the product philosophy.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: May be revisited with graduated autonomy in a much later milestone.

### R302 — Processing live traffic streams rather than batch Excel/log files.
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
| R103 | core-capability | validated | M002/S02 | none | validated |
| R104 | core-capability | validated | M002/S02 | none | validated |
| R105 | core-capability | validated | M002/S02 | M002/S03 | validated |
| R106 | core-capability | validated | M002/S03 | none | validated |
| R107 | core-capability | validated | M002/S03 | M002/S04 | validated |
| R108 | core-capability | validated | M002/S05 | none | validated |
| R109 | core-capability | validated | M002/S04 | none | validated |
| R110 | core-capability | validated | M002/S04 | none | validated |
| R111 | core-capability | validated | M002/S04 | none | validated |
| R112 | core-capability | validated | M001/S02 | none | validated |
| R201 | core-capability | deferred | future | none | unmapped |
| R202 | core-capability | deferred | future | none | unmapped |
| R301 | anti-feature | out-of-scope | none | none | n/a |
| R302 | constraint | out-of-scope | none | none | n/a |
| R401 | failure-visibility | active | M003-2heki1/S02 | none | mapped |
| R402 | quality-attribute | validated | M003-2heki1/S01 | none | Generate prompt references dst_ip/src_ip with both grouping directions. 5 regression tests guard against counterpart_ip reappearing. rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/ returns empty. |
| R403 | failure-visibility | validated | M003-2heki1/S01 | none | Both runners extract stage from exc.__cause__ PipelineError details, not initial_state. 8 runner tests verify correct stage extraction and prove "starting" is never used. |
| R404 | operability | validated | M003-2heki1/S01 | none | All 8 complete() calls (4 Excel + 4 VPC stages) pass stage= kwarg. 8 test assertions verify stage= in call_args for each stage. rg 'stage=' confirms all calls tagged. |
| R405 | failure-visibility | validated | M003-2heki1/S01 | M003-2heki1/S02 | Both validate stages log rejected proposals with proposal_id and reason (7 tests). All 10 stage functions wrap exceptions in PipelineError with details["stage"] (11 tests). Stage-level wrapping catches before runner catch-all per D064. |
| R406 | quality-attribute | active | M003-2heki1/S03 | none | mapped |
| R407 | quality-attribute | active | M003-2heki1/S03 | none | mapped |
| R501 | core-capability | active | M004 (provisional) | none | unmapped |
| R502 | core-capability | active | M004 (provisional) | none | unmapped |
| R503 | core-capability | active | M004 (provisional) | none | unmapped |
| R504 | quality-attribute | active | M004 (provisional) | none | unmapped |

## Coverage Summary

- Active requirements: 7
- Mapped to slices: 7
- Validated: 16 (R101, R102, R103, R104, R105, R106, R107, R108, R109, R110, R111, R112, R402, R403, R404, R405)
- Unmapped active requirements: 0
