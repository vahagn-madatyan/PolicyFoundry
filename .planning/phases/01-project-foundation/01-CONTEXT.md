# Phase 1: Project Foundation - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Scaffolding, domain models, exception hierarchy, and project structure. Developers get a working Python project with all domain models, shared types, and error handling in place so every subsequent phase builds on a stable base. No business logic — just the skeleton and type definitions.

</domain>

<decisions>
## Implementation Decisions

### Package Layout
- src/ layout: `src/policyfoundry/` — prevents accidental dev-copy imports, standard for publishable packages
- Pipeline module named `pipeline/` (not `agents/`) with sub-modules `stages/` and `prompts/` — matches domain language (Analyze, Assess, Generate, Decide)
- Module structure: config/, ingestion/, storage/, pipeline/, adapters/, output/, utils/
- Separate `tests/` tree mirroring src/ structure: tests/test_config/, tests/test_ingestion/, etc.
- No audit/ module — deferred to v2; add when audit requirements are active
- Old spec references to `firewall_ai` and Palo Alto modules are superseded — name is `policyfoundry`, AWS-only for v1

### Domain Model Scope
- NormalizedFlowLog: 12-field schema (expanded from requirements' 10) — timestamp, src_ip, dst_ip, src_port, dst_port, protocol, action, bytes_transferred, rule_id, app_name, flow_direction (INBOUND/OUTBOUND), packets_count
- LLM output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision): full schemas defined in Phase 1 based on architecture plan — shape is locked, fields can evolve
- UniversalRule: vendor-neutral from day 1 — direction, action (ALLOW/DENY), protocol, ports, CIDRs, description, priority. AWS adapter won't use DENY or priority but the model is ready for Palo Alto later
- PipelineState: TypedDict (not Pydantic) with run metadata — run_id, started_at, current_stage, plus data references (flow_log_path, sg_ids, analysis, assessment, proposals, decisions). Stores flow log references as strings, not raw data

### Dev Tooling
- Package manager: uv (already in success criteria)
- Linting: Ruff strict config (most rules enabled), formatting via ruff format — all config in pyproject.toml
- Type checking: Pyright in strict mode via pyproject.toml
- Pre-commit: .pre-commit-config.yaml with ruff (lint + format) and pyright hooks
- Dev commands: Makefile wrapping uv run — make test, make lint, make format, make check

### Error Philosophy
- Per-domain exception hierarchy: PolicyFoundryError base, then ConfigError, IngestionError, StorageError, AdapterError, PipelineError, OutputError
- ConfigError gets immediate subclasses: ConfigFileNotFound, ConfigValidationError; other domains add subclasses in their phases
- Structured context: each exception carries optional error_code (string like 'INGEST_001') and details dict for machine-readable context
- All exceptions importable from single module: policyfoundry.exceptions
- User-facing: clean actionable messages by default; stack traces only with --debug flag or POLICYFOUNDRY_DEBUG=1 env var

### Claude's Discretion
- Exact field types and validators for LLM output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision)
- pyproject.toml dependency versions and optional dependency groups
- conftest.py shared fixtures design
- Makefile target names and help formatting

</decisions>

<specifics>
## Specific Ideas

- Old architecture plan (01-architecture-plan.md) and implementation spec (02-implementation-spec.md) exist in repo root — reference for schema field ideas but naming/structure is superseded by PROJECT.md decisions
- Package should be installable as CLI entry point: `policyfoundry` command via `[project.scripts]`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing Python code

### Established Patterns
- None yet — Phase 1 establishes all patterns

### Integration Points
- pyproject.toml is the central config hub (ruff, pyright, uv, project metadata)
- src/policyfoundry/__init__.py exports version and package metadata
- policyfoundry.exceptions is the single import point for all error types

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-project-foundation*
*Context gathered: 2026-03-07*
