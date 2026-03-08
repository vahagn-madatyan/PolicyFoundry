# Requirements: PolicyFoundry

**Defined:** 2026-03-07
**Core Value:** Point the CLI at real AWS VPC flow logs and get back actionable, justified Security Group rule suggestions — with full audit lineage and zero manual analysis.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingestion

- [ ] **INGEST-01**: User can parse AWS VPC Flow Logs from local files
- [ ] **INGEST-02**: User can parse AWS VPC Flow Logs from S3 buckets via boto3
- [ ] **INGEST-03**: Parsed logs are normalized to unified 10-field schema (timestamp, src_ip, dst_ip, src_port, dst_port, protocol, action, bytes_transferred, rule_id, app_name)
- [ ] **INGEST-04**: Malformed log lines are skipped with warnings; duplicate records are deduplicated by ingestion ID
- [ ] **INGEST-05**: Normalized logs are stored as Parquet files and queryable via DuckDB for analytics

### Adapter

- [ ] **ADAPT-01**: User can fetch current AWS Security Group rules and view them in universal format
- [ ] **ADAPT-02**: Rules are represented in a vendor-neutral universal schema extensible to other firewall vendors
- [ ] **ADAPT-03**: Proposed rule changes are validated against AWS SG constraints (allow-only, 60-rule limit, reject overly permissive 0.0.0.0/0)

### Pipeline

- [ ] **PIPE-01**: User can run a 4-stage LangGraph AI pipeline: Analyze → Assess → Generate Policy → Decide
- [ ] **PIPE-02**: Stage 1 (Analyze) interprets pre-aggregated traffic statistics to identify patterns, anomalies, and top talkers
- [ ] **PIPE-03**: Stage 2 (Assess) compares traffic patterns against current SG rules to identify gaps and risk
- [ ] **PIPE-04**: Stage 3 (Generate) produces vendor-neutral rule proposals with business justification and impact analysis
- [ ] **PIPE-05**: Stage 4 (Decide) assigns risk levels and determines CREATE/UPDATE/SKIP for each proposal
- [ ] **PIPE-06**: LLM calls route through LiteLLM with Ollama as default local provider

### Output

- [ ] **OUT-01**: User can view analysis results in Rich terminal with color-coded risk tables and summary panels
- [ ] **OUT-02**: User can export analysis results as machine-readable JSON

### Safety

- [ ] **SAFE-01**: Tool operates in suggest-only mode — no firewall changes are applied
- [ ] **SAFE-02**: Each pipeline run tracks LLM token usage and estimated cost

### Configuration

- [ ] **CONF-01**: User can configure the tool via YAML file (~/.policyfoundry/config.yaml) with environment variable overrides
- [ ] **CONF-02**: User can set LLM provider, model, log sources, and target security groups in config

### Infrastructure

- [ ] **INFRA-01**: Terraform configuration bootstraps AWS test environment (VPC, Security Groups, EC2 instances generating traffic, VPC Flow Logs enabled)
- [ ] **INFRA-02**: Dockerfile and docker-compose.yml for containerized usage

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Pipeline Enhancements

- **PIPE-07**: Pipeline checkpointing via SQLiteSaver for resumability after failures
- **PIPE-08**: SARIF output format for CI/CD integration (GitHub Code Scanning, Azure DevOps)
- **PIPE-09**: Structured Pydantic output validation for every LLM call
- **PIPE-10**: Pipeline replay from specific checkpoint stage

### Safety & Audit

- **SAFE-03**: Immutable event-sourced audit log with full AI lineage (model, tokens, reasoning)
- **SAFE-04**: Human-in-the-loop approval gate via LangGraph interrupt for per-suggestion review

### Additional Adapters

- **ADAPT-04**: Palo Alto Cloud NGFW adapter (two-phase commit, App-ID support)
- **ADAPT-05**: Azure NSG adapter
- **ADAPT-06**: Fortinet FortiOS adapter

### Advanced Features

- **ADV-01**: Threat intelligence integration (AbuseIPDB, GreyNoise free tier)
- **ADV-02**: Standalone overly permissive rule detection command
- **ADV-03**: Standalone unused rule detection command
- **ADV-04**: Cloud LLM support (AWS Bedrock Claude, OpenAI GPT-4o)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Auto-apply mode | Trust must be earned through suggestion accuracy; Phase 1 is suggest-only |
| Web GUI / dashboard | CLI is the product; doubles codebase and halves iteration speed |
| Real-time streaming ingestion | Batch is sufficient for policy management cadence; VPC Flow Logs have 10-min delay anyway |
| Multi-cloud in Phase 1 | Each cloud has different primitives; prove pipeline on AWS first |
| Deep Agents library | Using LangGraph native sub-graphs; reduces niche dependency |
| Compliance report generation | Deep domain expertise needed; integrate with compliance platforms instead |
| Natural language query interface | Different interaction model; dilutes focus on structured pipeline |
| Custom rule DSL | Overkill; use configurable YAML for custom parameters |
| Team collaboration / RBAC / SSO | Enterprise features for when there are enterprise customers |
| Mobile app | CLI tool; not applicable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | TBD | Pending |
| INGEST-02 | TBD | Pending |
| INGEST-03 | TBD | Pending |
| INGEST-04 | TBD | Pending |
| INGEST-05 | TBD | Pending |
| ADAPT-01 | TBD | Pending |
| ADAPT-02 | TBD | Pending |
| ADAPT-03 | TBD | Pending |
| PIPE-01 | TBD | Pending |
| PIPE-02 | TBD | Pending |
| PIPE-03 | TBD | Pending |
| PIPE-04 | TBD | Pending |
| PIPE-05 | TBD | Pending |
| PIPE-06 | TBD | Pending |
| OUT-01 | TBD | Pending |
| OUT-02 | TBD | Pending |
| SAFE-01 | TBD | Pending |
| SAFE-02 | TBD | Pending |
| CONF-01 | TBD | Pending |
| CONF-02 | TBD | Pending |
| INFRA-01 | TBD | Pending |
| INFRA-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 0
- Unmapped: 22

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after initial definition*
