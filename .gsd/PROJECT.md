# PolicyFoundry

## What This Is

PolicyFoundry is an AI-powered firewall policy management CLI tool that ingests network traffic flow logs, analyzes patterns through a multi-stage LLM pipeline, queries existing firewall rules, and autonomously suggests rule changes. It bridges traffic analysis (NDR) and policy management (NSPM) — two domains that remain separate in every existing product. Python CLI first, starting with AWS (VPC Flow Logs + Security Groups), with Palo Alto Cloud NGFW support following once the pipeline is proven.

## Core Value

Point the CLI at real AWS VPC flow logs and get back actionable, justified Security Group rule suggestions — with full audit lineage and zero manual analysis.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- [x] Ingest AWS VPC Flow Logs from S3 or local files and normalize to unified 10-field schema
- [x] Store normalized logs as Parquet files queryable by DuckDB
- [x] Run 5-stage agentic AI pipeline via LangGraph: Analyze → Assess → Generate → Validate → Decide
- [x] Query existing AWS Security Group rules via boto3 adapter
- [x] Produce vendor-neutral rule change recommendations (suggest-only mode)
- [x] Output results as JSON or rich terminal UI with color-coded risk tables
- [x] LLM routing via LiteLLM with Ollama as primary local provider
- [x] All LLM outputs use structured Pydantic models (no free-text parsing)
- [x] Token usage and estimated cost tracked per pipeline run
- [x] ReadOnlyAdapter safety enforcement — no firewall modifications possible
- [x] Terraform in-repo for bootstrapping AWS test infrastructure (VPC, SGs, Flow Logs)
- [x] Dockerfile and docker-compose.yml for containerized usage with Ollama sidecar

### Active

<!-- Current scope. Building toward these. -->

- [ ] LangGraph checkpointing for pipeline resumability (SQLiteSaver)
- [ ] Event-sourced immutable audit log for every rule change proposal
- [ ] Human-in-the-loop approval gate via LangGraph interrupt
- [ ] SARIF output format for CI/CD integration
- [ ] Palo Alto Cloud NGFW adapter

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Palo Alto Cloud NGFW adapter — deferred until AWS pipeline is proven end-to-end
- Web GUI (TypeScript/Next.js) — Phase 2, CLI is the product for now
- Real-time streaming ingestion — start with batch/micro-batch
- Auto-apply mode — Phase 1 is suggest-only; graduated autonomy comes later
- Deep Agents library — using LangGraph native sub-graphs and tool-calling instead
- Additional adapters (Fortinet, Check Point, Azure NSG) — Phase 2+
- Team collaboration, RBAC, SSO — enterprise features for later
- Mobile app — web-first, mobile never (CLI tool)

## Context

- **Domain**: Network security — firewall rule management is manual, error-prone, and disconnected from traffic analysis. Security teams analyze traffic in one tool and manage rules in another. PolicyFoundry closes that gap with AI.
- **Target user**: Security engineers and network admins managing AWS Security Groups who want AI-assisted policy recommendations based on actual traffic patterns.
- **LLM strategy**: Start with Ollama local (zero cloud costs during development), route through LiteLLM for provider flexibility. AWS Bedrock (Claude) and OpenAI available as future providers.
- **AWS infrastructure**: User has AWS account; will bootstrap test environment (VPC, SGs, dummy EC2s generating traffic, VPC Flow Logs) via Terraform/CDK included in the repo.
- **Existing work**: Extensive architecture plan, implementation spec, and agentic kickoff prompt already written. Dashboard visualization component exists (React/JSX).
- **Business model**: Open-core (BSL 1.1 → Apache 2.0 after 3 years). Free CLI for single-firewall analysis; premium cloud for multi-FW, web dashboard, auto-apply, compliance reports.

## Constraints

- **Language**: Python 3.12+ — rich LLM ecosystem, LangChain/LangGraph native
- **CLI Framework**: Typer + Rich — Click-based, auto-help, beautiful terminal output
- **LLM Framework**: LangGraph for orchestration, LangChain for tools/memory, LiteLLM for routing — no Deep Agents
- **Data Validation**: Pydantic v2 exclusively — no dataclasses for domain models
- **Storage (CLI tier)**: DuckDB (analytics) + Parquet (logs) + SQLite (state/audit) — zero external dependencies
- **AWS SDK**: boto3 for Security Groups, VPC Flow Logs, and future Bedrock access
- **Async**: All I/O operations must be async/await; asyncio.run() at CLI entrypoint only
- **Testing**: pytest + pytest-asyncio; moto for AWS mocking; tests alongside implementation
- **License**: BSL 1.1 with 3-year conversion to Apache 2.0
- **Security**: Never hardcode credentials; env vars or config YAML; API keys by env var name reference

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PolicyFoundry as project name | Repo name, broader than just firewalls | — Pending |
| AWS-first (drop Palo Alto from MVP) | Prove the pipeline end-to-end with one vendor before adding complexity | — Pending |
| Ollama as starting LLM provider | Zero cloud costs during development, iterate fast locally | — Pending |
| Drop Deep Agents, use LangGraph only | Reduce dependency on niche library, LangGraph has native sub-graph support | — Pending |
| Terraform in-repo for test infra | Reproducible AWS test environment, onboarding friendly | — Pending |
| Suggest-only mode for Phase 1 | Build trust before any auto-apply; safety-first approach | — Pending |
| Pydantic v2 for all domain models | Type-safe, structured LLM output parsing, config validation | — Pending |

---
*Last updated: 2026-03-12 after M001 milestone completion*
