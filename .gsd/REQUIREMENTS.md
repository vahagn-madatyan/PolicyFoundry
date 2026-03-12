# Requirements

## Active

### OUT-01 — User can view analysis results in Rich terminal with color-coded risk tables and summary panels

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

User can view analysis results in Rich terminal with color-coded risk tables and summary panels

### OUT-02 — User can export analysis results as machine-readable JSON

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

User can export analysis results as machine-readable JSON

### SAFE-01 — Tool operates in suggest-only mode — no firewall changes are applied

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

Tool operates in suggest-only mode — no firewall changes are applied

### SAFE-02 — Each pipeline run tracks LLM token usage and estimated cost

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

Each pipeline run tracks LLM token usage and estimated cost

### INFRA-01 — Terraform configuration bootstraps AWS test environment (VPC, Security Groups, EC2 instances generating traffic, VPC Flow Logs enabled)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

Terraform configuration bootstraps AWS test environment (VPC, Security Groups, EC2 instances generating traffic, VPC Flow Logs enabled)

### INFRA-02 — Dockerfile and docker-compose.yml for containerized usage

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

Dockerfile and docker-compose.yml for containerized usage

## Validated

### INGEST-01 — User can parse AWS VPC Flow Logs from local files

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S03

### INGEST-02 — User can parse AWS VPC Flow Logs from S3 buckets via boto3

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S03

### INGEST-03 — Parsed logs are normalized to unified 10-field schema

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S03

### INGEST-04 — Malformed log lines are skipped with warnings; duplicate records are deduplicated

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S03

### INGEST-05 — Normalized logs are stored as Parquet files and queryable via DuckDB

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S04

### ADAPT-01 — User can fetch current AWS Security Group rules and view them in universal format

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S05

### ADAPT-02 — Rules are represented in a vendor-neutral universal schema

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S05

### ADAPT-03 — Proposed rule changes are validated against AWS SG constraints

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S05

### PIPE-01 — User can run a 4-stage LangGraph AI pipeline: Analyze → Assess → Generate Policy → Decide

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S07

### PIPE-02 — Stage 1 (Analyze) interprets pre-aggregated traffic statistics

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S07

### PIPE-03 — Stage 2 (Assess) compares traffic patterns against current SG rules

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S07

### PIPE-04 — Stage 3 (Generate) produces vendor-neutral rule proposals with justification

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S07

### PIPE-05 — Stage 4 (Decide) assigns risk levels and determines CREATE/UPDATE/SKIP

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S07

### PIPE-06 — LLM calls route through LiteLLM with Ollama as default local provider

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S06

### CONF-01 — User can configure the tool via YAML file with environment variable overrides

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S02

### CONF-02 — User can set LLM provider, model, log sources, and target security groups in config

- Status: validated
- Class: core-capability
- Source: inferred
- Validated by: S02

## Deferred

(none)

## Out of Scope

(none)
