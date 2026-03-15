# PolicyFoundry

## What This Is

PolicyFoundry is an AI-powered firewall policy management CLI tool. It ingests network traffic data — AWS VPC Flow Logs or vendor-exported Excel traffic logs — analyzes patterns through multi-stage LangGraph pipelines, and produces justified firewall rule recommendations. Suggest-only mode; never modifies rules directly.

## Core Value

Point the CLI at real traffic data and get back actionable, risk-scored firewall rule suggestions with business justifications — ready to export as a change request form your security team can act on.

## Current State

**M001 complete. M002/S03 complete (3 of 5 slices).** Full pipeline from VPC Flow Log ingestion through 5-stage LangGraph analysis to Rich terminal output and JSON export. AWS Security Group adapter, ReadOnlyAdapter safety enforcement, Terraform test infra, Docker packaging. Excel traffic ingestion with auto-detect column mapping parses 83,633 rows. Traffic pre-processing aggregates 83K flows into ~600 tuples with direction labels and subnet grouping. Analysis pipeline (5-stage LangGraph with NullAdapter) produces risk-scored rule proposals with AI-generated justifications — Rich and JSON output formatters ready. 564 tests passing.

## Architecture / Key Patterns

- **CLI**: Typer + Rich, sync commands with internal `asyncio.run()` (D027)
- **Pipeline**: LangGraph StateGraph with PipelineContext DI — Analyze → Assess → Generate → Validate → Decide
- **Excel Pipeline**: Separate LangGraph graph (D039) with pre-summarizer (D049), NullAdapter default (D040), inline flow data (D050)
- **LLM**: Instructor + LiteLLM for structured Pydantic output, dual retry (3x validation, 3x transient)
- **Adapters**: FirewallAdapter ABC → AdapterRegistry plugin discovery → vendor adapters (AWS SG, NullAdapter)
- **Ingestion**: Parser → Dedup → IngestionResult pattern. Local files, S3, and Excel
- **Storage**: Parquet + zstd compression, DuckDB analytics queries
- **Output**: Rich terminal formatter (shared renderers D048), JSON export, (M002) Excel/PDF change request forms
- **Safety**: ReadOnlyAdapter wraps all adapter access, SafetyError on writes
- **Config**: Pydantic Settings with YAML + env var merge, 4-layer priority

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] **M001: PolicyFoundry MVP** — VPC Flow Log → LangGraph pipeline → Rich output with risk tables, JSON export, suggest-only safety, Terraform + Docker packaging
- [ ] **M002: Excel Traffic Analysis & Change Request Forms** — Excel traffic log → multi-stage LangGraph pipeline → FW rule suggestions → Excel/PDF change request form export
- [ ] **M003: Live Firewall Integration** — Query existing FW rules, compare against proposed rules, gap analysis on live policies (provisional)

---
*Last updated: 2026-03-15 after M002/S03 completion*
