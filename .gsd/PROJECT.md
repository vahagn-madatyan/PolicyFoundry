# PolicyFoundry

## What This Is

PolicyFoundry is an AI-powered firewall policy management CLI tool. It ingests network traffic data — AWS VPC Flow Logs or vendor-exported Excel traffic logs — analyzes patterns through multi-stage LangGraph pipelines, and produces justified firewall rule recommendations with change request form exports. Suggest-only mode; never modifies rules directly.

## Core Value

Point the CLI at real traffic data and get back actionable, risk-scored firewall rule suggestions with business justifications — ready to export as a change request form your security team can act on.

## Current State

**M001 complete. M002 complete.** Two fully functional analysis modes:

1. **VPC Flow Log mode** (`--source local|s3`): Ingest AWS VPC Flow Logs → 5-stage LangGraph analysis → Rich terminal output and JSON export. AWS Security Group adapter, ReadOnlyAdapter safety enforcement.
2. **Excel traffic mode** (`--source excel`): Ingest Excel traffic exports → auto-detect 10 columns → direction inference + flow aggregation (~603 tuples from 83K rows) + subnet grouping → 5-stage LangGraph pipeline with NullAdapter → Rich/JSON output → xlsx/pdf change request form export with custom template support.

Infrastructure: Terraform test environment, Docker packaging. 661 tests passing.

**M003-2heki1 complete.** All 14 PR review issues from M002 fixed across 3 slices: S01 (pipeline correctness & observability), S02 (silent failure elimination), S03 (type safety & data integrity). 661 tests passing (excluding credential-dependent AWS tests), zero regressions. Codebase is solid for M004.

## Architecture / Key Patterns

- **CLI**: Typer + Rich, sync commands with internal `asyncio.run()` (D027)
- **Pipeline**: LangGraph StateGraph with PipelineContext DI — Analyze → Assess → Generate → Validate → Decide
- **Two parallel pipelines**: VPC pipeline (DuckDB queries, data_dir) and Excel pipeline (inline flow data, pre-summarizer) — shared LLMClient, adapter interface, and Rich renderers
- **LLM**: Instructor + LiteLLM for structured Pydantic output, dual retry (3x validation, 3x transient)
- **Adapters**: FirewallAdapter ABC → AdapterRegistry plugin discovery → vendor adapters (AWS SG, NullAdapter)
- **Ingestion**: Parser → Dedup → IngestionResult pattern. Local files, S3, and Excel (synonym-based column auto-detect)
- **Analysis**: Direction inference (4-signal heuristic), flow aggregation (ephemeral port exclusion), subnet grouping (/24 candidates)
- **Storage**: Parquet + zstd compression, DuckDB analytics queries (VPC mode only)
- **Output**: Rich terminal formatter (shared renderers D048), JSON export
- **Export**: xlsx change request forms (default + custom template), PDF forms (fpdf2)
- **Safety**: ReadOnlyAdapter wraps all adapter access, SafetyError on writes
- **Config**: Pydantic Settings with YAML + env var merge, 4-layer priority

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] **M001: PolicyFoundry MVP** — VPC Flow Log → LangGraph pipeline → Rich output with risk tables, JSON export, suggest-only safety, Terraform + Docker packaging
- [x] **M002: Excel Traffic Analysis & Change Request Forms** — Excel traffic log → multi-stage LangGraph pipeline → FW rule suggestions → Excel/PDF change request form export
- [x] **M003-2heki1: PR Review Bug Fixes** — Fixed 14 critical + important issues: pipeline correctness, silent failure elimination, type safety. 661 tests, zero regressions.
- [ ] **M004: Secrets Management** — .env file support, OS credential store (macOS Keychain / Windows Credential Manager), `policyfoundry secret` CLI commands
