# Roadmap: PolicyFoundry

## Overview

PolicyFoundry goes from zero to a working CLI that ingests AWS VPC Flow Logs, runs them through a 4-stage LLM pipeline, and outputs justified Security Group rule recommendations. The build order follows the data flow: foundation and config first, then data ingestion and storage, then the firewall adapter and LLM integration, then the pipeline stages themselves, then output formatting, safety controls, and finally CLI integration with test infrastructure. Each phase delivers a coherent, testable capability that unblocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Project Foundation** - Scaffolding, domain models, exception hierarchy, and project structure
- [ ] **Phase 2: Configuration System** - YAML config with env var overrides and LLM provider settings
- [ ] **Phase 3: Log Ingestion** - Parse AWS VPC Flow Logs from local files and S3 with normalization
- [ ] **Phase 4: Storage Layer** - Parquet persistence and DuckDB analytics queries
- [ ] **Phase 5: Firewall Adapter** - AWS Security Group rule fetching, universal schema, and constraint validation
- [ ] **Phase 6: LLM Integration** - LiteLLM client factory with Ollama routing and structured output
- [ ] **Phase 7: Pipeline Core** - 4-stage LangGraph StateGraph wiring Analyze through Decide
- [ ] **Phase 8: Output and Safety** - Rich terminal display, JSON export, suggest-only enforcement, and cost tracking
- [ ] **Phase 9: CLI Integration** - Typer command surface connecting all components end-to-end
- [ ] **Phase 10: Infrastructure and Packaging** - Terraform test environment, Docker packaging, and end-to-end validation

## Phase Details

### Phase 1: Project Foundation
**Goal**: Developers have a working Python project with all domain models, shared types, and error handling in place so every subsequent phase builds on a stable base
**Depends on**: Nothing (first phase)
**Requirements**: None directly (foundational scaffolding enabling all requirements)
**Success Criteria** (what must be TRUE):
  1. Running `uv run python -c "import policyfoundry"` succeeds with no errors
  2. All domain model schemas (NormalizedFlowLog, UniversalRule, PipelineState, TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision) can be instantiated with valid data and reject invalid data
  3. PipelineState TypedDict stores flow log references as strings (not raw log data), preventing future checkpoint bloat
  4. Custom exception hierarchy exists and all exceptions are importable from a single module
**Plans**: TBD

Plans:
- [ ] 01-01: Project scaffolding and domain models
- [ ] 01-02: PipelineState TypedDict and exception hierarchy

### Phase 2: Configuration System
**Goal**: Users can configure PolicyFoundry via YAML file and environment variables, setting LLM provider, model, log sources, and target security groups
**Depends on**: Phase 1
**Requirements**: CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. User can create ~/.policyfoundry/config.yaml and the tool reads it on startup
  2. User can override any config value via environment variable (e.g., POLICYFOUNDRY_LLM_PROVIDER=ollama)
  3. User can set LLM provider, model name, log source paths, and target security group IDs in config
  4. Invalid config values produce clear error messages naming the bad field and expected format
**Plans**: TBD

Plans:
- [ ] 02-01: Pydantic Settings configuration with YAML and env var support

### Phase 3: Log Ingestion
**Goal**: Users can point the tool at VPC Flow Log files (local or S3) and get normalized, deduplicated flow records
**Depends on**: Phase 1
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04
**Success Criteria** (what must be TRUE):
  1. User can parse a local VPC Flow Log file and see normalized records with all 10 schema fields populated
  2. User can parse VPC Flow Logs from an S3 bucket (given valid AWS credentials) and see the same normalized output
  3. Malformed log lines are skipped with a warning message (not a crash), and the warning identifies the line
  4. Duplicate records (same ingestion ID) are deduplicated so each flow appears exactly once
**Plans**: TBD

Plans:
- [ ] 03-01: VPC Flow Log parser for local files with normalization
- [ ] 03-02: S3 ingestion via boto3 and deduplication logic

### Phase 4: Storage Layer
**Goal**: Normalized logs are persisted as Parquet files and queryable via DuckDB for traffic analytics
**Depends on**: Phase 3
**Requirements**: INGEST-05
**Success Criteria** (what must be TRUE):
  1. Normalized logs are written to Parquet files with zstd compression
  2. User can query stored logs via DuckDB and get results (e.g., top talkers by bytes, denied flows by source)
  3. Queries against multi-MB Parquet files return in under 5 seconds on a standard laptop
**Plans**: TBD

Plans:
- [ ] 04-01: Parquet writer and DuckDB analytics store

### Phase 5: Firewall Adapter
**Goal**: Users can fetch current AWS Security Group rules in a universal format, and proposed rule changes are validated against AWS constraints
**Depends on**: Phase 1
**Requirements**: ADAPT-01, ADAPT-02, ADAPT-03
**Success Criteria** (what must be TRUE):
  1. User can run a command to fetch SG rules from AWS and see them displayed in vendor-neutral universal format
  2. Universal rule schema contains fields sufficient to represent rules from any firewall vendor (direction, protocol, ports, CIDRs, action)
  3. Proposed rules that violate AWS SG constraints are rejected: overly permissive 0.0.0.0/0 without explicit flag, exceeding 60-rule limit, DENY actions (SGs are allow-only)
  4. The adapter declares its capabilities (allow-only, rule limit) so downstream components can adapt behavior
**Plans**: TBD

Plans:
- [ ] 05-01: FirewallAdapter ABC, AdapterRegistry, and universal rule schema
- [ ] 05-02: AWS Security Group adapter with boto3 and rule validation

### Phase 6: LLM Integration
**Goal**: LLM calls route through LiteLLM with Ollama as the default provider, returning structured Pydantic objects
**Depends on**: Phase 1, Phase 2
**Requirements**: PIPE-06
**Success Criteria** (what must be TRUE):
  1. LLM calls go through LiteLLM and reach Ollama when configured as the provider
  2. LLM responses are parsed into Pydantic models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision) without free-text parsing
  3. When structured output parsing fails, the system retries with the validation error fed back to the LLM
  4. Switching LLM provider in config (e.g., from Ollama to a cloud provider) works without code changes
**Plans**: TBD

Plans:
- [ ] 06-01: LiteLLM client factory with Ollama routing
- [ ] 06-02: Structured output parsing with retry-on-failure

### Phase 7: Pipeline Core
**Goal**: Users can run the full 4-stage AI pipeline (Analyze, Assess, Generate Policy, Decide) on ingested flow logs and get rule recommendations
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05
**Success Criteria** (what must be TRUE):
  1. User can trigger a pipeline run that executes all 4 stages in order: Analyze, Assess, Generate, Decide
  2. Stage 1 (Analyze) produces traffic pattern analysis including top talkers, anomalies, and protocol distribution from DuckDB pre-aggregated stats
  3. Stage 2 (Assess) compares traffic patterns to current SG rules and identifies gaps (allowed traffic with no rule, denied traffic that should be allowed)
  4. Stage 3 (Generate) produces vendor-neutral rule proposals with business justification and impact analysis, respecting adapter capabilities
  5. Stage 4 (Decide) assigns risk levels (LOW/MEDIUM/HIGH/CRITICAL) and actions (CREATE/UPDATE/SKIP) to each proposal
**Plans**: TBD

Plans:
- [ ] 07-01: LangGraph StateGraph definition and Analyze stage
- [ ] 07-02: Assess and Generate stages with adapter capability injection
- [ ] 07-03: Decide stage and full pipeline wiring

### Phase 8: Output and Safety
**Goal**: Users can view pipeline results in a rich terminal display or export as JSON, with suggest-only enforcement and cost tracking
**Depends on**: Phase 7
**Requirements**: OUT-01, OUT-02, SAFE-01, SAFE-02
**Success Criteria** (what must be TRUE):
  1. User can view analysis results in the terminal with color-coded risk tables (red for CRITICAL, yellow for HIGH, green for LOW) and summary panels
  2. User can export analysis results as machine-readable JSON that contains all proposals, risk levels, and justifications
  3. The tool never applies firewall changes -- suggest-only mode is enforced at the adapter level, not just the UI
  4. After a pipeline run, user can see total LLM token usage (input and output tokens) and estimated cost
**Plans**: TBD

Plans:
- [ ] 08-01: Rich terminal output with risk tables and summary panels
- [ ] 08-02: JSON export, suggest-only enforcement, and token cost tracking

### Phase 9: CLI Integration
**Goal**: All capabilities are wired into a polished Typer CLI with intuitive commands, help text, and error handling
**Depends on**: Phase 2, Phase 3, Phase 4, Phase 5, Phase 7, Phase 8
**Requirements**: None directly (integration layer connecting requirement-bearing phases)
**Success Criteria** (what must be TRUE):
  1. User can run `policyfoundry analyze --source <path>` and see the full pipeline execute with progress feedback
  2. User can run `policyfoundry rules --sg <sg-id>` to view current Security Group rules
  3. Running `policyfoundry --help` shows all available commands with descriptions, and no command requires AWS credentials just to display help
  4. Errors produce actionable messages (e.g., "AWS credentials not found -- set AWS_PROFILE or configure credentials") instead of stack traces
**Plans**: TBD

Plans:
- [ ] 09-01: Typer command surface and CLI entrypoint
- [ ] 09-02: Progress feedback, error handling, and help text polish

### Phase 10: Infrastructure and Packaging
**Goal**: Users can bootstrap an AWS test environment via Terraform and run PolicyFoundry in Docker, with end-to-end tests proving the full pipeline works
**Depends on**: Phase 9
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. Running `terraform apply` in the infra directory creates a VPC, Security Groups, EC2 instances generating traffic, and VPC Flow Logs enabled
  2. User can build and run PolicyFoundry via `docker-compose up` with no local Python environment required
  3. End-to-end test runs the full pipeline (ingest sample logs, run pipeline, produce output) and passes without manual intervention
**Plans**: TBD

Plans:
- [ ] 10-01: Terraform test infrastructure
- [ ] 10-02: Dockerfile, docker-compose, and end-to-end tests

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

Note: Phases 3 and 5 both depend only on Phase 1, and Phase 6 depends on Phases 1 and 2. These can overlap but are listed sequentially for simplicity.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation | 0/2 | Not started | - |
| 2. Configuration System | 0/1 | Not started | - |
| 3. Log Ingestion | 0/2 | Not started | - |
| 4. Storage Layer | 0/1 | Not started | - |
| 5. Firewall Adapter | 0/2 | Not started | - |
| 6. LLM Integration | 0/2 | Not started | - |
| 7. Pipeline Core | 0/3 | Not started | - |
| 8. Output and Safety | 0/2 | Not started | - |
| 9. CLI Integration | 0/2 | Not started | - |
| 10. Infrastructure and Packaging | 0/2 | Not started | - |
