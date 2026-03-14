# Project Research Summary

**Project:** PolicyFoundry
**Domain:** AI-powered firewall policy management (CLI-first, agentic pipeline)
**Researched:** 2026-03-07
**Confidence:** HIGH

## Executive Summary

PolicyFoundry is an AI-powered CLI tool that analyzes VPC Flow Logs, interprets traffic patterns via an LLM pipeline, and generates justified Security Group rule recommendations. This is a well-understood problem domain (Network Security Policy Management) currently dominated by enterprise vendors (Tufin, AlgoSec, FireMon) at $50K-200K+/year. The open-source gap is clear: tools like Prowler and ScoutSuite audit configurations but do not analyze actual traffic patterns or generate rule recommendations. Google Cloud Firewall Insights is the closest analog (ML-powered traffic analysis) but is GCP-only and not self-hostable. Skybox Security's shutdown in February 2025 created additional market opportunity. PolicyFoundry fills this gap with a local-first, LLM-powered approach that keeps sensitive network data on-premise via Ollama.

The recommended approach is a Python 3.12+ CLI using Typer/Rich for the interface, a 4-stage LangGraph StateGraph pipeline (Analyze, Assess, Generate, Decide) with SQLite checkpointing, DuckDB over Parquet for flow log analytics, and LiteLLM for multi-provider LLM routing. The architecture follows a ports-and-adapters pattern with a universal rule schema, making it AWS-only in Phase 1 but multi-vendor ready from day one. The stack is mature -- LangGraph reached 1.0 GA, LangChain is at 1.2, and every dependency has HIGH confidence with verified PyPI versions. Notably, the original project spec contains outdated versions across the board (LangGraph 0.2, LangChain 0.3, deprecated packages like `langchain-community` ChatLiteLLM and CDKTF) -- all version pins must be updated before implementation begins.

The dominant risks are LLM-related: hallucinated overly permissive rules (mitigated by deterministic post-LLM validation), structured output parsing failures with Ollama local models (mitigated by retry-with-repair and schema testing), and checkpoint state bloat from storing raw logs (mitigated by storing only Parquet file references in pipeline state). These risks are all addressable in Phase 1 and have clear prevention strategies. The biggest open question is Ollama structured output reliability via LiteLLM -- this needs empirical validation early in implementation, with a fallback to using `langchain-ollama` ChatOllama directly for local development.

## Key Findings

### Recommended Stack

The stack centers on the LangChain/LangGraph ecosystem for AI orchestration, with DuckDB for analytics and a CLI-first interface via Typer + Rich. All dependencies are verified at current stable versions as of March 2026. Notable changes from the original project spec: LangGraph and LangChain both reached 1.0 GA (major stability milestone), `langchain-community` ChatLiteLLM is deprecated in favor of the dedicated `langchain-litellm` package, CDKTF was deprecated by HashiCorp in December 2025, and AWS CDK is incompatible (Python <=3.11 only). Use plain Terraform HCL for test infrastructure.

**Core technologies:**
- **Python 3.12+ / uv**: Runtime and package manager -- mature type hints, 10-100x faster dependency resolution than pip/poetry
- **LangGraph 1.0.10**: 4-stage StateGraph pipeline with SQLite checkpointing and human-in-the-loop via `interrupt()`
- **LangChain 1.2 + langchain-litellm 0.6.1**: Foundation for structured LLM output via `.with_structured_output()` and LiteLLM bridge
- **LiteLLM 1.82**: Multi-provider LLM routing with cost tracking; `ollama/modelname` for local, `bedrock/` for cloud
- **DuckDB 1.4.4 + PyArrow 23.0**: Embedded columnar analytics over Parquet files -- fast aggregation on multi-GB flow logs; no native async (use `asyncio.to_thread()`)
- **Pydantic 2.12 + pydantic-settings 2.13**: Domain models, LLM structured output schemas, and YAML + env var configuration
- **Typer 0.24.1 + Rich 14.3**: CLI framework with tables, panels, progress indicators (Rich is now bundled with Typer)
- **boto3 1.42+**: AWS Security Group CRUD and S3 flow log access; no native async (use `run_in_executor`)
- **Terraform HCL 1.9+**: Test infrastructure -- NOT CDKTF (deprecated Dec 2025), NOT AWS CDK (Python <=3.11 only)

**Critical version corrections from original spec:**
- LangGraph: 0.2 -> 1.0.10 (GA release)
- LangChain: 0.3 -> 1.2 (GA release)
- `langchain-community` ChatLiteLLM: REMOVED -- use `langchain-litellm` package
- Deep Agents: REMOVED -- dropped per PROJECT.md; LangGraph sub-graphs cover same patterns
- New required packages: `langgraph-checkpoint-sqlite`, `langchain-litellm`, `langchain-ollama`, `aiosqlite`

### Expected Features

**Must have (table stakes):**
- VPC Flow Log ingestion from S3 and local files with normalization to 10-field unified schema
- DuckDB storage with Parquet persistence for multi-GB analytical queries
- AWS Security Group rule fetching and display via boto3
- 4-stage LangGraph AI pipeline (Analyze, Assess, Generate, Decide) with structured Pydantic output from every LLM call
- Pipeline checkpointing via SQLiteSaver for resume-from-failure
- Rich terminal output with risk-colored tables + JSON machine-readable output
- YAML configuration system with env var overrides (pydantic-settings)
- Immutable event-sourced audit log in SQLite with full AI lineage
- Suggest-only mode as default and only mode in Phase 1 (no apply capability)

**Should have (differentiators):**
- Traffic-to-rule AI pipeline -- no open-source competitor does this; enterprise tools charge $50K+/year
- Local-first LLM via Ollama -- zero cloud cost, data never leaves the network
- Risk-scored recommendations with calibrated AI confidence levels (0.0-1.0)
- SARIF output for CI/CD integration (GitHub Code Scanning, Azure DevOps)
- Vendor-neutral universal rule schema designed for multi-vendor from day one
- Cost tracking per pipeline run (tokens in/out, estimated cost)
- Human-in-the-loop approval gate via LangGraph `interrupt()`
- Pipeline resumability from any checkpoint (`policyfoundry replay --run-id X --from-stage assess`)

**Defer (v2+):**
- Auto-apply mode -- trust must be earned through suggestion accuracy; requires circuit breaker, kill switch, emergency revert
- Web dashboard -- doubles codebase; CLI must be proven first
- Multi-cloud adapters (Azure NSG, GCP Firewall Rules, Palo Alto) -- each adapter is significant work; prove on AWS first
- Real-time streaming analysis -- VPC Flow Logs have inherent 10-min delay; batch is correct for policy management cadence
- Natural language query interface -- different interaction model that dilutes focus
- Compliance report generation -- deep domain expertise needed; integrate with Vanta/Drata instead

### Architecture Approach

The architecture is a layered CLI application with clear component boundaries: CLI Layer (Typer commands) -> Ingestion Layer (vendor-specific log parsers) -> Storage Layer (Parquet + DuckDB + SQLite) -> Pipeline Layer (LangGraph StateGraph) -> Adapter Layer (firewall vendor plugins) -> Output Layer (JSON/SARIF/Rich). The key design decision: TypedDict for LangGraph state (required for Annotated reducer compatibility), Pydantic BaseModel for LLM output schemas (required for `.with_structured_output()`). Each pipeline stage receives pre-aggregated DuckDB statistics, never raw logs -- the LLM interprets patterns, DuckDB does computation.

**Major components:**
1. **Ingestion Layer** -- LogParser Protocol per vendor (AWS VPC Flow Logs v2-v7); Normalizer orchestrates parsing + dedup; streaming batches for large files
2. **Storage Layer** -- Parquet for log persistence (zstd compression), DuckDB for analytics (reads Parquet directly via zero-ETL), SQLite for state/audit/checkpoints
3. **LangGraph Pipeline** -- 4-stage StateGraph (Analyze traffic patterns, Assess security posture, Generate policy proposals, Decide actions) with sync SqliteSaver checkpointing
4. **Adapter Layer** -- FirewallAdapter ABC with AdapterRegistry and explicit import-time registration; AWS SG adapter with UniversalRule bidirectional translator; AdapterCapabilities model for graceful degradation
5. **Audit Layer** -- Event-sourced immutable append-only SQLite store; AuditEvent records full lifecycle (PROPOSED, APPROVED, APPLIED, REJECTED, ROLLED_BACK) with LLM lineage (model, tokens, cost, prompt hash, response hash)
6. **LLM Layer** -- LiteLLM client factory routing to Ollama (local) or cloud providers; structured output via `.with_structured_output(PydanticModel)`
7. **Output Layer** -- JSON (programmatic), SARIF (CI/CD), Rich terminal (human) formatters consuming final pipeline state

### Critical Pitfalls

1. **LLM hallucinating overly permissive rules (0.0.0.0/0)** -- The single most important safety mechanism: implement a deterministic post-LLM validation layer (not another LLM call) that rejects CIDRs broader than /16, split-CIDR combinations covering the full address space, port ranges 0-65535, and protocol "any" without explicit `--allow-public` flag. This ships before any rule suggestion is ever shown to a user.

2. **Structured output parsing failures with Ollama** -- LiteLLM's `ollama_chat` endpoint has documented issues with structured output (GitHub #5172, #10616). Mitigate by: using `langchain-ollama` ChatOllama directly for local dev, keeping schemas flat, setting temperature=0, implementing retry-with-repair (feed ValidationError back to LLM), and testing every schema 50+ times against target models. Models >=32B are significantly more reliable than 7B variants.

3. **Checkpoint state bloat from flow log data** -- Never store raw flow logs in LangGraph state. Store only Parquet file references (`flow_log_ref: str`) and pre-aggregated statistics. Target <1MB per checkpoint. This must be decided before any pipeline node is implemented -- changing state shape later requires migrating all existing checkpoints.

4. **AWS SG allow-only model vs. DENY rules** -- The LLM will recommend blocking malicious traffic, but AWS SGs only support ALLOW rules. Inject adapter capabilities into the Generate stage prompt: "The target firewall only supports ALLOW rules." The `rule_validator_tool` must reject DENY/DROP/REJECT actions for AWS SG targets before the Decide stage. Suggest NACLs as advisory alternative.

5. **VPC Flow Log data gaps (SKIPDATA, version differences)** -- Flow logs are best-effort samples, not complete packet captures. Parse the `log-status` field, count SKIPDATA records per time window, include a `data_completeness_score` in TrafficAnalysis output. Never recommend removing a rule based solely on absence of matching traffic without a configurable minimum observation window (default: 30 days).

## Implications for Roadmap

Based on combined research, the architecture has a clear dependency chain that dictates build order. These phase suggestions follow the "Build Order" from ARCHITECTURE.md, refined by feature priorities from FEATURES.md and pitfall timing from PITFALLS.md.

### Phase 1: Project Foundation and Configuration

**Rationale:** Config, exceptions, and schemas have zero dependencies and are needed by every other component. Getting the PipelineState TypedDict right here prevents the checkpoint bloat pitfall from ever occurring.
**Delivers:** Project scaffolding (pyproject.toml with corrected versions, src layout, uv workspace), Pydantic Settings configuration system (YAML + env vars), custom exception hierarchy, and all domain model schemas (NormalizedFlowLog, UniversalRule, AdapterCapabilities, PipelineState TypedDict, AuditEvent, TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision).
**Addresses features:** Configuration file support, suggest-only mode flag, domain model foundation
**Avoids pitfalls:** Checkpoint state bloat (design PipelineState with `flow_log_ref: str` from day one); using deprecated packages (corrected version pins)

### Phase 2: Data Ingestion and Storage

**Rationale:** The pipeline cannot run without data. Ingestion and storage are independent of AI components and can be fully tested with real VPC Flow Log files. This is the data foundation everything else builds on.
**Delivers:** AWS VPC Flow Log parser (v2-v7 field handling, SKIPDATA detection, data completeness metrics), normalization pipeline with streaming batches, Parquet writer (PyArrow, zstd compression), DuckDB analytics store (top talkers, port distributions, denied flow counts, byte volume timeseries, data completeness queries).
**Addresses features:** Flow log ingestion and normalization, DuckDB storage + Parquet
**Avoids pitfalls:** VPC Flow Log data gaps (parse log-status, surface SKIPDATA counts, data_completeness_score); performance trap of loading all logs into memory (streaming ingestion with batch flushes); DuckDB memory spikes (predicate pushdown, column pruning, LIMIT clauses)

### Phase 3: Firewall Adapter and LLM Client

**Rationale:** These are the two external integration points the pipeline depends on. Building and testing them in isolation (mock AWS with moto, test Ollama structured output with harness) before wiring into the pipeline reduces debugging surface area significantly.
**Delivers:** FirewallAdapter ABC + AdapterRegistry with explicit registration, AWS SG adapter (boto3 client with `run_in_executor`, UniversalRule translator, capability declaration), deterministic rule validator tool (CIDR breadth checks, protocol checks, capacity pre-flight), LLM client factory via LiteLLM, structured output test harness (50+ runs per schema per model).
**Addresses features:** AWS SG rule fetching and display, LiteLLM + Ollama LLM client, structured Pydantic LLM output
**Avoids pitfalls:** Allow-only SG model vs. DENY rules (capability-aware validation); 60-rule limit exhaustion (pre-flight capacity check in validate_rule and dry_run); structured output parsing failures (test harness, retry-with-repair); boto3 blocking event loop (run_in_executor for all boto3 calls); LLM hallucinating overly permissive rules (deterministic validator)

### Phase 4: LangGraph Pipeline Core

**Rationale:** All dependencies are in place -- data layer, adapter, LLM client, validator. This phase wires them into the 4-stage pipeline, which is the core value proposition and primary differentiator.
**Delivers:** StateGraph definition with 4 nodes (Analyze, Assess, Generate, Decide), per-stage system prompts (with adapter capability injection in Generate), pipeline tools (traffic_query wrapping DuckDB, firewall_query wrapping adapter, rule_validator wrapping deterministic checks), sync SqliteSaver checkpointing, pipeline resume from checkpoint.
**Addresses features:** 4-stage LangGraph AI pipeline, pipeline checkpointing, risk-scored recommendations with confidence levels
**Avoids pitfalls:** LLM hallucinating overly permissive rules (rule_validator_tool in Generate stage); checkpoint state bloat (verified in Phase 1 state design, only file refs in state); async/sync mismatch (use sync SqliteSaver -- no benefit to async for single-user CLI); `interrupt()` in try/except (catch specific exceptions only)

### Phase 5: Audit, Output, and Human Review

**Rationale:** These are "leaf" systems that consume pipeline results. Building them after the pipeline is functional allows testing with real pipeline output rather than mocks.
**Delivers:** Event-sourced audit store (immutable SQLite, full LLM lineage with prompt hash, response hash, model version, token count, cost), Rich terminal output (risk-colored tables, progress spinners during LLM calls, plain-English justifications), JSON output (Pydantic model serialization), human-in-the-loop approval gate via LangGraph `interrupt()` + `Command(resume=response)`.
**Addresses features:** Immutable audit log, Rich terminal output, JSON output, human-in-the-loop gate
**Avoids pitfalls:** Audit trail gaps (store full prompt/response references, pipeline_run_id + stage_name + checkpoint_id linkage, input_data_hash); `interrupt()` in bare try/except; mutable audit events (append-only API design, no update/delete methods)

### Phase 6: CLI Integration, SARIF Output, and End-to-End Testing

**Rationale:** Final wiring of Typer commands to pipeline + output + audit. This is where the user-facing product comes together. SARIF output and test infrastructure can be built in parallel.
**Delivers:** Typer CLI commands (analyze, rules, audit, config, replay), progress feedback during LLM inference (Rich spinner with stage name, elapsed time, model, token count), demo mode with sample data (no AWS credentials required), SARIF output formatter, end-to-end integration tests, Terraform test infrastructure (VPC, SGs, EC2, Flow Logs).
**Addresses features:** Human-readable output, multiple output formats, SARIF for CI/CD, suggest-only mode as product
**Avoids pitfalls:** UX pitfalls (lazy-load AWS connections, progress spinners, Rich-formatted output, actionable error messages instead of stack traces); requiring AWS credentials for --help

### Phase Ordering Rationale

- **Foundation first (Phase 1):** Schemas and config have zero dependencies but everything depends on them. The PipelineState TypedDict design in Phase 1 prevents the checkpoint bloat pitfall from ever materializing.
- **Data before AI (Phase 2 before 3-4):** Ingestion and storage can be built and tested independently with real log files. The AI pipeline needs real data to produce meaningful results.
- **Adapter and LLM together (Phase 3):** The rule validator tool needs both adapter capabilities AND LLM output to function. Testing them in isolation first, then together, before the full pipeline reduces debugging surface.
- **Pipeline before presentation (Phase 4 before 5-6):** The pipeline must produce real results before output formatting and audit can be meaningfully tested.
- **This order addresses all 10 critical pitfalls:** Pitfalls 1, 2, 3, 4, 5, 6, 7, 8, 10 are all addressed in Phases 1-3. Pitfall 9 (eventual consistency) is Phase 2+ auto-apply and does not apply to suggest-only mode.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (LLM Client):** Ollama structured output reliability via LiteLLM is the biggest open question. Empirical testing required -- run every Pydantic schema against target Ollama models (qwen2.5:32b, llama3.1:70b, llama3.2) 50+ times to measure parse success rates. May need dual code path: langchain-ollama for local, langchain-litellm for cloud.
- **Phase 4 (Pipeline Core):** Prompt engineering for each pipeline stage requires iteration. The Generate stage prompt must inject adapter capabilities and enforce rule constraints. LangSmith tracing is valuable here for prompt debugging and eval dataset creation.
- **Phase 5 (SARIF Output):** SARIF spec has moderate complexity. Mapping PolicyProposal fields to SARIF Result/Rule/Location objects needs spec review.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Pydantic Settings, project scaffolding, exception hierarchies -- well-documented with zero ambiguity.
- **Phase 2 (Data Ingestion):** VPC Flow Log parsing (stable AWS-documented format), Parquet writing (PyArrow), DuckDB analytics -- all have official examples and extensive documentation.
- **Phase 6 (CLI Integration):** Typer CLI wiring, Rich formatting, Terraform HCL -- extensive documentation and examples available.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every dependency verified on PyPI with current versions 2026-03-07. LangGraph 1.0 GA is a major stability milestone. All version corrections from original spec documented. |
| Features | HIGH | Competitor analysis across 6+ NSPM tools (Tufin, AlgoSec, FireMon, AWS Firewall Manager, GCP Firewall Insights, Prowler). Feature priorities validated against PCI-DSS 4.0 requirements. Skybox shutdown creates market opportunity. |
| Architecture | HIGH | LangGraph StateGraph patterns verified against official docs, community best practices, and production case studies (Uber, LinkedIn, Klarna). Ports-and-adapters pattern is well-established. Build order validated against dependency analysis. |
| Pitfalls | HIGH | All critical pitfalls verified against official AWS docs, LangGraph GitHub issues, LiteLLM bug reports, and OWASP LLM Top 10. Recovery strategies provided for each. |

**Overall confidence:** HIGH

### Gaps to Address

- **Ollama structured output reliability:** LiteLLM's `ollama_chat` endpoint has documented issues (GitHub #5172, #10616). Must be validated empirically in Phase 3 with a test harness. Fallback: use `langchain-ollama` ChatOllama directly for local Ollama, LiteLLM only for cloud providers.
- **Optimal Ollama model selection:** Which models produce reliable structured output for security domain analysis? Research suggests qwen2.5:32b and llama3.1:70b are more reliable than 7B variants, but benchmarking is needed against PolicyFoundry's specific schemas.
- **Prompt engineering for security domain:** System prompts for each pipeline stage require iterative development. No off-the-shelf prompts exist for traffic-to-rule analysis. LangSmith evaluation datasets should be built during Phase 4.
- **DuckDB memory with large Parquet files:** Can spike to 4GB RAM for 120MB Parquet (documented GitHub #17262). Pre-aggregation queries must use aggressive LIMIT and time-window filters. May need `memory_limit` configuration.
- **Single vs. separate SQLite files:** Using one SQLite file for checkpoints + audit + state prevents different retention policies. Recommendation: use separate files from day one -- checkpoint.db (short TTL), audit.db (1-year PCI-DSS retention), state.db (application state).

## Sources

### Primary (HIGH confidence)
- LangGraph 1.0 GA documentation and migration guide -- StateGraph, interrupt(), checkpointing, reducer patterns
- AWS VPC Flow Log official documentation -- log formats v2-v7, SKIPDATA, aggregation intervals
- AWS Security Group official documentation -- rule limits (60 per SG), allow-only model, DryRun support, counting formula
- PyPI verified package versions (all checked 2026-03-07) -- LangGraph 1.0.10, LangChain 1.2.10, DuckDB 1.4.4, Pydantic 2.12.5, etc.
- PCI-DSS 4.0 requirements -- Requirement 10 (audit trails), business justification mandate, 1-year retention
- NSPM vendor feature comparisons -- FireMon, AlgoSec, Tufin capabilities documented across multiple comparison sources

### Secondary (MEDIUM confidence)
- LiteLLM Ollama structured output GitHub issues (#5172, #10616) -- known parsing failures with ollama_chat endpoint
- LangGraph community best practices (sparkco.ai, swarnendu.de) -- state management, TypedDict vs Pydantic patterns
- DuckDB memory management docs and GitHub issues (#17262) -- memory spike patterns with large Parquet files
- OWASP LLM Top 10 2025 -- LLM-specific vulnerability patterns applicable to security tooling

### Tertiary (LOW confidence)
- Ollama structured output reliability across model variants -- limited benchmarking data; needs empirical validation in Phase 3
- SARIF output adoption rates for security CLI tools -- assumed valuable based on GitHub Code Scanning ecosystem; not validated with target users
- LiteLLM budget tracking with Ollama local models -- local models have no real cost; unclear how budget tracking handles this edge case

---
*Research completed: 2026-03-07*
*Ready for roadmap: yes*

# Architecture Research

**Domain:** AI-powered firewall policy management (CLI pipeline)
**Researched:** 2026-03-07
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLI LAYER (Typer + Rich)                       │
│  analyze | rules | audit | config | replay | apply                     │
├────────────┬────────────┬──────────────┬────────────┬──────────────────┤
│            │            │              │            │                  │
│            ▼            │              │            │                  │
│  ┌──────────────────┐   │              │            │                  │
│  │ INGESTION LAYER  │   │              │            │                  │
│  │ LogParser(Proto)  │   │              │            │                  │
│  │ ├─ AwsVpcParser  │   │              │            │                  │
│  │ └─ [Future]      │   │              │            │                  │
│  │ Normalizer       │   │              │            │                  │
│  └────────┬─────────┘   │              │            │                  │
│           │              │              │            │                  │
│           ▼              │              │            │                  │
│  ┌──────────────────┐   │              │            │                  │
│  │  STORAGE LAYER   │   │              │            │                  │
│  │ Parquet (logs)   │◄──┼──────────────┼────────────┤                  │
│  │ DuckDB (OLAP)    │   │              │            │                  │
│  │ SQLite (state)   │◄──┼──────────────┼────────────┤                  │
│  └────────┬─────────┘   │              │            │                  │
│           │              │              │            │                  │
│           ▼              ▼              │            │                  │
│  ┌─────────────────────────────────┐   │            │                  │
│  │    LANGGRAPH PIPELINE           │   │            │                  │
│  │                                 │   │            │                  │
│  │  ┌─────────┐    ┌──────────┐   │   │            │                  │
│  │  │ ANALYZE │───▶│ ASSESS   │   │   │            │                  │
│  │  │ Traffic │    │ Security │   │   │            │                  │
│  │  └─────────┘    └────┬─────┘   │   │            │                  │
│  │                      │         │   │            │                  │
│  │  ┌─────────┐    ┌────▼─────┐   │   │            │                  │
│  │  │ DECIDE  │◄───│ GENERATE │   │   │            │                  │
│  │  │ Action  │    │ Policy   │   │   │            │                  │
│  │  └────┬────┘    └──────────┘   │   │            │                  │
│  │       │                        │   │            │                  │
│  │  ┌────▼──────────────────┐     │   │            │                  │
│  │  │ HUMAN REVIEW (HITL)  │     │   │            │                  │
│  │  │ interrupt() + resume  │     │   │            │                  │
│  │  └────┬──────────────────┘     │   │            │                  │
│  │       │                        │   │            │                  │
│  │  SQLiteSaver (checkpoints)     │   │            │                  │
│  └───────┼────────────────────────┘   │            │                  │
│          │                             │            │                  │
│          ▼                             ▼            ▼                  │
│  ┌──────────────────┐   ┌──────────────────┐  ┌──────────────┐       │
│  │ ADAPTER LAYER    │   │  AUDIT LAYER     │  │ OUTPUT LAYER │       │
│  │ FirewallAdapter  │   │  EventStore      │  │ JSON         │       │
│  │ ├─ AwsSgAdapter  │   │  (append-only    │  │ SARIF        │       │
│  │ └─ [Future]      │   │   SQLite)        │  │ Rich TUI     │       │
│  │ AdapterRegistry  │   └──────────────────┘  └──────────────┘       │
│  │ UniversalRule    │                                                 │
│  └──────────────────┘                                                 │
│                                                                       │
│  ┌──────────────────┐   ┌──────────────────┐                         │
│  │ CONFIG LAYER     │   │   LLM LAYER      │                         │
│  │ Pydantic Settings│   │ LiteLLM Router   │                         │
│  │ YAML + env vars  │   │ ├─ Ollama (local)│                         │
│  │                  │   │ └─ [Future cloud] │                         │
│  └──────────────────┘   └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘

External Dependencies:
  ├── AWS APIs (boto3) ─── Security Groups, VPC Flow Logs, S3
  ├── Ollama (local) ──── LLM inference via OpenAI-compatible API
  └── [Future] ────────── Bedrock, OpenAI, threat intel feeds
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| CLI Layer | User-facing commands, argument parsing, progress display | Typer app with Rich console output; `asyncio.run()` at entrypoint only |
| Ingestion Layer | Parse vendor-specific logs, normalize to unified schema | `LogParser` Protocol per vendor; `Normalizer` orchestrates parsing + dedup |
| Storage Layer | Persist logs (Parquet), analytics queries (DuckDB), state/audit (SQLite) | Three stores with distinct responsibilities; DuckDB reads Parquet directly |
| LangGraph Pipeline | 4-stage AI analysis: Analyze, Assess, Generate, Decide | `StateGraph` with `PipelineState` TypedDict; SQLiteSaver checkpointer |
| Adapter Layer | Read/write firewall rules across vendors via universal schema | `FirewallAdapter` ABC + `AdapterRegistry`; vendor subpackages |
| Audit Layer | Immutable event log for every rule proposal lifecycle event | Append-only SQLite table; `AuditEvent` Pydantic model |
| Output Layer | Format results for different consumers | JSON (programmatic), SARIF (CI/CD), Rich (human terminal) |
| Config Layer | Load and validate all configuration | `Pydantic BaseSettings` from YAML + env vars |
| LLM Layer | Route LLM calls to providers with fallback | LiteLLM client factory; structured output via `.with_structured_output()` |

## Recommended Project Structure

```
src/
├── policyfoundry/              # Package root (renamed from firewall_ai)
│   ├── __init__.py             # Version, package metadata
│   ├── main.py                 # Typer CLI entrypoint
│   ├── exceptions.py           # Custom exception hierarchy
│   │
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py         # Pydantic BaseSettings (YAML + env)
│   │   └── providers.py        # LLM provider registry + validation
│   │
│   ├── ingestion/              # Log parsing and normalization
│   │   ├── __init__.py
│   │   ├── base.py             # LogParser Protocol
│   │   ├── schema.py           # NormalizedFlowLog + enums
│   │   ├── aws_vpc.py          # AWS VPC Flow Log parser
│   │   └── normalizer.py       # Multi-vendor normalization pipeline
│   │
│   ├── storage/                # Data persistence
│   │   ├── __init__.py
│   │   ├── parquet_store.py    # Parquet write/read (pyarrow)
│   │   ├── duckdb_store.py     # DuckDB analytical queries
│   │   └── sqlite_store.py     # SQLite state + audit tables
│   │
│   ├── pipeline/               # LangGraph AI pipeline
│   │   ├── __init__.py
│   │   ├── graph.py            # StateGraph definition + compilation
│   │   ├── state.py            # PipelineState TypedDict + output models
│   │   ├── llm.py              # LLM client factory (LiteLLM)
│   │   ├── nodes/              # Pipeline stage implementations
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py      # Stage 1: traffic pattern analysis
│   │   │   ├── assess.py       # Stage 2: security posture assessment
│   │   │   ├── generate.py     # Stage 3: policy generation
│   │   │   ├── decide.py       # Stage 4: action decision gate
│   │   │   └── human_review.py # HITL approval via interrupt()
│   │   ├── tools/              # LangChain @tool functions
│   │   │   ├── __init__.py
│   │   │   ├── traffic_query.py
│   │   │   ├── firewall_query.py
│   │   │   └── rule_validator.py
│   │   └── prompts/            # System prompts per stage
│   │       ├── __init__.py
│   │       ├── analyze.py
│   │       ├── assess.py
│   │       ├── generate.py
│   │       └── decide.py
│   │
│   ├── adapters/               # Firewall vendor plugins
│   │   ├── __init__.py
│   │   ├── base.py             # FirewallAdapter ABC
│   │   ├── registry.py         # Plugin discovery + registration
│   │   ├── schema.py           # UniversalRule + AdapterCapabilities
│   │   └── aws_sg/             # AWS Security Groups adapter
│   │       ├── __init__.py
│   │       ├── adapter.py      # AwsSecurityGroupAdapter
│   │       ├── translator.py   # UniversalRule <-> IpPermission
│   │       └── client.py       # boto3 EC2 wrapper
│   │
│   ├── audit/                  # Event-sourced audit system
│   │   ├── __init__.py
│   │   ├── models.py           # AuditEvent, EventType, ActorInfo
│   │   └── event_store.py      # Immutable append-only store
│   │
│   ├── output/                 # Result formatters
│   │   ├── __init__.py
│   │   ├── json_output.py
│   │   ├── sarif_output.py
│   │   └── rich_output.py
│   │
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── ip_utils.py
│       └── retry.py
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/               # Sample log files, rule snapshots
│   ├── unit/
│   ├── integration/
│   └── eval/                   # LLM output quality evaluations
│
└── infra/                      # Terraform/CDK for test AWS env
    └── terraform/
```

### Structure Rationale

- **`pipeline/` instead of `agents/`:** The project uses a deterministic 4-stage pipeline, not free-roaming agents. The name reflects the linear flow: Analyze then Assess then Generate then Decide. Each node is a function, not an autonomous agent. This keeps the mental model simple.
- **`adapters/` as vendor subpackages:** Each firewall vendor (aws_sg, future paloalto, fortinet) gets a subdirectory with adapter + translator + client. This enforces separation and makes it obvious where to add a new vendor.
- **`storage/` unified:** DuckDB, Parquet, and SQLite serve distinct roles but share a layer. DuckDB reads Parquet files directly (no ETL step), so they are co-located rather than split.
- **`pipeline/prompts/` separated from nodes:** Prompts change at a different cadence than node logic. Isolating them makes prompt iteration easier and supports future prompt versioning.
- **No `models.py` mega-file:** Domain models live where they are used: `ingestion/schema.py`, `adapters/schema.py`, `pipeline/state.py`, `audit/models.py`. This prevents a single models file from becoming a dependency magnet.

## Architectural Patterns

### Pattern 1: LangGraph StateGraph with Typed Pipeline State

**What:** Define the entire pipeline state as a single `TypedDict` with `Annotated` reducer fields. Each node reads from state, calls tools and LLM, returns a partial state update. The graph compiles to an immutable DAG with SQLite checkpointing.

**When to use:** Always for this project. The 4-stage pipeline is inherently sequential with checkpointing at each boundary. Subgraphs are unnecessary because the stages share a single state schema and there is no agent autonomy (no loops, no dynamic spawning).

**Trade-offs:** Simple and debuggable. Limitation: all nodes share state, so one stage's output schema change ripples. Mitigated by Pydantic validation on each stage's output model.

**Example:**
```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

class PipelineState(TypedDict):
    # Input
    flow_logs: list[NormalizedFlowLog]
    target_firewall: str
    firewall_config: dict

    # Stage outputs (each set by one node, read by subsequent)
    traffic_analysis: TrafficAnalysis | None
    security_assessment: SecurityAssessment | None
    policy_proposals: list[PolicyProposal] | None
    decisions: list[RuleDecision] | None
    approval_status: str

    # Metadata
    run_id: str
    errors: Annotated[list[str], lambda a, b: a + b]  # append reducer
    messages: Annotated[list, add_messages]  # LangGraph message reducer

def build_pipeline(settings: Settings) -> CompiledGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("analyze", analyze_traffic_node)
    graph.add_node("assess", assess_security_node)
    graph.add_node("generate", generate_policy_node)
    graph.add_node("decide", decide_action_node)
    graph.add_node("human_review", human_review_node)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "assess")
    graph.add_edge("assess", "generate")
    graph.add_edge("generate", "decide")
    graph.add_conditional_edges(
        "decide",
        route_by_approval_needed,
        {"needs_review": "human_review", "complete": END},
    )
    graph.add_edge("human_review", END)

    checkpointer = SqliteSaver.from_conn_string(
        str(settings.storage.state_db)
    )
    return graph.compile(checkpointer=checkpointer)
```

**Critical design decisions:**
- Use `SqliteSaver` (synchronous), not `AsyncSqliteSaver`. The CLI runs pipeline stages sequentially. AsyncSqliteSaver adds aiosqlite complexity for no throughput gain in a single-user CLI. [Confidence: HIGH, per LangGraph docs]
- Use `TypedDict` for state, not Pydantic BaseModel. LangGraph's `Annotated` reducer pattern works naturally with TypedDict. Pydantic models for state cause serialization overhead at checkpoints. [Confidence: HIGH, per LangGraph best practices]
- Stage output models (TrafficAnalysis, SecurityAssessment, etc.) ARE Pydantic BaseModel for LLM structured output validation. The distinction: TypedDict for graph state, Pydantic for LLM output schemas.

### Pattern 2: Structured Output via Pydantic + with_structured_output()

**What:** Every LLM call uses LangChain's `.with_structured_output(PydanticModel)` to enforce a schema on LLM responses. The Pydantic model's class name, docstring, and field descriptions become part of the prompt, guiding the LLM to produce valid JSON.

**When to use:** Every node that calls an LLM. No exceptions. Free-text LLM responses in a security tool are a recipe for parsing bugs and hallucination-driven rule changes.

**Trade-offs:** Small models (Ollama local) may struggle with complex schemas. Mitigation: keep schemas flat (no deeply nested models), provide clear field descriptions, use `handle_errors=True` for automatic retry on validation failure.

**Example:**
```python
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

class TrafficAnalysis(BaseModel):
    """Analysis of network traffic patterns from flow logs."""

    summary: str = Field(
        description="2-3 sentence summary of observed traffic patterns"
    )
    total_flows: int = Field(description="Total number of flow records analyzed")
    top_talkers: list[dict] = Field(
        description="Top source-destination pairs by flow count"
    )
    anomaly_scores: list[AnomalyReport] = Field(
        default_factory=list,
        description="Detected anomalies with severity and evidence"
    )

async def analyze_traffic_node(state: PipelineState) -> dict:
    llm = create_llm(settings)
    structured_llm = llm.with_structured_output(TrafficAnalysis)

    # Pre-aggregate via DuckDB (LLM never sees raw logs)
    stats = await duckdb_store.top_talkers(n=20, hours=24)

    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=f"Traffic statistics:\n{json.dumps(stats)}")
    ]

    result: TrafficAnalysis = await structured_llm.ainvoke(messages)
    return {"traffic_analysis": result}
```

**Ollama-specific concern (MEDIUM confidence):** LiteLLM's Ollama structured output support has known issues. The `ollama_chat` endpoint sometimes fails to produce valid JSON. Mitigations: (1) Use `format="json"` mode with Ollama. (2) Consider the Instructor library as a fallback for schema enforcement. (3) Test with multiple Ollama models (llama3, mistral, qwen) to find which produce reliable structured output. This is a research flag for the implementation phase.

### Pattern 3: Firewall Adapter Plugin Architecture (Ports and Adapters)

**What:** Define an abstract `FirewallAdapter` ABC that declares the universal rule lifecycle: connect, get_rules, validate, dry_run, apply, rollback. Each vendor implements this interface in its own subpackage. An `AdapterRegistry` discovers and manages adapter instances. A `UniversalRule` Pydantic model is the lingua franca between the pipeline and any vendor.

**When to use:** This is the core extensibility mechanism. Every firewall vendor interaction flows through the adapter. The pipeline never calls boto3 or vendor APIs directly.

**Trade-offs:** The universal rule schema must be a superset of all vendor capabilities. Fields that don't apply to a given vendor (e.g., `application` for AWS SGs which lack L7 filtering) are optional. The `AdapterCapabilities` model lets the pipeline gracefully degrade: if a vendor does not support dry-run, the pipeline falls back to enhanced validation.

**Example:**
```python
from abc import ABC, abstractmethod

class FirewallAdapter(ABC):
    """Universal interface for firewall vendor integrations."""

    @abstractmethod
    async def connect(self, config: AdapterConfig) -> None:
        """Validate credentials and establish connection."""

    @abstractmethod
    async def get_rules(
        self, filter: RuleFilter | None = None
    ) -> list[UniversalRule]:
        """Fetch current rules translated to universal schema."""

    @abstractmethod
    async def validate_rule(self, rule: UniversalRule) -> ValidationResult:
        """Check rule against vendor constraints without applying."""

    @abstractmethod
    async def dry_run(self, rule: UniversalRule) -> DryRunResult:
        """Simulate rule application. Falls back to validate if unsupported."""

    @abstractmethod
    async def apply_rule(self, rule: UniversalRule) -> ApplyResult:
        """Apply rule change. Returns rollback handle."""

    @abstractmethod
    async def rollback(self, handle: RollbackHandle) -> None:
        """Revert a previously applied change."""

    @abstractmethod
    def capabilities(self) -> AdapterCapabilities:
        """Declare what this adapter supports."""

class AdapterRegistry:
    """Discovers and manages firewall adapter instances."""

    def __init__(self):
        self._adapters: dict[str, type[FirewallAdapter]] = {}

    def register(self, name: str, adapter_cls: type[FirewallAdapter]) -> None:
        self._adapters[name] = adapter_cls

    def get(self, name: str, config: AdapterConfig) -> FirewallAdapter:
        cls = self._adapters[name]
        return cls(config)

    def list_adapters(self) -> list[str]:
        return list(self._adapters.keys())

# Registration happens at import time in each adapter's __init__.py
# adapters/aws_sg/__init__.py:
#   from policyfoundry.adapters.registry import default_registry
#   from policyfoundry.adapters.aws_sg.adapter import AwsSecurityGroupAdapter
#   default_registry.register("aws-sg", AwsSecurityGroupAdapter)
```

**Key architectural choice:** Use explicit registration via `__init__.py` imports, not dynamic plugin discovery (entry_points, importlib scanning). For Phase 1 with one adapter, dynamic discovery is over-engineering. When a second adapter arrives, evaluate whether to add entry_points. [Confidence: HIGH -- standard Python plugin pattern]

### Pattern 4: Human-in-the-Loop via LangGraph interrupt()

**What:** The Decide node routes proposals that need human approval to a `human_review` node. This node uses LangGraph's `interrupt()` function to pause the graph, serialize state to SQLite via the checkpointer, and surface the proposals to the CLI. The user reviews proposals in Rich-formatted terminal output and responds with approve/reject per rule. The CLI resumes the graph with `Command(resume=response)`.

**When to use:** Phase 1 is 100% suggest-only, meaning every rule change hits the human review gate. In future phases, the risk-based router (`route_by_approval_needed`) will skip the gate for low-risk auto-approved changes.

**Trade-offs:** The `interrupt()` approach is cleaner than `interrupt_before` for this use case because the node can prepare the approval payload (Rich-formatted rule details) before pausing. With `interrupt_before`, the node has not yet run so there is nothing to show the user. The trade-off: code before `interrupt()` re-executes on resume, so side effects must be idempotent.

**Example:**
```python
from langgraph.types import interrupt, Command

async def human_review_node(state: PipelineState) -> dict:
    """Present rule proposals to human for approval."""
    proposals = state["decisions"]

    # Prepare approval payload (JSON-serializable)
    review_payload = {
        "run_id": state["run_id"],
        "proposals": [
            {
                "decision_id": d.decision_id,
                "action": d.action,
                "risk_level": d.risk_level,
                "reason": d.reason,
                "vendor_rule": d.vendor_rule,
            }
            for d in proposals
            if d.approval_required
        ],
        "total_proposals": len(proposals),
    }

    # Pause graph -- payload surfaces in __interrupt__
    human_response = interrupt(review_payload)

    # Resume lands here with the user's decisions
    # human_response = {"approved": ["dec-001", "dec-003"], "rejected": ["dec-002"]}
    approved_ids = set(human_response.get("approved", []))

    updated_decisions = []
    for d in proposals:
        if d.decision_id in approved_ids:
            updated_decisions.append(d)

    return {
        "decisions": updated_decisions,
        "approval_status": "reviewed",
    }
```

**CLI-side resume pattern:**
```python
# In main.py analyze command:
config = {"configurable": {"thread_id": run_id}}
result = pipeline.invoke(initial_state, config)

if "__interrupt__" in result:
    payload = result["__interrupt__"][0].value
    # Display with Rich tables
    display_proposals(payload["proposals"])
    # Collect user approval
    response = collect_approval(payload["proposals"])
    # Resume
    final = pipeline.invoke(Command(resume=response), config)
```

### Pattern 5: Event-Sourced Immutable Audit Log

**What:** Every lifecycle event for a rule change proposal (PROPOSED, APPROVED, APPLIED, REJECTED, ROLLED_BACK) is recorded as an immutable `AuditEvent` in a SQLite append-only table. Events are never updated or deleted. The current state of any proposal is derived by replaying its events.

**When to use:** Every adapter operation, every pipeline completion, every human approval decision. The audit log is the compliance backbone (PCI-DSS 4.0 requires 1 year retention with 3 months immediately accessible).

**Trade-offs:** Append-only means the table grows forever. Mitigated by retention policies (archive events older than 1 year) and the fact that event sizes are small (2-5 KB each). SQLite handles millions of rows without issue for a CLI tool.

**Example:**
```python
class AuditEventStore:
    """Immutable, append-only audit event store backed by SQLite."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                pipeline_run_id TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                target_firewall TEXT NOT NULL,
                rule_before TEXT,          -- JSON serialized UniversalRule
                rule_after TEXT,           -- JSON serialized UniversalRule
                business_justification TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                ai_confidence REAL,
                ai_reasoning TEXT,
                llm_model_used TEXT,
                llm_tokens_used INTEGER,
                llm_cost_usd REAL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # No UPDATE or DELETE operations exposed -- immutability by API design

    async def record(self, event: AuditEvent) -> None:
        """Append an immutable audit event."""
        self._conn.execute(
            "INSERT INTO audit_events (...) VALUES (...)",
            event.to_row(),
        )
        self._conn.commit()

    async def get_events(
        self,
        run_id: str | None = None,
        event_type: EventType | None = None,
        since: datetime | None = None,
    ) -> list[AuditEvent]:
        """Query events with optional filters."""
        ...
```

**Critical: Immutability is enforced at the API level, not the database level.** SQLite has no built-in append-only mode. The `AuditEventStore` class exposes only `record()` and `get_events()`. There are no `update()` or `delete()` methods. If a rule decision is reversed, a new ROLLED_BACK event is appended -- the original APPLIED event remains.

## Data Flow

### Primary Pipeline Flow

```
User runs: policyfoundry analyze --source aws-vpc --firewall aws-sg

    [1] CLI parses args, loads config
         │
    [2] Ingestion: AwsVpcParser reads logs from S3/local file
         │ yields NormalizedFlowLog stream
         │
    [3] Storage: ParquetStore writes batch to .parquet file
         │ DuckDB registers parquet directory
         │
    [4] Pipeline builds initial PipelineState
         │
    [5] ANALYZE node:
         │  ├── DuckDB: pre-aggregate stats (top talkers, port dist, etc.)
         │  ├── LLM: interpret stats → TrafficAnalysis (Pydantic)
         │  └── Checkpoint: state saved to SQLite
         │
    [6] ASSESS node:
         │  ├── Adapter: fetch current SG rules → list[UniversalRule]
         │  ├── LLM: compare traffic vs rules → SecurityAssessment
         │  └── Checkpoint: state saved
         │
    [7] GENERATE node:
         │  ├── LLM: produce rule proposals → list[PolicyProposal]
         │  ├── Tool: validate each proposal vs adapter capabilities
         │  └── Checkpoint: state saved
         │
    [8] DECIDE node:
         │  ├── LLM: final gate → list[RuleDecision]
         │  ├── Audit: record PROPOSED events
         │  └── Route: all → human_review (Phase 1)
         │
    [9] HUMAN REVIEW node:
         │  ├── interrupt() → pauses graph, saves state
         │  ├── CLI: displays proposals with Rich tables
         │  ├── User: approves/rejects each proposal
         │  ├── Command(resume=response) → resumes graph
         │  └── Audit: record APPROVED/REJECTED events
         │
    [10] OUTPUT: format results → JSON / SARIF / Rich terminal
```

### Checkpoint + Resume Flow (Pipeline Resumability)

```
Pipeline fails at stage 3 (e.g., LLM timeout)
    │
    ├── Stages 1-2 results saved in SQLiteSaver checkpoint
    │
User runs: policyfoundry replay --run-id <id> --from-stage generate
    │
    ├── Load checkpoint for run_id at thread_id
    ├── Restore PipelineState with stages 1-2 already populated
    ├── Resume from GENERATE node (no LLM re-invocation for stages 1-2)
    └── Continue through DECIDE → HUMAN REVIEW → OUTPUT
```

### Adapter Translation Flow

```
PolicyProposal (vendor-neutral)
    │
    ▼
Translator.to_vendor_format(universal_rule)
    │
    ├── AWS SG: UniversalRule → IpPermission dict
    │   ├── Map protocol enum to AWS string
    │   ├── Map NetworkEndpoint to CidrIp or UserIdGroupPairs
    │   ├── Truncate description to 255 chars (AWS limit)
    │   └── Handle missing port_range for ICMP (-1 protocol)
    │
    └── [Future] Palo Alto: UniversalRule → PAN-OS JSON
        ├── Map to zone-based rule structure
        ├── Include App-ID application field
        └── Candidate config → commit workflow
```

### Key Data Flows

1. **Logs to Analytics:** Raw vendor logs -> Normalizer -> Parquet files -> DuckDB reads Parquet directly (zero-ETL). DuckDB's predicate pushdown and column pruning mean only relevant data enters memory.

2. **Pipeline State to Checkpoint:** After each node completes, LangGraph serializes the full PipelineState to SQLite via SqliteSaver. Each checkpoint is keyed by (thread_id, checkpoint_id). This enables both resume-from-failure and time-travel debugging.

3. **LLM Output to Domain Models:** LLM response -> `.with_structured_output()` -> Pydantic model validation -> typed field in PipelineState. If validation fails, LangChain auto-retries with error context (configurable via `handle_errors`).

4. **Decisions to Audit Trail:** Each RuleDecision generates an AuditEvent at the PROPOSED stage. Human approval generates APPROVED/REJECTED events. Future auto-apply generates APPLIED events. All events reference the pipeline_run_id for full traceability.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 security group, <1M flows | Current architecture (DuckDB in-memory, SQLite, single pipeline) handles this with ease |
| 10 security groups, 1-10M flows | Parquet partitioned by date; DuckDB file-backed (not in-memory); batch pipeline per SG or parallel graph invocations |
| 100+ SGs, 100M+ flows | Outgrows CLI tier. Cloud tier needed: ClickHouse for analytics, PostgreSQL for state, PostgresSaver for checkpoints, Kafka for ingestion buffer |

### Scaling Priorities

1. **First bottleneck -- LLM latency:** Each pipeline stage waits for LLM response. With Ollama local, expect 5-30 seconds per stage depending on model size and context. Mitigation: checkpointing means failures do not restart from scratch. Future: parallel LLM calls within a stage (e.g., assess multiple risk scores concurrently).

2. **Second bottleneck -- DuckDB memory:** Large Parquet directories (10M+ rows) will push DuckDB memory usage. Mitigation: DuckDB can spill to disk, and pre-aggregation queries should use `LIMIT` and time-window filters aggressively. The LLM never sees raw logs -- only aggregated statistics.

3. **Third bottleneck -- SQLite write contention:** Not an issue for CLI (single-user), but AsyncSqliteSaver under concurrent access will bottleneck. This is a Phase 2 (cloud/multi-user) concern that is solved by migrating to PostgresSaver.

## Anti-Patterns

### Anti-Pattern 1: Passing Raw Logs to the LLM

**What people do:** Feed all normalized flow logs directly into the LLM prompt as context.
**Why it's wrong:** A 1M-row flow log dump will blow any context window and cost a fortune in tokens. Even with large context models, the LLM cannot meaningfully analyze raw log lines -- it needs statistical patterns.
**Do this instead:** Pre-aggregate with DuckDB (top talkers, port distributions, denied flow counts, byte volume timeseries). Pass only the aggregated statistics (20-50 rows) to the LLM. The LLM interprets patterns; DuckDB does computation.

### Anti-Pattern 2: Using Pydantic BaseModel for LangGraph State

**What people do:** Define PipelineState as a Pydantic BaseModel for validation benefits.
**Why it's wrong:** LangGraph's `Annotated` reducer pattern (e.g., `Annotated[list[str], lambda a, b: a + b]`) works naturally with TypedDict but fights with Pydantic BaseModel's validation and serialization. Checkpointing overhead increases because Pydantic models must be serialized/deserialized at every node boundary.
**Do this instead:** Use TypedDict for the graph state schema. Use Pydantic BaseModel for the individual output models (TrafficAnalysis, SecurityAssessment, etc.) that are values within the state. This gives you the best of both: lightweight state management with validated LLM outputs.

### Anti-Pattern 3: Dynamic Plugin Discovery for a Single Adapter

**What people do:** Build elaborate entry_point-based plugin systems, importlib scanning, and plugin configuration before they have a second adapter.
**Why it's wrong:** Premature abstraction. The registry, ABC interface, and universal rule schema already provide the extensibility seam. Dynamic discovery adds complexity (debugging registration failures, import ordering issues) for zero current benefit.
**Do this instead:** Use explicit import-time registration in each adapter's `__init__.py`. The registry pattern supports adding vendors trivially. When the second adapter arrives, evaluate if entry_points add value.

### Anti-Pattern 4: Mutable Audit Events

**What people do:** Update audit events when status changes (e.g., change PROPOSED to APPROVED in-place).
**Why it's wrong:** Violates event sourcing. Loses the timeline of what happened when. Makes compliance auditors nervous. PCI-DSS 4.0 requires tamper-evident logs.
**Do this instead:** Always append a new event. The current state of a rule proposal is derived by scanning its event chain: PROPOSED -> APPROVED -> APPLIED. Each event is immutable after creation.

### Anti-Pattern 5: Wrapping interrupt() in try/except

**What people do:** Wrap the LangGraph `interrupt()` call in a try/except block for "safety."
**Why it's wrong:** `interrupt()` works by raising a special exception internally. A bare `except` catches this exception and breaks the interrupt mechanism entirely. The graph will not pause.
**Do this instead:** Never wrap `interrupt()` in bare try/except. If error handling is needed around interrupt, catch specific exception types only (never `Exception` or bare `except`).

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| AWS EC2 (Security Groups) | boto3 `describe_security_group_rules`, `authorize_security_group_ingress/egress` | Supports `DryRun=True` for validation without changes. Rate limited: respect API throttling. |
| AWS S3 (VPC Flow Logs) | boto3 `get_object` to read log files from S3 bucket | Logs are space-delimited text. Handle pagination for large buckets. |
| Ollama (local LLM) | HTTP to `localhost:11434` via LiteLLM's `ollama/` prefix | Must be running separately. Use `format="json"` for structured output. Test model compatibility. |
| LangSmith (observability) | Env vars: `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY` | Optional but recommended. Every pipeline run traced end-to-end. Useful for prompt debugging. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI <-> Pipeline | CLI builds initial PipelineState, invokes compiled graph, reads result | CLI owns the `asyncio.run()` event loop. Pipeline is async internally. |
| Pipeline <-> Storage | Nodes call DuckDB store methods for analytics queries | DuckDB store is injected into nodes via settings/dependency. Not a global singleton. |
| Pipeline <-> Adapters | Assess node calls `adapter.get_rules()`. Decide node calls `adapter.validate_rule()` | Adapter instance created from registry + config at pipeline start. Passed via state or closure. |
| Pipeline <-> LLM | Each node calls `llm.with_structured_output(Model).ainvoke(messages)` | LLM client created once per pipeline run via factory. LiteLLM handles routing + fallback. |
| Pipeline <-> Audit | Decide and Human Review nodes call `audit_store.record(event)` | Audit store injected into relevant nodes. Events are fire-and-forget (append-only). |
| Human Review <-> CLI | `interrupt()` pauses graph. CLI reads `__interrupt__` payload. CLI calls `Command(resume=response)` | The checkpointer must persist state between these two invocations. Thread ID links them. |

## Build Order (Dependencies Between Components)

The components have clear dependency chains that dictate build order:

```
Phase 1: Foundation (no dependencies)
  ├── Config (settings.py, providers.py)
  ├── Exceptions (exception hierarchy)
  └── Ingestion schemas (NormalizedFlowLog, enums)

Phase 2: Data Layer (depends on Phase 1)
  ├── Ingestion parsers (aws_vpc.py, normalizer.py)
  ├── Parquet store (write/read logs)
  └── DuckDB store (analytics queries over Parquet)

Phase 3: Domain Models (depends on Phase 1)
  ├── Adapter schemas (UniversalRule, AdapterCapabilities)
  ├── Pipeline state (PipelineState TypedDict, output models)
  └── Audit models (AuditEvent, EventType)

Phase 4: Adapter (depends on Phase 3)
  ├── FirewallAdapter ABC
  ├── AdapterRegistry
  └── AWS SG adapter (client + translator + adapter)

Phase 5: Pipeline Core (depends on Phases 2, 3, 4)
  ├── LLM client factory
  ├── Pipeline tools (traffic_query, firewall_query, rule_validator)
  ├── Prompts (per-stage system prompts)
  ├── Nodes (analyze, assess, generate, decide, human_review)
  └── Graph definition (StateGraph + compilation)

Phase 6: Supporting Systems (depends on Phase 3)
  ├── Audit event store (SQLite append-only)
  ├── SQLite state store (pipeline runs, rule history)
  └── Output formatters (JSON, SARIF, Rich)

Phase 7: Integration (depends on all above)
  ├── CLI commands (wire Typer commands to pipeline + output)
  ├── End-to-end testing
  └── Terraform test infrastructure
```

**Why this order:** Config and schemas have zero dependencies and are needed by everything else. The data layer (ingestion + storage) can be built and tested independently of the AI pipeline. Adapter schemas must exist before the pipeline can reference UniversalRule in its state. The pipeline depends on tools that query DuckDB and adapters. Audit and output are "leaf" systems that consume pipeline results but have no upstream dependencies. CLI wiring happens last because it orchestrates all components.

## Sources

- [LangGraph Interrupts Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) - Official docs on interrupt() and interrupt_before patterns
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) - Checkpointing architecture
- [langgraph-checkpoint-sqlite v3.0.3](https://pypi.org/project/langgraph-checkpoint-sqlite/) - SqliteSaver and AsyncSqliteSaver
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output) - with_structured_output() patterns
- [LangGraph Best Practices](https://www.swarnendu.de/blog/langgraph-best-practices/) - State management, node design
- [Mastering LangGraph State Management 2025](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025/) - TypedDict + Annotated reducer patterns
- [LiteLLM Ollama Integration](https://docs.litellm.ai/docs/providers/ollama) - Ollama provider configuration
- [LiteLLM Structured Outputs](https://docs.litellm.ai/docs/completion/json_mode) - JSON mode and schema support
- [LiteLLM Ollama Structured Output Issues](https://github.com/BerriAI/litellm/issues/5172) - Known limitations with Ollama structured output
- [DuckDB Architecture and Use Cases](https://motherduck.com/duckdb-book-summary-chapter1/) - Embedded OLAP patterns
- [Building Analytics Stack with Python, Parquet, DuckDB](https://www.kdnuggets.com/building-your-modern-data-analytics-stack-with-python-parquet-and-duckdb) - DuckDB + Parquet integration patterns
- [Event Sourcing Database Architecture](https://www.redpanda.com/guides/event-stream-processing-event-sourcing-database) - Append-only event store patterns
- [Python Plugin Architecture](https://alysivji.com/simple-plugin-system.html) - Plugin registration patterns
- [Ports and Adapters in Python](https://code.likeagirl.io/ports-and-adapters-in-python-domain-driven-design-patterns-2c8c5a3171c8) - ABC adapter pattern
- [Transactional Agentic AI with LangGraph](https://www.marktechpost.com/2025/12/31/how-to-design-transactional-agentic-ai-systems-with-langgraph-using-two-phase-commit-human-interrupts-and-safe-rollbacks/) - Human interrupts and rollback patterns

---
*Architecture research for: AI-powered firewall policy management CLI (PolicyFoundry)*
*Researched: 2026-03-07*

# Technology Stack

**Project:** PolicyFoundry
**Researched:** 2026-03-07
**Overall Confidence:** HIGH

## Recommended Stack

### Core Language & Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Core language | Rich LLM ecosystem, LangChain/LangGraph native, type hint maturity. 3.12 is the sweet spot -- 3.13 works but free-threading is still beta. Pin `>=3.12,<3.14`. | HIGH |
| uv | latest | Package manager | 10-100x faster than pip/poetry. Drop-in pip replacement. Uses standard `pyproject.toml`. The 2026 default for new Python projects -- no reason to start with pip or poetry anymore. | HIGH |

### CLI Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Typer | >=0.24.1 | CLI framework | Click-based, auto-help, type-hint-driven commands. As of 0.22.0, `typer-slim` is gone -- Rich and Shellingham are mandatory dependencies, so no extra install needed. | HIGH |
| Rich | >=14.3 | Terminal formatting | Tables, panels, progress bars, Markdown rendering. Bundled with Typer. Use `rich_markup_mode="rich"` on the Typer app for help text formatting. | HIGH |

### Data Validation & Configuration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pydantic | >=2.12 | Domain models, LLM structured output | Type-safe validation, JSON Schema generation for LLM structured output, `.model_dump()` / `.model_validate()` API. V2 is required -- V1 is incompatible with Python 3.14+ and deprecated across LangChain. | HIGH |
| pydantic-settings | >=2.13 | Configuration management | YAML + env var layered config. `BaseSettings` with `yaml_file` support. Replaces hand-rolled config loading. | HIGH |

### LLM Orchestration (LangChain Ecosystem)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LangGraph | >=1.0.10 | Agentic pipeline orchestration | StateGraph for the 4-stage pipeline, checkpointing, `interrupt_before` for human-in-the-loop. v1.0 is the first stable release -- production-proven at Uber, LinkedIn, Klarna. | HIGH |
| langgraph-checkpoint-sqlite | >=3.0.3 | Pipeline state persistence | Separate package from LangGraph core. Provides `SqliteSaver` and `AsyncSqliteSaver`. Import: `from langgraph.checkpoint.sqlite import SqliteSaver`. Must be explicitly installed. | HIGH |
| LangChain | >=1.2 | Foundation: tools, prompts, structured output | `with_structured_output()` for Pydantic model binding. v1.0+ deprecated `langgraph.prebuilt` -- use `langchain.agents.create_agent` if needed, though PolicyFoundry uses custom StateGraph nodes so this is informational only. | HIGH |
| langchain-litellm | >=0.6.1 | LangChain <> LiteLLM bridge | **Use this, NOT `langchain-community` ChatLiteLLM.** The community version was deprecated in v0.3.24 with removal planned for 1.0. `langchain-litellm` is the official replacement package. Provides `ChatLiteLLM` and `ChatLiteLLMRouter`. | HIGH |
| langchain-ollama | >=1.0.1 | Direct Ollama integration | For development, use `ChatOllama` directly (faster, no proxy overhead). In production config, route through LiteLLM. `with_structured_output()` works natively via Ollama's JSON schema mode. | MEDIUM |
| langchain-aws | >=1.3.1 | AWS Bedrock integration | `ChatBedrock` for Claude on Bedrock. Needed for future cloud provider support. Not required for Phase 1 (Ollama-only), but pin it now. | HIGH |
| LangSmith | >=0.7.14 | Observability & eval | Execution traces, prompt debugging, eval datasets. Optional but strongly recommended -- set `LANGCHAIN_TRACING_V2=true`. Free tier sufficient for development. | MEDIUM |

### LLM Routing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LiteLLM | >=1.82 | Multi-provider LLM proxy/router | 100+ providers via unified OpenAI-compatible interface. Cost tracking, fallback chains, budget limits. Use as the routing layer -- individual `langchain-*` packages handle the actual model communication. For Ollama: model format is `ollama/modelname`. | HIGH |

### Storage

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| DuckDB | >=1.4.4 | Embedded columnar analytics | Multi-GB flow log analytics on a laptop. Direct Parquet file querying without ETL. v1.4.0 is LTS with AES-256 encryption. **Note: No native async support.** Use `asyncio.to_thread()` or `aioduckdb` wrapper for async contexts. | HIGH |
| PyArrow | >=23.0 | Parquet read/write | Required for Parquet file I/O. DuckDB reads Parquet natively, but PyArrow is needed for writing normalized logs. **Breaking change: >=23.0 requires Python >=3.10** (fine for our 3.12+ target). Use zstd compression. | HIGH |
| SQLite (stdlib) | built-in | State, audit, checkpoints | LangGraph `SqliteSaver` uses it. Audit event store uses it. Zero-config, embedded, ACID. Use `aiosqlite` for async access. | HIGH |

### AWS Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| boto3 | >=1.42 | AWS SDK | Security Group CRUD, VPC Flow Log S3 access, future Bedrock. Pin `>=1.42` -- releases weekly, so don't pin exact version. Uses IAM credentials from environment/config. | HIGH |

### HTTP Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| httpx | >=0.28.1 | Async HTTP client | For threat intel API calls, future Palo Alto REST adapter. Native async, HTTP/2 support. v1.0 is in dev preview but not yet stable -- stick with 0.28.x. | HIGH |

### Test Infrastructure (AWS)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Terraform (HCL) | >=1.9 | Test AWS infrastructure | VPC, Security Groups, EC2 instances, VPC Flow Logs. Use plain HCL, **NOT CDKTF** -- HashiCorp deprecated CDKTF on December 10, 2025. Repository archived, no updates. | HIGH |

**Important: Do NOT use CDKTF (Terraform CDK) or AWS CDK for this project.**

- **CDKTF:** Deprecated December 2025. Archived. Dead. Do not adopt.
- **AWS CDK:** Tempting since the project is Python, but `aws-cdk-lib` only supports Python <=3.11 (incompatible with our 3.12+ requirement). Also adds massive dependency tree (jsii, Node.js runtime) for what amounts to ~100 lines of infrastructure code.
- **Terraform HCL:** Simple, well-documented, zero Python dependency conflicts. A `infra/` directory with 3-4 `.tf` files is all that's needed for the test environment.

### Utilities

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyYAML | >=6.0 | YAML config parsing | pydantic-settings YAML support. Lightweight, battle-tested. | HIGH |
| python-dotenv | >=1.0 | .env file loading | Development convenience for env vars. Not needed in production (env vars set directly). | HIGH |
| aiosqlite | >=0.21 | Async SQLite access | Required for `AsyncSqliteSaver` in LangGraph and async audit event storage. | HIGH |

## Development Dependencies

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | >=9.0 | Test framework | Standard Python test runner. v9.0 is current stable. | HIGH |
| pytest-asyncio | >=1.3 | Async test support | Required for testing async adapter/pipeline code. Use `asyncio_mode = "auto"` in pyproject.toml. | HIGH |
| pytest-cov | >=6.0 | Coverage reporting | Standard coverage plugin. | HIGH |
| moto | >=5.1 | AWS service mocking | Mock EC2, S3, IAM for adapter tests. Use `@mock_aws` decorator or `mock_aws()` context manager. Install with `moto[ec2,s3]` extras. | HIGH |
| ruff | >=0.15 | Linting + formatting | Replaces flake8, black, isort in a single Rust-powered tool. 10-100x faster than alternatives. The 2026 standard for Python projects. | HIGH |
| mypy | >=1.14 | Type checking | Static type analysis. Critical for Pydantic model correctness. Use `--strict` mode. | HIGH |
| pre-commit | >=4.0 | Git hook management | Run ruff + mypy on commit. Catches issues before CI. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI Framework | Typer + Rich | Click (raw) | Typer IS Click with type hints. No reason to use raw Click. |
| CLI Framework | Typer + Rich | argparse | No Rich integration, verbose boilerplate, poor DX. |
| LLM Orchestration | LangGraph | CrewAI | CrewAI abstracts too much. PolicyFoundry needs fine-grained control over pipeline state, checkpointing, and tool routing. LangGraph's StateGraph is the right abstraction level. |
| LLM Orchestration | LangGraph | AutoGen | Microsoft's framework. Good for multi-agent chat but wrong paradigm for a deterministic 4-stage pipeline. |
| LLM Routing | LiteLLM | Direct provider SDKs | Vendor lock-in. LiteLLM provides unified interface + cost tracking + fallback chains. Worth the dependency. |
| LLM Routing | LiteLLM | LangChain `init_chat_model` | `init_chat_model` works for simple cases but lacks LiteLLM's budget tracking, rate limiting, and 100+ provider support. Use both: LiteLLM for routing, `langchain-litellm` for LangChain integration. |
| Data Validation | Pydantic v2 | dataclasses | No validation, no JSON Schema generation, no `with_structured_output()` support. |
| Data Validation | Pydantic v2 | attrs | Good library but no LangChain integration for structured output. Pydantic is the ecosystem standard. |
| Storage (Analytics) | DuckDB | Polars | Polars is great for DataFrames but DuckDB provides SQL interface (better for LLM tool-calling -- LLMs write SQL, not DataFrame operations). |
| Storage (Analytics) | DuckDB | SQLite | SQLite is row-oriented. Flow log analytics (aggregations, group-bys over millions of rows) need columnar storage. DuckDB is 100x+ faster for these queries. |
| Package Manager | uv | Poetry | Poetry is slower, heavier, and uses non-standard lock format. uv is the 2026 default. |
| Package Manager | uv | pip | uv is a drop-in pip replacement that's 10-100x faster. No reason to use pip for a new project. |
| Linting | ruff | flake8 + black + isort | Three tools vs one. Ruff is faster and covers all three use cases. |
| Test Infra | Terraform HCL | CDKTF | **Deprecated December 2025.** Repository archived by HashiCorp. |
| Test Infra | Terraform HCL | AWS CDK | Python support stops at 3.11 (our project requires 3.12+). Adds Node.js/jsii dependency for ~100 lines of infra code. |
| Test Infra | Terraform HCL | Pulumi | Overkill for a test environment with 4-5 resources. Terraform HCL is simpler and universally understood. |
| Agent Framework | LangGraph (custom nodes) | Deep Agents | PROJECT.md explicitly drops Deep Agents. Niche library, LangGraph sub-graphs cover the same use cases natively. |
| HTTP Client | httpx | aiohttp | httpx has cleaner API, sync+async in one library, HTTP/2 support. aiohttp is async-only and more verbose. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| Deep Agents | Dropped per PROJECT.md. Niche, unnecessary -- LangGraph sub-graphs handle sub-agent patterns. |
| CDKTF | Deprecated December 2025. Archived. No maintenance. |
| AWS CDK (Python) | Python 3.11 max. Incompatible with our 3.12+ requirement. |
| `langchain-community` ChatLiteLLM | Deprecated in v0.3.24. Use `langchain-litellm` package instead. |
| `langchain-community` ChatOllama | Deprecated. Use `langchain-ollama` (dedicated package) instead. |
| `langgraph.prebuilt` | Deprecated in LangGraph 1.0. Use `langchain.agents` if prebuilt agents are needed. PolicyFoundry uses custom nodes, so this doesn't apply. |
| Vector (log ingestion) | Original architecture plan suggested Vector for log normalization. Unnecessary for CLI -- Python parsers handle the same job without a separate Rust binary dependency. |
| Kafka | Phase 2+ cloud feature. Not needed for CLI batch processing. |
| ClickHouse | Phase 2+ cloud feature. DuckDB covers CLI analytics. |
| PostgreSQL | Phase 2+ cloud feature. SQLite covers CLI state/audit. |
| Redis | Phase 2+ cloud feature. No caching layer needed for CLI. |
| Textual (TUI) | Optional nice-to-have. Do NOT include in Phase 1 scope -- Rich terminal output is sufficient. Defer to Phase 2. |

## LLM Integration Architecture Decision

There are two viable patterns for integrating LiteLLM + Ollama with LangGraph. Use **Pattern A**.

### Pattern A: langchain-litellm as universal adapter (RECOMMENDED)

```python
from langchain_litellm import ChatLiteLLM

# All providers routed through LiteLLM
llm = ChatLiteLLM(
    model="ollama/llama3.2",          # Ollama via LiteLLM
    api_base="http://localhost:11434",
    temperature=0.1,
    max_tokens=4096,
)

# Structured output works via LiteLLM's OpenAI-compatible interface
structured_llm = llm.with_structured_output(TrafficAnalysis)
result = await structured_llm.ainvoke(messages)
```

**Why:** Single code path for all providers. Swap `ollama/llama3.2` for `bedrock/anthropic.claude-sonnet-4-20250514` with zero code changes. Cost tracking and fallback chains come free.

### Pattern B: Direct langchain-ollama for dev, LiteLLM for prod (ALTERNATIVE)

```python
# Development (faster, no proxy overhead)
from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3.2", temperature=0.1)

# Production (multi-provider routing)
from langchain_litellm import ChatLiteLLM
llm = ChatLiteLLM(model="bedrock/anthropic.claude-sonnet-4-20250514")
```

**Why not:** Two code paths. Config-driven switching adds complexity for marginal performance gain. LiteLLM's Ollama overhead is negligible for a batch CLI.

## DuckDB Async Strategy

DuckDB has no native async Python support. For PolicyFoundry's async architecture:

```python
import asyncio
import duckdb

async def query_traffic_stats(query: str) -> list[dict]:
    """Run DuckDB queries without blocking the event loop."""
    def _execute():
        conn = duckdb.connect("flow_logs.duckdb")
        return conn.execute(query).fetchdf().to_dict("records")

    return await asyncio.to_thread(_execute)
```

**Rationale:** `asyncio.to_thread()` is stdlib, zero dependencies, and sufficient for CLI batch processing where DuckDB queries are the primary bottleneck (not concurrent I/O). The `aioduckdb` package exists but is unmaintained and unnecessary for this use case.

## Installation

```bash
# Initialize project with uv
uv init policyfoundry
cd policyfoundry

# Core dependencies
uv add \
    typer>=0.24.1 \
    rich>=14.3 \
    pydantic>=2.12 \
    pydantic-settings>=2.13 \
    langgraph>=1.0.10 \
    langgraph-checkpoint-sqlite>=3.0.3 \
    langchain>=1.2 \
    langchain-litellm>=0.6.1 \
    langchain-ollama>=1.0.1 \
    langchain-aws>=1.3.1 \
    langsmith>=0.7.14 \
    litellm>=1.82 \
    duckdb>=1.4.4 \
    pyarrow>=23.0 \
    boto3>=1.42 \
    httpx>=0.28.1 \
    pyyaml>=6.0 \
    python-dotenv>=1.0 \
    aiosqlite>=0.21

# Dev dependencies
uv add --dev \
    pytest>=9.0 \
    pytest-asyncio>=1.3 \
    pytest-cov>=6.0 \
    "moto[ec2,s3]>=5.1" \
    ruff>=0.15 \
    mypy>=1.14 \
    pre-commit>=4.0
```

## pyproject.toml Reference

```toml
[project]
name = "policyfoundry"
version = "0.1.0"
requires-python = ">=3.12,<3.14"
description = "AI-powered firewall policy management CLI"
license = { text = "BSL-1.1" }

dependencies = [
    # CLI
    "typer>=0.24.1",
    "rich>=14.3",

    # Data Validation
    "pydantic>=2.12",
    "pydantic-settings>=2.13",

    # LangChain Ecosystem
    "langgraph>=1.0.10",
    "langgraph-checkpoint-sqlite>=3.0.3",
    "langchain>=1.2",
    "langchain-litellm>=0.6.1",
    "langchain-ollama>=1.0.1",
    "langchain-aws>=1.3.1",
    "langsmith>=0.7.14",

    # LLM Routing
    "litellm>=1.82",

    # Storage
    "duckdb>=1.4.4",
    "pyarrow>=23.0",
    "aiosqlite>=0.21",

    # AWS
    "boto3>=1.42",

    # HTTP
    "httpx>=0.28.1",

    # Config
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.3",
    "pytest-cov>=6.0",
    "moto[ec2,s3]>=5.1",
    "ruff>=0.15",
    "mypy>=1.14",
    "pre-commit>=4.0",
]

[project.scripts]
policyfoundry = "policyfoundry.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "TCH"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

## Version Pinning Strategy

- **Minimum version pins** (`>=X.Y`) for most dependencies -- allows patch updates.
- **No exact pins** except Python itself (`>=3.12,<3.14`).
- **Lock file** generated by `uv lock` captures exact resolved versions for reproducibility.
- **boto3**: Pin `>=1.42`, never exact -- AWS releases weekly and exact pins cause dependency hell.
- **LangChain ecosystem**: All pinned to current major version (`>=1.x`) to stay within the v1.0 stability commitment.

## Key Version Changes from Original Spec

The original `02-implementation-spec.md` has outdated versions. Here are the corrections:

| Package | Original Spec | Current Version | Notes |
|---------|--------------|-----------------|-------|
| langgraph | >=0.2 | >=1.0.10 | v1.0 GA released. Major milestone. |
| langchain | >=0.3 | >=1.2 | v1.0 GA released alongside LangGraph 1.0. |
| langchain-community | >=0.3 | **REMOVE** | ChatLiteLLM deprecated here. Use `langchain-litellm` instead. |
| deepagents | >=0.1 | **REMOVE** | Dropped per PROJECT.md decision. |
| litellm | >=1.40 | >=1.82 | Active development, fast release cycle. |
| duckdb | >=1.0 | >=1.4.4 | v1.4.0 is LTS. |
| pyarrow | >=17.0 | >=23.0 | Major version jump. Now requires Python >=3.10. |
| typer | >=0.12 | >=0.24.1 | Many releases since spec was written. |
| rich | >=13.7 | >=14.3 | Major version bump. |
| pytest | >=8.0 | >=9.0 | Major version bump. |
| pytest-asyncio | >=0.23 | >=1.3 | Major version bump to 1.x. |
| moto | >=5.0 | >=5.1.21 | Minor updates. |
| ruff | >=0.5 | >=0.15 | Significant updates. |
| textual | >=0.70 | **DEFER** | Not needed for Phase 1. |
| langchain-aws | >=0.2 | >=1.3.1 | Major version bump. |
| langsmith | >=0.1 | >=0.7.14 | Significant updates. |
| N/A | N/A | langgraph-checkpoint-sqlite>=3.0.3 | **NEW.** Separate package, must be explicitly installed. |
| N/A | N/A | langchain-litellm>=0.6.1 | **NEW.** Replaces deprecated community package. |
| N/A | N/A | langchain-ollama>=1.0.1 | **NEW.** Dedicated Ollama integration. |
| N/A | N/A | aiosqlite>=0.21 | **NEW.** Required for async SQLite access. |

## Sources

- [LangGraph PyPI](https://pypi.org/project/langgraph/) - v1.0.10 verified 2026-03-07
- [LangGraph 1.0 GA announcement](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [LangGraph v1 migration guide](https://docs.langchain.com/oss/python/migrate/langgraph-v1)
- [LangChain PyPI](https://pypi.org/project/langchain/) - v1.2.10 verified
- [langchain-litellm PyPI](https://pypi.org/project/langchain-litellm/) - v0.6.1 verified
- [langchain-ollama PyPI](https://pypi.org/project/langchain-ollama/) - v1.0.1 verified
- [langchain-aws PyPI](https://pypi.org/project/langchain-aws/) - v1.3.1 verified
- [langgraph-checkpoint-sqlite PyPI](https://pypi.org/project/langgraph-checkpoint-sqlite/) - v3.0.3 verified
- [LiteLLM PyPI](https://pypi.org/project/litellm/) - v1.82.0 verified
- [LiteLLM Ollama docs](https://docs.litellm.ai/docs/providers/ollama)
- [LiteLLM structured output docs](https://docs.litellm.ai/docs/completion/json_mode)
- [DuckDB PyPI](https://pypi.org/project/duckdb/) - v1.4.4 verified
- [DuckDB async discussion](https://github.com/duckdb/duckdb/discussions/3560)
- [PyArrow PyPI](https://pypi.org/project/pyarrow/) - v23.0.1 verified
- [Pydantic PyPI](https://pypi.org/project/pydantic/) - v2.12.5 verified
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) - v2.13.1 verified
- [Typer PyPI](https://pypi.org/project/typer/) - v0.24.1 verified
- [Rich PyPI](https://pypi.org/project/rich/) - v14.3.3 verified
- [boto3 PyPI](https://pypi.org/project/boto3/) - v1.42.63 verified
- [httpx PyPI](https://pypi.org/project/httpx/) - v0.28.1 verified
- [moto PyPI](https://pypi.org/project/moto/) - v5.1.21 verified
- [LangSmith PyPI](https://pypi.org/project/langsmith/) - v0.7.14 verified
- [pytest PyPI](https://pypi.org/project/pytest/) - v9.0.2 verified
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) - v1.3.0 verified
- [ruff PyPI](https://pypi.org/project/ruff/) - v0.15.5 verified
- [aws-cdk-lib PyPI](https://pypi.org/project/aws-cdk-lib/) - v2.241.0, Python <=3.11
- [CDKTF deprecation announcement](https://ascii.co.uk/news/article/news-20251219-002e4264/cdk-for-terraform-officially-deprecated-after-five-years)
- [LangChain structured output docs](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Ollama structured outputs blog](https://ollama.com/blog/structured-outputs)
- [Python package managers 2026 comparison](https://scopir.com/posts/best-python-package-managers-2026/)

# Feature Research

**Domain:** AI-powered firewall policy management / network security policy management (NSPM)
**Researched:** 2026-03-07
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete. Derived from what Tufin, AlgoSec, FireMon, AWS Firewall Manager, Google Cloud Firewall Insights, Prowler, and open-source AWS security tools all provide as baseline.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Flow log ingestion and normalization** | Every NSPM and traffic analysis tool ingests logs. Without this, the tool has no data to work with. Users expect pointing at S3/local files and getting parsed, queryable data. | MEDIUM | VPC Flow Logs have well-documented v2-v7 formats. Parse space-delimited text, normalize to unified schema. S3 + local file support for Phase 1. |
| **Current rule fetching and display** | AlgoSec, FireMon, Tufin all show your existing rule base. Users must see what they have before they trust suggestions to change it. | LOW | boto3 `describe_security_group_rules` is straightforward. Translate to universal schema for display. |
| **Overly permissive rule detection** | Google Cloud Firewall Insights, AWS Firewall Manager, Prowler, and every NSPM tool flags `0.0.0.0/0` and wide port ranges. This is the most basic security hygiene check. | LOW | Compare rule CIDRs and port ranges against observed traffic. Flag rules wider than actual usage. No LLM needed for basic cases. |
| **Unused rule detection** | Every enterprise NSPM tool (Tufin, FireMon, AlgoSec) and Google Cloud Firewall Insights detect rules with zero traffic hits. This is the #1 rule cleanup action. | MEDIUM | Cross-reference flow log traffic against existing rules. Rules with no matching flows in observation window are candidates. Needs flow-to-rule association logic. |
| **Rule change suggestions with justification** | This is PolicyFoundry's core value prop. Every competitor provides recommendations. What matters is the quality of justification -- PCI-DSS 4.0 requires business justification for every rule. | HIGH | 4-stage LangGraph pipeline output. Each suggestion must include: what to change, why, risk level, confidence score, and business justification text. |
| **Human-readable output (terminal)** | CLI tools live and die by output quality. Security engineers need scannable, understandable results, not raw JSON dumps. Rich tables, color-coded risk levels, clear summaries. | LOW | Typer + Rich provides panels, tables, color coding, progress bars. Essential for CLI-first product. |
| **Machine-readable output (JSON)** | CI/CD integration is expected. Security engineers need to pipe output to other tools, SIEM, or ticket systems. JSON is the universal interchange format. | LOW | Serialize Pydantic models to JSON. Straightforward. |
| **Audit trail of suggestions** | PCI-DSS 4.0 Requirement 10 mandates audit trails for all security-relevant actions. SOC 2 requires tamper-proof logs. Even suggest-only mode must log what was proposed and why. | MEDIUM | Event-sourced immutable log in SQLite. Every proposal gets an AuditEvent with full lineage (run ID, model used, confidence, reasoning). |
| **Configuration file support** | Every CLI tool supports config files. Users need to configure LLM provider, AWS credentials reference, log sources, and target security groups without passing 20 CLI flags. | LOW | YAML config at `~/.policyfoundry/config.yaml`. Pydantic Settings handles env var overrides. Well-understood pattern. |
| **Dry-run / suggest-only mode** | Users MUST be able to run the tool without any risk of changes. AWS SG `DryRun` flag exists for a reason. Suggest-only is not optional for Phase 1 -- it IS the mode. | LOW | Default and only mode in Phase 1. No `apply` functionality ships initially. Output is advisory. |
| **Multiple output formats** | Security tooling outputs to various consumers: terminals, CI/CD, SIEM, ticketing. SARIF is the standard for CI/CD security findings. | MEDIUM | JSON (done with Pydantic), SARIF (static analysis standard, used by GitHub Code Scanning), Rich terminal. SARIF adds moderate complexity but is worth it for CI/CD adoption. |

### Differentiators (Competitive Advantage)

Features that set PolicyFoundry apart. These are what make it more than "yet another security group auditor."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Traffic-to-rule AI pipeline** | The core differentiator. No existing open-source tool uses an agentic AI pipeline to go from raw VPC Flow Logs to specific, justified Security Group rule recommendations. Tufin/AlgoSec/FireMon do this with proprietary engines, but cost $50K+/year. Prowler/ScoutSuite audit configurations but don't analyze traffic patterns. PolicyFoundry bridges the gap. | HIGH | 4-stage LangGraph pipeline: Analyze traffic patterns, Assess security posture against current rules, Generate policy proposals, Decide actions. Each stage is a checkpointed node with structured Pydantic output. |
| **LLM-powered traffic pattern interpretation** | DuckDB aggregates the stats; the LLM interprets what the patterns MEAN. "Port 4443 traffic from 3 internal IPs to an external IP at 3am looks like data exfiltration" -- this contextual reasoning is impossible with rule-based tools. | HIGH | Stage 1 (Analyze) feeds pre-aggregated DuckDB statistics to the LLM. The LLM identifies clusters, anomalies, and suspicious patterns. Keeps token costs manageable by never sending raw logs. |
| **Local-first LLM (Ollama)** | Zero cloud costs, zero data leaving the network. Competitors like AlgoSec and Tufin are cloud-hosted SaaS. Security teams handling sensitive network data strongly prefer keeping it local. Ollama + LiteLLM routing means users control where their data goes. | MEDIUM | LiteLLM routes to Ollama by default. No API keys needed to get started. Trade-off: local models (Llama 3, Mistral) are less capable than Claude/GPT-4 for complex reasoning. Good enough for pattern detection; may struggle with nuanced policy generation. |
| **Pipeline checkpointing and resumability** | LangGraph SQLiteSaver checkpoints every pipeline stage. If the LLM call fails at Stage 3, resume from Stage 3 without re-running Stages 1-2. No competitor CLI offers this. Enterprise tools do, but at enterprise prices. | MEDIUM | LangGraph has native checkpointing. SQLiteSaver for CLI tier. Enables `policyfoundry replay --run-id X --from-stage assess`. Saves time and LLM costs on failures. |
| **Vendor-neutral universal rule schema** | PolicyFoundry defines rules in a universal format, then translates to vendor-specific API calls. This means the same analysis pipeline works for AWS SGs today and Palo Alto/Azure NSGs/GCP Firewall tomorrow. Tufin and AlgoSec are multi-vendor but proprietary. | MEDIUM | UniversalRule Pydantic model captures the superset of vendor capabilities. Adapter pattern translates bidirectionally. Phase 1 is AWS-only, but the schema is designed for multi-vendor from day one. |
| **Risk-scored recommendations with confidence levels** | Each suggestion includes a risk level (LOW/MEDIUM/HIGH/CRITICAL) and an AI confidence score (0.0-1.0). Security teams can filter by risk, prioritize high-confidence suggestions, and ignore low-confidence ones. No open-source tool provides calibrated confidence. | MEDIUM | Stage 4 (Decide) assigns risk levels and confidence. The LLM evaluates each proposal against organizational risk tolerance. Confidence calibration will improve with eval datasets over time. |
| **SARIF output for CI/CD integration** | SARIF (Static Analysis Results Interchange Format) is the standard for security findings in GitHub Code Scanning, Azure DevOps, and other CI/CD platforms. PolicyFoundry can run in CI/CD to flag security group drift on every pull request. No other traffic-analysis tool outputs SARIF. | MEDIUM | SARIF spec is well-documented. Map PolicyProposal to SARIF Result with rule ID, message, and severity. Enables "security-as-code" workflows where SG analysis runs alongside linting and tests. |
| **Event-sourced audit with full AI lineage** | Every suggestion records which LLM model produced it, what tokens it used, what it cost, and the full reasoning chain. This is beyond what PCI-DSS requires -- it enables trust-building with auditors who want to understand AI decision-making. | MEDIUM | AuditEvent model captures: model used, token count, cost, AI reasoning text, pipeline run ID, before/after rule state. Immutable append-only log in SQLite. |
| **Cost tracking per pipeline run** | Every LLM call records tokens in/out and estimated cost. Users see exactly what each analysis costs. Critical for local LLM users (compute time) and cloud LLM users (API costs). Budget limits prevent runaway spending. | LOW | LLMCallRecord model tracks per-call costs. Aggregate per run. LiteLLM provides cost estimation for most providers. Simple but valuable for adoption -- users hate surprise bills. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems. Deliberately NOT building these.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-apply mode in Phase 1** | "Why suggest when you can just fix it?" Security automation feels like the end goal. | Auto-applying firewall rules without established trust is reckless. One bad AI suggestion could block production traffic or open attack surfaces. Trust must be earned through suggestion accuracy. Enterprise tools (Tufin, AlgoSec) took years to reach auto-apply. PCI-DSS requires human review of changes. | Suggest-only with clear, justified recommendations. Track suggestion acceptance rate. Graduate to auto-apply only after 100+ accurate suggestions with <5% false positive rate (Phase 2+). |
| **Real-time streaming analysis** | "I want alerts the moment something bad happens." Real-time sounds better than batch. | Streaming ingestion (Kafka, ClickHouse materialized views) adds enormous complexity to a CLI tool. VPC Flow Logs have inherent 10-minute aggregation delay anyway. The ROI of sub-minute analysis is near zero for policy management (policies change weekly, not per-second). Real-time is for SIEM/NDR tools, not policy tools. | Batch analysis on-demand or via cron. Micro-batch (30-60 second poll) in Phase 2 for near-real-time monitoring. Real-time threat detection is a different product category. |
| **Web GUI / dashboard** | "CLI is for developers, security teams want dashboards." Visual representation of network topology and rule coverage. | Building a web frontend (React/Next.js) doubles the codebase and halves iteration speed. The CLI is the product for Phase 1. Enterprise NSPM tools all have GUIs, but they also have 100+ person engineering teams. A solo/small team building CLI + web simultaneously ships neither well. | Rich terminal output via Typer + Rich. Optional Textual TUI for interactive exploration. JSON/SARIF output enables third-party visualization. Web dashboard is Phase 2 after CLI is proven. |
| **Multi-cloud support in Phase 1** | "We use AWS and Azure and GCP." Multi-cloud is the reality for enterprises. | Each cloud has different firewall primitives (AWS SGs vs Azure NSGs vs GCP Firewall Rules), different APIs, different log formats, and different quirks. Supporting three clouds triples the adapter work and triples the testing surface. Prove the pipeline works perfectly on one cloud first. | AWS-only for Phase 1. Universal rule schema is designed for multi-vendor from day one. Azure NSG and GCP Firewall adapters are Phase 2 once the pipeline is proven. |
| **Threat intelligence integration in Phase 1** | "Check IPs against threat feeds." AbuseIPDB, GreyNoise, VirusTotal lookups add context. | External API dependencies add latency, rate limits, API key management, and cost. Threat intel is valuable for the Assess stage but not essential for MVP. The core value is traffic-to-rule analysis, not IP reputation. Adding threat intel before the pipeline works end-to-end is premature optimization. | Placeholder tool interface in Stage 2. Implement with free tier APIs (AbuseIPDB, GreyNoise Community) in Phase 1.x after core pipeline is working. Design the tool interface now so it can be plugged in later. |
| **Natural language query interface** | "Ask questions about your network in English." Conversational AI interface for ad-hoc queries. | LLM-powered NLQ adds a separate interaction model alongside the structured pipeline. It requires prompt engineering, context management, and handling ambiguous queries -- all orthogonal to the core analysis pipeline. It is a different product experience that dilutes focus. | Structured CLI commands with clear options. DuckDB SQL queries for power users who want ad-hoc analysis. NLQ can be a Phase 2 feature after the structured pipeline is mature. |
| **Compliance report generation (PCI-DSS, SOC 2 formal reports)** | "Generate my PCI-DSS audit report." Compliance is a pain point and automation is appealing. | Formal compliance reports require deep domain expertise in each standard, legal review, and continuous updates as standards evolve. PCI-DSS 4.0 alone has hundreds of requirements. This is a separate product (see Vanta, Drata, Secureframe). PolicyFoundry should provide DATA for compliance, not generate the reports themselves. | Audit trail data exportable in standard formats (JSON, CSV). Compliance-relevant metadata on every suggestion (business justification, risk level, change history). Integrate with compliance platforms rather than replacing them. |
| **Custom rule language / DSL** | "Let me write custom detection rules." Users want to define their own analysis patterns. | A custom DSL is a language design problem, not a security problem. It requires parser, documentation, error handling, IDE support, and ongoing maintenance. The LLM pipeline should handle pattern detection. For custom rules, users can modify prompts or add tool functions. | Configurable analysis parameters in YAML (risk thresholds, port allowlists, CIDR exemptions). User-provided security policy YAML that the LLM references during analysis. Custom LangGraph tool functions for power users. |

## Feature Dependencies

```
[Flow Log Ingestion + Normalization]
    |
    +--requires--> [DuckDB Storage + Parquet Writer]
    |                  |
    |                  +--enables--> [Traffic Query Tool]
    |                                    |
    |                                    +--feeds--> [Stage 1: Analyze Traffic]
    |                                                    |
    +--requires--> [Current Rule Fetching (boto3)]       |
                       |                                 |
                       +--feeds--> [Stage 2: Assess Security]
                                       |
                                       +--feeds--> [Stage 3: Generate Policy]
                                                       |
                                                       +--feeds--> [Stage 4: Decide]
                                                                       |
                                                                       +--produces--> [Rule Suggestions with Justification]
                                                                       |                  |
                                                                       |                  +--consumed-by--> [Output Formatters (Rich/JSON/SARIF)]
                                                                       |                  |
                                                                       |                  +--consumed-by--> [Audit Trail]
                                                                       |
                                                                       +--gated-by--> [Human-in-the-Loop Review]

[LLM Client (LiteLLM + Ollama)]
    +--used-by--> [Stage 1: Analyze]
    +--used-by--> [Stage 2: Assess]
    +--used-by--> [Stage 3: Generate]
    +--used-by--> [Stage 4: Decide]

[Configuration System (YAML + Pydantic Settings)]
    +--used-by--> [Everything]

[Pipeline Checkpointing (SQLiteSaver)]
    +--wraps--> [LangGraph StateGraph]
    +--enables--> [Pipeline Resumability]

[Overly Permissive Detection] --requires--> [Current Rule Fetching] + [Flow Log Ingestion]
[Unused Rule Detection] --requires--> [Current Rule Fetching] + [Flow Log Ingestion] + [DuckDB Storage]
```

### Dependency Notes

- **Stage 1 (Analyze) requires DuckDB storage:** The LLM receives pre-aggregated statistics, not raw logs. DuckDB must be populated before analysis can begin.
- **Stage 2 (Assess) requires current rules:** Cannot assess security posture without knowing what rules exist. The firewall adapter must fetch and translate current rules before this stage runs.
- **Output formatters require pipeline completion:** SARIF/JSON/Rich output consumes the final pipeline state. Partial results are possible with checkpointing but full output needs all stages.
- **Audit trail requires pipeline metadata:** AuditEvent records reference pipeline run ID, LLM model, token counts. These come from pipeline execution, not standalone.
- **Unused rule detection requires both rule data AND flow log data:** This is a cross-reference operation. Cannot be done with rules alone or logs alone.
- **Human-in-the-loop gate conflicts with auto-apply:** Phase 1 has only human review. Auto-apply (Phase 2+) replaces the gate for low-risk changes but coexists for high-risk ones.

## MVP Definition

### Launch With (v1.0)

Minimum viable product -- what is needed to validate that AI-powered traffic-to-rule analysis works and is useful.

- [ ] **VPC Flow Log ingestion from S3 and local files** -- without data, nothing works
- [ ] **Normalization to unified 10-field schema** -- foundation for all analysis
- [ ] **DuckDB storage and Parquet persistence** -- enables fast analytical queries on multi-GB datasets
- [ ] **AWS Security Group rule fetching via boto3** -- must know current state to suggest changes
- [ ] **LLM client via LiteLLM with Ollama support** -- zero-cost local inference for development and privacy-conscious users
- [ ] **4-stage LangGraph pipeline (Analyze, Assess, Generate, Decide)** -- the core AI value proposition
- [ ] **Structured Pydantic output from every LLM call** -- type-safe, parseable, no free-text fragility
- [ ] **Pipeline checkpointing via SQLiteSaver** -- resume from failure without re-running expensive LLM calls
- [ ] **Rich terminal output with risk-colored tables** -- CLI-first product must have beautiful output
- [ ] **JSON output** -- machine-readable for integration
- [ ] **YAML configuration system** -- don't force 20 CLI flags on every invocation
- [ ] **Immutable audit log in SQLite** -- compliance readiness from day one
- [ ] **Suggest-only mode (no apply capability)** -- safety-first, build trust before automation

### Add After Validation (v1.x)

Features to add once the core pipeline is proven accurate and useful.

- [ ] **SARIF output for CI/CD integration** -- trigger: users ask to run PolicyFoundry in GitHub Actions
- [ ] **Threat intelligence tool (AbuseIPDB/GreyNoise free tier)** -- trigger: users want IP reputation context in assessments
- [ ] **Overly permissive rule detection as standalone command** -- trigger: users want quick SG audit without full pipeline
- [ ] **Unused rule detection as standalone command** -- trigger: users want cleanup recommendations without AI analysis
- [ ] **LLM cost tracking and budget limits** -- trigger: users move from Ollama to cloud LLM providers
- [ ] **Human-in-the-loop approval gate via LangGraph interrupt** -- trigger: users want to approve/reject individual suggestions interactively
- [ ] **Pipeline replay from checkpoint** -- trigger: users want to re-run from a specific stage after adjusting config
- [ ] **Cloud LLM support (AWS Bedrock Claude, OpenAI)** -- trigger: users want higher-quality analysis than local models provide

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Auto-apply mode with graduated autonomy** -- why defer: trust must be earned through suggestion accuracy; requires safety mechanisms (circuit breaker, kill switch, emergency revert)
- [ ] **Web dashboard with network topology visualization** -- why defer: doubles codebase; CLI must be proven first
- [ ] **Multi-cloud adapters (Azure NSG, GCP Firewall Rules)** -- why defer: each adapter is significant work; prove on AWS first
- [ ] **Palo Alto Cloud NGFW adapter** -- why defer: different API model, two-phase commit complexity
- [ ] **Compliance report generation (PCI-DSS, SOC 2)** -- why defer: deep domain expertise needed; better to integrate with compliance platforms
- [ ] **Team collaboration, RBAC, SSO** -- why defer: enterprise features for when there are enterprise customers
- [ ] **Micro-batch / near-real-time monitoring** -- why defer: batch analysis is sufficient for policy management cadence
- [ ] **Natural language query interface** -- why defer: different interaction model; dilutes focus on structured pipeline

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Flow log ingestion + normalization | HIGH | MEDIUM | P1 |
| DuckDB storage + Parquet | HIGH | MEDIUM | P1 |
| AWS SG rule fetching | HIGH | LOW | P1 |
| LiteLLM + Ollama LLM client | HIGH | MEDIUM | P1 |
| 4-stage LangGraph AI pipeline | HIGH | HIGH | P1 |
| Structured Pydantic LLM output | HIGH | MEDIUM | P1 |
| Pipeline checkpointing (SQLiteSaver) | MEDIUM | LOW | P1 |
| Rich terminal output | HIGH | LOW | P1 |
| JSON output | HIGH | LOW | P1 |
| YAML config system | MEDIUM | LOW | P1 |
| Immutable audit log | MEDIUM | MEDIUM | P1 |
| Suggest-only mode | HIGH | LOW | P1 |
| SARIF output | MEDIUM | MEDIUM | P2 |
| Threat intelligence tool | MEDIUM | MEDIUM | P2 |
| Overly permissive rule detection (standalone) | MEDIUM | LOW | P2 |
| Unused rule detection (standalone) | MEDIUM | MEDIUM | P2 |
| LLM cost tracking | LOW | LOW | P2 |
| Human-in-the-loop approval gate | MEDIUM | MEDIUM | P2 |
| Pipeline replay | LOW | LOW | P2 |
| Cloud LLM providers | MEDIUM | LOW | P2 |
| Auto-apply mode | HIGH | HIGH | P3 |
| Web dashboard | HIGH | HIGH | P3 |
| Multi-cloud adapters | HIGH | HIGH | P3 |
| Compliance reports | MEDIUM | HIGH | P3 |
| RBAC / SSO / team features | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch -- without these, the product does not deliver its core promise
- P2: Should have, add after core pipeline is proven -- these increase adoption and utility
- P3: Nice to have, future consideration -- these are Phase 2+ or enterprise tier features

## Competitor Feature Analysis

| Feature | Tufin / AlgoSec / FireMon | AWS Firewall Manager | Google Cloud Firewall Insights | Prowler / ScoutSuite | PolicyFoundry |
|---------|---------------------------|---------------------|-------------------------------|---------------------|---------------|
| Traffic-to-rule analysis | Yes (proprietary engines) | No (compliance only) | Yes (ML-based, GCP only) | No (config audit only) | Yes (LLM-powered, open source) |
| Overly permissive detection | Yes | Yes (content audit policies) | Yes (ML-powered) | Yes (basic CIS checks) | Yes (traffic-based, AI-enhanced) |
| Unused rule detection | Yes (hit count analysis) | No | Yes (ML predictions) | No | Yes (flow log cross-reference) |
| Rule change suggestions | Yes (with workflow) | No (flag only) | Yes (narrower ranges) | No | Yes (with business justification) |
| Compliance reporting | Yes (PCI-DSS, SOC 2, etc.) | Partial (compliance status) | No | Yes (CIS, NIST, PCI) | Phase 2 (audit data export) |
| Multi-vendor support | Yes (100+ vendors) | AWS only | GCP only | Multi-cloud | AWS Phase 1, multi-vendor later |
| Auto-apply rules | Yes (with approval workflow) | Yes (auto-remediation) | No | No | Phase 2+ (graduated autonomy) |
| CI/CD integration | Limited | CloudFormation hooks | No | JSON/CSV output | SARIF output for GitHub/Azure DevOps |
| Local / self-hosted | On-prem option ($$$) | N/A (AWS service) | N/A (GCP service) | Yes (CLI tool) | Yes (CLI + Ollama, zero cloud cost) |
| AI/LLM powered | AlgoSec AI bot (2025) | No | ML for predictions | No | Core architecture (agentic pipeline) |
| Audit trail | Yes (enterprise grade) | AWS CloudTrail | Stackdriver | Report generation | Event-sourced immutable log |
| Pricing | $50K-200K+/year | Per-policy pricing | Per-insight pricing | Free (open source) | Free CLI (open-core BSL 1.1) |
| Risk scoring | Yes | Limited | No | Severity levels | Yes (per-recommendation, calibrated) |

### Key Competitive Insights

1. **The gap PolicyFoundry fills:** No open-source tool combines traffic analysis with AI-powered rule recommendation. Prowler/ScoutSuite audit configurations but don't analyze traffic. AWS Firewall Manager flags compliance issues but doesn't suggest specific rule changes based on traffic patterns. The enterprise NSPM tools (Tufin, AlgoSec, FireMon) do this but cost $50K+/year.

2. **Google Cloud Firewall Insights is the closest analog:** It analyzes traffic patterns to recommend narrower IP/port ranges and uses ML to predict future rule usage. But it is GCP-only, cloud-native (no self-hosting), and does not use LLMs for contextual reasoning.

3. **Skybox Security shut down in February 2025:** This left a gap in the NSPM market. Organizations migrating from Skybox need alternatives, and PolicyFoundry could capture the "self-hosted, cost-effective" segment.

4. **AlgoSec and Tufin added AI features in 2025:** Both introduced AI-powered bots and automated optimization. The market is moving toward AI-assisted policy management, validating PolicyFoundry's approach.

5. **Prowler and ScoutSuite are the open-source competition:** They audit AWS configurations against CIS/NIST/PCI benchmarks. PolicyFoundry differentiates by analyzing actual traffic patterns, not just static configurations.

## Sources

- [FireMon vs AlgoSec vs Tufin comparison](https://www.firemon.com/firemon-vs-algosec-vs-tufin/) -- Feature comparison of major NSPM vendors
- [Top Network Security Policy Management Solutions (AIMultiple)](https://aimultiple.com/network-security-policy-management-solutions) -- NSPM feature categories and market overview
- [AWS Firewall Manager features](https://aws.amazon.com/firewall-manager/features/) -- AWS native SG management capabilities
- [Google Cloud Firewall Insights overview](https://docs.google.com/cloud/network-intelligence-center/docs/firewall-insights/concepts/overview) -- ML-powered rule recommendations on GCP
- [Improve Security Groups using VPC Flow Logs (cloudonaut)](https://cloudonaut.io/improve-security-groups-using-vpc-flow-logs-aws-config/) -- Traffic-based SG recommendation methodology
- [PCI-DSS 4.0 firewall requirements (FwChange)](https://fwchange.com/blog/pci-dss-firewall-compliance) -- Compliance requirements for firewall changes
- [PCI-DSS 4.0 requirements guide (Linford)](https://linfordco.com/blog/pci-dss-4-0-requirements-guide/) -- Mandatory audit trail requirements
- [Skybox Security shutdown (Xcitium)](https://www.xcitium.com/blog/news/what-is-skybox/) -- Skybox operations ceased February 2025
- [NSPM comparison (FortMatrix)](https://sudhir.is-a.dev/posts/NSPM_Comparison/) -- Independent comparison of AlgoSec, Tufin, FireMon
- [Prowler open source security tool](https://github.com/JasonTeixeira/Prowler) -- CIS/NIST/PCI compliance auditing CLI
- [VPC Flow Logs documentation (AWS)](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html) -- Official log format reference
- [AWS-SG-Analyzer (GitHub)](https://github.com/SherifTalaat/AWS-SG-Analyzer) -- Open source SG analysis tool
- [flowlogs-reader (GitHub)](https://github.com/obsrvbl-oss/flowlogs-reader) -- CLI tool for VPC Flow Log reading

---
*Feature research for: AI-powered firewall policy management (PolicyFoundry)*
*Researched: 2026-03-07*

# Pitfalls Research

**Domain:** AI-powered firewall policy management (LLM pipeline analyzing VPC Flow Logs, suggesting AWS Security Group changes)
**Researched:** 2026-03-07
**Confidence:** HIGH (critical pitfalls verified against official docs and multiple sources)

## Critical Pitfalls

### Pitfall 1: LLM Hallucination Producing Overly Permissive Rules (0.0.0.0/0)

**What goes wrong:**
The LLM generates a Security Group rule recommendation with source CIDR `0.0.0.0/0` (or the IPv6 equivalent `::/0`), effectively opening a port to the entire internet. Worse, LLMs can hallucinate *split CIDR blocks* like `0.0.0.0/1` + `128.0.0.0/1` that together cover the full IPv4 space but dodge naive string-matching checks against `0.0.0.0/0`. The model presents these with high confidence and plausible business justifications, making them easy to rubber-stamp during human review.

**Why it happens:**
LLMs optimize for plausible, helpful responses -- not security correctness. When traffic patterns show legitimate connections from diverse sources, the model may generalize to a broad CIDR instead of enumerating specific ranges. Training data contains countless tutorials and Stack Overflow answers with `0.0.0.0/0` examples. The model has no understanding of blast radius.

**How to avoid:**
- Implement a **deterministic post-LLM validation layer** (not another LLM call) that rejects rules with:
  - Source/destination CIDR broader than a configurable threshold (e.g., /16 or wider)
  - Any CIDR that when combined with other proposed rules covers the full address space
  - Port ranges wider than necessary (e.g., 0-65535)
  - Protocol "any" (-1) without explicit user override
- Include an `ai_confidence` field on every rule; require human review for any rule below a configurable threshold
- Put maximum-permissiveness checks in the `rule_validator_tool` so the LLM's own Generate stage gets feedback before Decide
- Never allow `0.0.0.0/0` inbound without a CLI `--allow-public` flag that the user must explicitly pass

**Warning signs:**
- LLM generates rules with /0, /1, /2 CIDR blocks
- Generated rules consistently use wider CIDRs than the traffic data justifies
- Justification text says "for convenience" or "to ensure connectivity"
- Rules reference port ranges like 0-65535 or protocol -1

**Phase to address:**
Phase 1 (pipeline foundation). The deterministic validator must ship before any rule suggestion is ever shown to a user. This is the single most important safety mechanism in the entire system.

---

### Pitfall 2: Structured Output Parsing Failures with Ollama Local Models

**What goes wrong:**
Ollama models (especially smaller ones like 7B-13B) fail to produce valid JSON conforming to the Pydantic schema, causing `ValidationError` exceptions that crash the pipeline. Failures include: incomplete JSON (model stops mid-output without closing braces), extra commentary mixed into JSON, missing required fields, wrong data types (string instead of enum), and hallucinated field names. LiteLLM's integration with Ollama's `ollama_chat` endpoint has known issues where it does not return JSON-compatible structured output or follow tool-call formatting required by structured output frameworks.

**Why it happens:**
Ollama enforces JSON grammar at the token level but does not validate the full response against the schema. If the model hits its token limit mid-JSON, you get truncated output. Smaller models (7B) have weaker instruction-following ability for complex schemas. LiteLLM adds an abstraction layer that may not correctly pass `response_format` or `format: json` parameters to all Ollama backend versions. The `with_structured_output()` method in LangChain has model-specific behavior -- what works with OpenAI may silently fail with Ollama via LiteLLM.

**How to avoid:**
- Use `langchain_ollama.ChatOllama` directly for Ollama instead of routing through LiteLLM for local development. Use LiteLLM only for cloud providers (Bedrock, OpenAI)
- Set `temperature: 0` for all security analysis calls to maximize schema adherence
- Implement a **retry-with-repair loop**: on `ValidationError`, feed the error message back to the LLM with the original prompt and ask it to fix the output (LangChain's `RetryOutputParser` pattern)
- Keep Pydantic schemas as flat as possible -- avoid deeply nested models in LLM-facing schemas. Use separate simpler schemas for LLM output, then map to your internal domain models
- Set `max_tokens` high enough that the model never truncates mid-JSON (monitor actual token usage vs. limit)
- Test every schema against your chosen Ollama model before integrating into the pipeline. Models like `qwen2.5:32b` and `llama3.1:70b` are significantly more reliable at structured output than 7B variants
- Pin Ollama model versions in config to prevent a model update from breaking parsing

**Warning signs:**
- `ValidationError` exceptions in pipeline logs
- Retry counts climbing above 2 per LLM call
- JSON responses with trailing natural language after the closing brace
- Different success rates between models for the same prompt

**Phase to address:**
Phase 1 (LLM integration). Must be validated in the first sprint where LLM calls are implemented. Create a test harness that runs every pipeline schema against the target Ollama model 50+ times to measure reliability.

---

### Pitfall 3: AWS Security Group Allow-Only Model vs. Universal Rule Schema DENY Actions

**What goes wrong:**
The LLM generates a `DENY` or `DROP` rule (because the traffic analysis shows malicious activity that should be blocked), the universal rule schema accepts it, but the AWS SG adapter cannot apply it -- Security Groups are allow-only. The pipeline either crashes with an unhandled error, silently drops the rule, or (worst case) translates it into an ALLOW rule by accident due to a translation bug.

**Why it happens:**
The universal rule schema (`UniversalRule.action`) supports ALLOW, DENY, DROP, and REJECT to accommodate multi-vendor scenarios (Palo Alto supports all). Developers build and test the pipeline end-to-end assuming the schema is the truth, forgetting that AWS SGs only support ALLOW. The LLM has no inherent knowledge of adapter capabilities and will recommend blocking malicious IPs -- a reasonable suggestion that happens to be impossible with SGs alone.

**How to avoid:**
- The Generate stage prompt **must** include adapter capabilities as context: "The target firewall only supports ALLOW rules. Do not generate DENY rules. To restrict traffic, recommend removing or tightening existing ALLOW rules."
- The `rule_validator_tool` must check `AdapterCapabilities.supports_deny_rules` and reject DENY/DROP/REJECT actions for AWS SG targets before the rule ever reaches the Decide stage
- Include adapter capability awareness in the pipeline state so every node knows what the target can do
- When the analysis identifies traffic to block, generate a separate "advisory" output suggesting NACLs (which do support deny) rather than trying to express it as an SG rule
- Add a translator-level assertion: `if action != ALLOW: raise UnsupportedRuleAction`

**Warning signs:**
- LLM generates "block IP X.X.X.X" rules for AWS SG targets
- Translation layer has if/else branches for action types it cannot actually translate
- Test suite only tests ALLOW rules against the AWS adapter

**Phase to address:**
Phase 1 (adapter implementation). The adapter capability system and prompt injection of capabilities must be built at the same time as the AWS SG adapter. Test with scenarios where traffic analysis clearly shows malicious activity to verify the pipeline handles it correctly.

---

### Pitfall 4: AWS Security Group 60-Rule Limit Exhaustion

**What goes wrong:**
The LLM generates 15 new rules for a Security Group that already has 50 inbound rules. The first 10 apply successfully. Rule 11 fails with `RulesPerSecurityGroupLimitExceeded`. The system is now in a partial-apply state: some rules applied, others did not, and the SG is in an inconsistent state relative to the pipeline's intent.

**Why it happens:**
AWS SGs default to 60 inbound + 60 outbound rules per group. The limit is not per-rule but per-CIDR-entry (a rule with 3 CIDRs counts as 3 toward the quota). Prefix list references count as the prefix list's max size, not its current size. Developers test with small rule sets and never hit the limit. The LLM has no awareness of remaining capacity.

**How to avoid:**
- Before the Generate stage, query current rule count and calculate remaining capacity. Pass `remaining_capacity: N` into the LLM prompt
- Implement a **pre-flight check** in the adapter: count existing rules + proposed rules and fail fast if the total would exceed the limit, before applying anything
- Use **atomic batching**: either all rules in a batch apply or none do. Since AWS SG API does not support transactions, implement this by: (1) dry-run all rules first, (2) track applied rules, (3) on failure, rollback all previously applied rules in the batch
- Consider rule consolidation: the LLM should merge overlapping CIDRs where possible (e.g., 10.0.1.0/24 + 10.0.2.0/24 on the same port could become 10.0.0.0/22)
- Surface the formula: `rules_per_SG * SGs_per_ENI <= 1000` total per network interface. Increasing rules per SG may require reducing SGs per ENI

**Warning signs:**
- SG rule count approaching 50 (83% of default limit)
- LLM generating many fine-grained rules instead of consolidated ones
- No pre-flight capacity check in the adapter
- Partial apply errors in audit log

**Phase to address:**
Phase 1 (adapter implementation). The pre-flight check must be part of the adapter's `validate_rule` and `dry_run` methods from day one. Rule consolidation is a Phase 2 optimization but the capacity check is not optional.

---

### Pitfall 5: LangGraph Checkpoint State Bloat from Flow Log Data

**What goes wrong:**
The `PipelineState` TypedDict stores `flow_logs: list[NormalizedFlowLog]` directly in state. LangGraph checkpoints save the full state at every node transition. With 100K flow logs at ~200 bytes each, that is ~20MB per checkpoint, times 5 nodes = 100MB per pipeline run. After 100 runs, the SQLite checkpoint database is 10GB. The CLI becomes slow to start, `replay` commands take minutes, and disk space on developer machines runs out.

**Why it happens:**
LangGraph stores a complete snapshot of state at every checkpoint by default. This is by design for time-travel debugging but catastrophic when state contains large datasets. Developers put flow logs in state for convenience during prototyping and never refactor.

**How to avoid:**
- **Never store raw flow logs in LangGraph state.** Store them in Parquet/DuckDB and pass only a reference (file path or query ID) in pipeline state
- Store only aggregated/summarized data in state (top talkers, port distributions, anomaly scores) -- the data the LLM actually needs
- Use state field `flow_log_ref: str` (path to Parquet file) instead of `flow_logs: list[NormalizedFlowLog]`
- Configure checkpoint TTL to auto-expire old checkpoints (LangGraph supports this)
- Consider `exit` durability mode if intermediate checkpoints are not needed for debugging -- this writes only at run completion

**Warning signs:**
- SQLite state database growing faster than 1MB per pipeline run
- `replay` command taking more than 5 seconds to load state
- `PipelineState` TypedDict containing any `list[...]` field with potentially unbounded size

**Phase to address:**
Phase 1 (pipeline state design). This must be decided in the architecture phase before any node is implemented. Changing state shape later requires migrating all existing checkpoints.

---

### Pitfall 6: AsyncSqliteSaver Hanging on Sync/Async Mismatch

**What goes wrong:**
The CLI uses `asyncio.run()` at the entrypoint and `AsyncSqliteSaver` for LangGraph checkpointing. But somewhere in the codebase, a synchronous method like `graph.invoke()` or `graph.get_state()` is called instead of `await graph.ainvoke()`. The program hangs indefinitely with no error message. This is extremely difficult to debug because there is no exception, no timeout, and no indication of what went wrong.

**Why it happens:**
LangGraph provides both sync and async APIs. The sync `SqliteSaver` and async `AsyncSqliteSaver` are separate classes that must match the invocation style. Developers switch between sync and async during development, or copy-paste examples that use `graph.invoke()` instead of `await graph.ainvoke()`. The `aiosqlite` library has also had breaking changes (v0.22.0 removed Thread inheritance) that cause `AttributeError` on `is_alive`.

**How to avoid:**
- Use synchronous `SqliteSaver` for the CLI tier. The CLI runs a single pipeline at a time; async checkpointing provides no benefit and adds this hanging risk. Use `asyncio.run()` only at the entrypoint, and let LangGraph's sync API handle the graph execution
- If async is required: create a strict rule that ALL graph interactions use async methods. Add a linting rule or wrapper that prevents calling `.invoke()`, `.get_state()`, `.get_state_history()` on async-checkpointed graphs
- Pin `aiosqlite` version in pyproject.toml to avoid breaking changes
- Add a 60-second timeout wrapper around all graph invocations so hangs become errors instead of infinite waits

**Warning signs:**
- CLI hangs after "Starting pipeline..." with no output
- Mix of `graph.invoke()` and `await graph.ainvoke()` calls in codebase
- `aiosqlite` version unpinned or recently updated
- No timeout on graph execution

**Phase to address:**
Phase 1 (pipeline orchestration). Decide sync vs. async for the checkpointer in the first implementation sprint. Recommendation: use sync `SqliteSaver` for CLI.

---

### Pitfall 7: VPC Flow Logs Data Gaps Leading to Wrong Security Conclusions

**What goes wrong:**
The LLM analyzes traffic patterns from VPC Flow Logs and concludes "no traffic on port 443 from subnet X" -- so it recommends removing the ALLOW rule for that traffic. In reality, the flow logs have gaps: SKIPDATA records indicate dropped log entries, the aggregation interval was 10 minutes so short-lived connections may not appear, and version 2 logs do not include flow direction or AWS service fields, making it impossible to distinguish load balancer traffic from direct traffic.

**Why it happens:**
VPC Flow Logs are **not** a complete packet capture. AWS explicitly documents that records may be skipped due to internal capacity constraints (log-status: SKIPDATA). Default aggregation is 10 minutes. Version 2 logs show only interface-local IPs, so traffic forwarded by a load balancer shows the LB's IP, not the original source. Developers treat flow logs as ground truth when they are best-effort samples.

**How to avoid:**
- Parse and surface the `log-status` field. Count SKIPDATA records per time window and include this in the LLM's analysis context: "Warning: 3% of records were skipped in this window. Conclusions about absent traffic are unreliable."
- Set the aggregation interval to 1 minute (Nitro instances do this automatically) in the test infrastructure Terraform
- Use version 5+ flow logs to get `flow-direction`, `pkt-srcaddr`, `pkt-dstaddr`, and `pkt-src-aws-service` fields. The parser must handle version differences gracefully
- Never recommend REMOVING an existing rule based solely on the absence of matching traffic. Require a configurable minimum observation window (e.g., 30 days) before considering traffic "absent"
- Include a `data_completeness_score` in the `TrafficAnalysis` output that the Assess and Generate stages use to temper their confidence

**Warning signs:**
- SKIPDATA records in flow logs being silently discarded during parsing
- Parser only handling version 2 fields
- LLM recommending rule removal after analyzing less than 7 days of data
- No data completeness metric in traffic analysis output

**Phase to address:**
Phase 1 (ingestion layer). The parser must handle SKIPDATA and version detection from the first implementation. The minimum observation window should be a configurable safety parameter.

---

### Pitfall 8: boto3 Is Not Async -- Blocking the Event Loop

**What goes wrong:**
The project constraint says "All I/O operations must be async/await." The adapter interface declares `async def get_rules()`, `async def apply_rule()`, etc. But boto3 is synchronous -- it does blocking HTTP calls. Wrapping a sync boto3 call in an `async def` does NOT make it non-blocking; it blocks the entire asyncio event loop, freezing the CLI during AWS API calls and preventing concurrent operations.

**Why it happens:**
boto3 does not support asyncio and has no plans to until a major rewrite. Developers see `async def` in the adapter interface, use `await self.client.describe_security_groups()`, and it "works" because Python allows calling sync code from async functions -- but the event loop is blocked. This is invisible in a CLI that makes one API call at a time but becomes a correctness issue if any concurrent operations are added.

**How to avoid:**
- Wrap boto3 calls in `asyncio.loop.run_in_executor(None, sync_function)` to run them in a thread pool. This is the recommended pattern for using synchronous libraries in async code
- Alternatively, use `aioboto3` (drop-in async replacement for boto3) which provides true async AWS API calls
- Document clearly that the boto3 client methods are sync wrappers and must always go through the executor
- Do NOT declare boto3 wrapper methods as `async def` without the executor pattern -- this is misleading

**Warning signs:**
- `async def` methods that directly call boto3 without `run_in_executor`
- CLI freezing during AWS API calls (no Rich spinner/progress updates)
- Import of `boto3` without `aioboto3` or `run_in_executor` pattern nearby

**Phase to address:**
Phase 1 (adapter implementation). Decide between `aioboto3` and `run_in_executor` pattern before writing the first adapter method.

---

### Pitfall 9: AWS Security Group Eventual Consistency Race Conditions

**What goes wrong:**
The pipeline reads current rules (`describe_security_group_rules`), generates recommendations, and applies a new rule. Then it reads rules again to verify -- but the new rule is not yet visible due to eventual consistency. The pipeline concludes the apply failed and either retries (creating a duplicate) or reports an error. Alternatively: the pipeline creates an SG and immediately tries to add rules, but the SG does not exist yet in the API's view.

**Why it happens:**
The EC2 API is eventually consistent. `authorize_security_group_ingress` returns success before the change is propagated to all API endpoints. Subsequent `describe` calls may not reflect the change for several seconds. This is documented AWS behavior, not a bug.

**How to avoid:**
- After any mutating API call, implement a **poll-with-backoff** verification: retry `describe` with exponential backoff (1s, 2s, 4s) until the expected rule appears, up to a configurable timeout
- Separate the "apply" and "verify" steps in the audit log. Log "APPLIED (pending verification)" then "VERIFIED" as separate events
- For the suggest-only Phase 1, this is low risk since no rules are actually applied. But the verification pattern must be built into the adapter from the start for Phase 2+
- Consider using `DryRun=True` before actual apply to catch permission errors without triggering consistency issues

**Warning signs:**
- Intermittent "rule not found" errors after successful apply calls
- Duplicate rules appearing in Security Groups
- Tests passing locally but failing in CI (timing-dependent)

**Phase to address:**
Phase 2 (auto-apply). In Phase 1 suggest-only mode, the read path (fetching current rules) is the primary concern and has lower consistency risk. The full verification pattern is needed when apply is implemented.

---

### Pitfall 10: Audit Trail Gaps -- Events Without Full LLM Lineage

**What goes wrong:**
The audit log records that a rule was proposed and the final rule spec, but does not capture: which LLM model version produced it, what prompt was sent, what traffic data the LLM saw, what the LLM's raw response was before Pydantic parsing, or which previous pipeline stages influenced the decision. When an auditor asks "why did the AI recommend opening port 8080?" the team cannot reconstruct the reasoning chain.

**Why it happens:**
The `AuditEvent` schema has `llm_model_used` and `ai_reasoning` fields, which seems sufficient. But `ai_reasoning` is a summary generated by the LLM itself (which can hallucinate its own reasoning). The actual prompt, the DuckDB query results that fed the analysis, and the intermediate stage outputs are only in LangGraph checkpoints -- which may have been garbage-collected, or may not include the full LLM request/response.

**How to avoid:**
- Store the full prompt and raw LLM response for every LLM call that contributes to a rule decision. Use LangSmith traces for development, but for production audit compliance, store these locally in the SQLite audit database (not dependent on a third-party SaaS)
- Include a `pipeline_run_id` + `stage_name` + `checkpoint_id` reference in every audit event so the full state can be reconstructed from checkpoints
- Add `input_data_hash` to audit events -- a hash of the traffic data that was analyzed -- so you can verify the analysis was based on a specific dataset
- Set checkpoint TTL to at least match audit retention (1 year for PCI-DSS compliance)
- Write audit events synchronously and treat write failures as pipeline failures -- never silently drop audit records

**Warning signs:**
- Audit events with `ai_reasoning: ""` or generic boilerplate
- No way to map an audit event back to the specific LLM call that produced it
- Checkpoint TTL shorter than audit retention requirement
- LangSmith as the only trace storage (external dependency for compliance data)

**Phase to address:**
Phase 1 (audit system). The audit event schema and write path must be implemented alongside the first pipeline node. Retrofitting audit lineage after the pipeline is built always results in gaps.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing flow logs directly in LangGraph state | Simpler state management, no external storage needed | Checkpoint bloat, 10x storage costs, slow replays | Never -- use Parquet file references from day one |
| Using string-based LLM output parsing instead of `with_structured_output` | Works with any model, no tool-calling support needed | Fragile regex parsing, breaks on model updates, no type safety | Never for this project -- Pydantic structured output is a core requirement |
| Hardcoding prompt templates instead of loading from files | Faster iteration in early development | Cannot A/B test prompts, version history lost, cannot swap per-model | Only for first prototype sprint; externalize by week 3 |
| Single SQLite file for checkpoints + audit + state | One fewer dependency, simpler config | Audit data mixed with expendable checkpoint data; cannot set different retention policies | Only in MVP if clear migration path exists to separate DBs |
| Skipping the DryRun step for AWS SG rule application | Faster apply, fewer API calls | No pre-validation of IAM permissions, rule limits hit at apply time | Never -- DryRun is free and catches errors early |
| Using synchronous SqliteSaver instead of async | Simpler code, no hanging bugs, easier debugging | Cannot run concurrent pipelines (irrelevant for CLI v1) | Acceptable for CLI tier; switch to PostgresSaver for cloud tier |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Ollama via LiteLLM | Assuming `with_structured_output()` works identically to OpenAI -- it does not; LiteLLM may not pass JSON format correctly to Ollama | Use `langchain_ollama.ChatOllama` directly for local Ollama. Use LiteLLM only for cloud providers |
| AWS SG via boto3 | Declaring adapter methods `async def` but calling sync boto3 directly, blocking the event loop | Use `run_in_executor()` or `aioboto3` for all boto3 calls within async contexts |
| AWS SG rule application | Not handling `InvalidPermission.Duplicate` error when the same rule already exists | Check for existing rules before apply; handle duplicate gracefully as a no-op with warning |
| DuckDB + Parquet | Loading entire Parquet file into memory for a filtered query | Use DuckDB's Parquet reader with `WHERE` clauses to leverage columnar predicate pushdown |
| LangGraph SQLiteSaver | Not setting `check_same_thread=False` or mixing sync/async invocation styles | SqliteSaver handles this internally with a lock; stick to one invocation style (sync or async) consistently |
| VPC Flow Logs from S3 | Assuming all log files use the same field format and ordering | Parse the header/version field first; handle version 2-5+ differences; do not assume field positions |
| LangSmith tracing | Enabling tracing in production without considering that prompts and responses contain customer network data | Make LangSmith optional; provide local-only audit logging; warn users about data sent to LangSmith |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all flow logs into Python memory before writing to Parquet | Works fine with 10K records; OOM at 1M+ | Use streaming ingestion: async generator yields batches, writer flushes to Parquet incrementally | >500K records per ingestion (~100MB raw) |
| DuckDB `SELECT *` on Parquet without column pruning | Queries complete slowly, high memory usage | Select only needed columns; DuckDB reads only referenced columns from Parquet | >1GB Parquet file, or queries on high-cardinality columns |
| Sending raw DuckDB query results (full table) to the LLM | Token limit exceeded, high latency, high cost | Pre-aggregate in DuckDB (top-N, group-by summaries); send statistics, not rows | >100 result rows from any traffic query |
| Single-threaded boto3 calls when fetching rules from multiple SGs | Each API call takes 200-500ms; 10 SGs = 5 seconds of blocking | Batch with ThreadPoolExecutor or use aioboto3 for concurrent fetches | >5 Security Groups in a single analysis |
| SQLite checkpoint database without WAL mode | Write contention if audit writer and checkpoint writer overlap | Enable WAL mode on SQLite: `PRAGMA journal_mode=WAL` | Concurrent pipeline runs or audit writes during pipeline execution |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| LLM recommending rules based on hallucinated traffic patterns not present in the data | False sense of security; rules that don't address actual traffic | Cross-validate every LLM traffic claim against DuckDB queries; add a verification node that spot-checks LLM assertions |
| Storing AWS credentials in config YAML instead of env vars | Credentials committed to git, leaked in logs | Use env var references only (`api_key_env: PALO_API_KEY`); add pre-commit hook to scan for credential patterns |
| Not restricting which IAM actions the CLI's role can perform | If the CLI is compromised, attacker gets full SG modification access | Create a minimal IAM policy: `ec2:DescribeSecurityGroup*`, `ec2:AuthorizeSecurityGroup*`, `ec2:RevokeSecurityGroup*` only on specific SGs |
| Audit log stored in user-writable SQLite without integrity checks | Malicious user (or bug) modifies audit history to cover tracks | Append-only table design with hash-chain integrity (each event includes hash of previous event); consider write-ahead checksum |
| LLM prompt injection via crafted flow log data | Attacker crafts traffic that creates flow log entries containing prompt injection strings | Sanitize all data fed to LLM prompts; treat flow log data as untrusted input; use separate system/user prompt boundaries |
| Suggesting temporary "break-glass" rules without expiration enforcement | Emergency rules with 0.0.0.0/0 stay forever after the incident | All rules with `expires_at` must have a background job or CLI reminder to verify expiration; surface stale temporary rules prominently |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing all rule recommendations in a flat list without risk grouping | User overwhelmed by 30 suggestions; misses the 2 critical ones | Group by risk level (CRITICAL first), show summary counts, let user drill into categories |
| Requiring AWS credentials to run any CLI command including `--help` | User cannot explore the tool without AWS setup; terrible onboarding | Lazy-load AWS connections only when commands actually need them; include a `demo` mode with sample data |
| No progress feedback during LLM inference (Ollama can take 30-60s per call) | User thinks CLI is frozen; kills the process | Rich progress spinner showing: current stage, elapsed time, model name, token count streaming |
| Showing raw Pydantic model dumps as output | User sees `{'risk_level': 'high', 'ai_confidence': 0.72}` -- meaningless to security engineers | Use Rich tables, color-coded risk levels, plain-English justifications, and show the proposed AWS CLI equivalent command |
| Error messages exposing internal stack traces | User sees `pydantic.ValidationError` traceback instead of actionable guidance | Catch known error types; show "LLM returned invalid output for stage Analyze. Retrying (2/3)..." instead of traceback |
| No `--dry-run` mode for the overall CLI | User cannot preview what the tool will do before it accesses AWS | Add `--dry-run` that runs the pipeline with sample/cached data and shows what would happen without any AWS API calls |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Flow log parser:** Often missing handling for SKIPDATA/NODATA log-status values -- verify parser surfaces data completeness metrics
- [ ] **AWS SG adapter:** Often missing handling for `InvalidPermission.Duplicate` errors -- verify idempotent apply behavior
- [ ] **AWS SG adapter:** Often missing prefix list rule counting -- verify rules referencing prefix lists count as max_size toward quota, not as 1
- [ ] **LLM structured output:** Often missing retry-on-parse-failure logic -- verify pipeline retries with error feedback, not just re-sends the same prompt
- [ ] **Audit trail:** Often missing the full prompt text and raw LLM response -- verify every audit event can reconstruct the complete decision chain
- [ ] **Checkpoint storage:** Often missing TTL configuration -- verify old checkpoints are cleaned up automatically
- [ ] **Human-in-the-loop gate:** Often missing resume-after-restart capability -- verify that if the CLI exits while waiting for approval, the pipeline can resume from the checkpoint
- [ ] **Pipeline state:** Often missing error accumulation -- verify that a failure in stage 2 does not lose stage 1 results; errors append, do not overwrite
- [ ] **Config system:** Often missing validation of Ollama model availability -- verify the CLI checks that the configured Ollama model is actually pulled/available before starting a pipeline run
- [ ] **Rule translation:** Often missing IPv6 support -- verify AWS SG adapter handles `Ipv6Ranges` in addition to `IpRanges`

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Overly permissive rule applied to SG | MEDIUM | 1. Immediately revoke the rule using rollback handle from audit log 2. Review audit trail to identify which pipeline run caused it 3. Add the specific CIDR pattern to the validator blocklist 4. Re-run pipeline with corrected validation |
| Checkpoint database corrupted | LOW | 1. Delete the SQLite checkpoint file 2. Re-run the pipeline from scratch (all data is in Parquet/DuckDB) 3. Audit events are in a separate table/file and unaffected |
| LLM model update breaks structured output | MEDIUM | 1. Pin model version in config and revert to last known working version 2. Run the schema test harness against the new model version 3. Adjust prompts or simplify schemas if needed 4. Only upgrade model after test harness passes |
| 60-rule limit hit during batch apply | HIGH | 1. Rollback all partially-applied rules from the current batch 2. Consolidate existing rules (merge overlapping CIDRs) to free capacity 3. Request AWS quota increase if consolidation is insufficient 4. Re-run pipeline with capacity-aware generation |
| AsyncSqliteSaver hanging | LOW | 1. Kill the process (it will not recover on its own) 2. Switch to sync SqliteSaver 3. Pipeline resumes from last checkpoint automatically |
| Audit log gaps discovered during compliance review | HIGH | 1. Cross-reference LangSmith traces (if enabled) with audit events to identify gaps 2. Reconstruct missing events from checkpoint history 3. Implement the hash-chain integrity check to detect future gaps 4. Document the gap in the compliance report |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| LLM hallucinating overly permissive rules | Phase 1 -- deterministic validator | Unit tests with intentionally overly-permissive LLM outputs; validator must reject 100% of 0.0.0.0/0 rules |
| Structured output parsing failures | Phase 1 -- LLM integration | Schema reliability test harness: 50 runs per schema, >95% parse success rate required |
| Allow-only SG model vs DENY rules | Phase 1 -- adapter capability system | Integration test: generate rules for malicious traffic against AWS SG target; verify no DENY rules reach apply |
| 60-rule limit exhaustion | Phase 1 -- adapter pre-flight checks | Test: attempt to add rules to a nearly-full SG; verify graceful failure with clear error |
| Checkpoint state bloat | Phase 1 -- pipeline state design | Measure: checkpoint size must be <1MB per node transition; reject state designs that store raw logs |
| Async/sync mismatch hanging | Phase 1 -- pipeline orchestration | Verify: no `graph.invoke()` calls exist in codebase when using async checkpointer; or use sync checkpointer |
| VPC Flow Log data gaps | Phase 1 -- ingestion layer | Verify: parser surfaces SKIPDATA count; data_completeness_score appears in TrafficAnalysis output |
| boto3 blocking event loop | Phase 1 -- adapter implementation | Verify: all boto3 calls wrapped in executor; or aioboto3 used; Rich spinner runs during API calls |
| Eventual consistency race conditions | Phase 2 -- auto-apply | Integration test: apply rule then immediately verify; confirm poll-with-backoff handles delay |
| Audit trail gaps | Phase 1 -- audit system | Verify: every LLM call in a pipeline run has a corresponding audit record with prompt hash and response hash |

## Sources

- [AWS VPC Flow Log Records](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html) -- official documentation on versions, fields, SKIPDATA, aggregation intervals
- [AWS Security Group Rules](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html) -- official documentation on rule limits and counting
- [AWS Security Group Quota Optimization](https://repost.aws/articles/AR_rIppDrsRvKFHzb8LTjs3Q/optimizing-security-groups-in-aws-managing-growth-and-quota-constraints) -- rule counting formula, ENI limits, prefix list counting
- [LangGraph Interrupts Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) -- official docs on interrupt_before, deterministic ordering, resume mechanics
- [LangGraph Persistence Guide](https://fast.io/resources/langgraph-persistence/) -- checkpoint bloat, TTL, durability modes
- [LangGraph State Management Best Practices](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025/) -- reducer patterns, state schema design
- [AsyncSqliteSaver Hanging Issue](https://github.com/langchain-ai/langgraph/issues/1800) -- sync/async mismatch causing infinite hang
- [LiteLLM Structured Output Bug with Ollama](https://github.com/BerriAI/litellm/issues/10616) -- ollama_chat endpoint not returning structured output
- [LangChain Structured Output with Ollama TypeError](https://github.com/langchain-ai/langchain/issues/34107) -- version-specific parsing failures
- [Ollama Structured Outputs Documentation](https://docs.ollama.com/capabilities/structured-outputs) -- grammar enforcement, truncation risk, validation limitations
- [Ollama Structured Output Issues](https://www.glukhov.org/post/2025/10/ollama-gpt-oss-structured-output-issues/) -- model-specific failures, reasoning trace interference
- [boto3 Async Discussion](https://github.com/boto/boto3/discussions/3531) -- confirmed no native async support planned
- [EC2 API Eventual Consistency](https://www.cloudavail.com/blog/2014/07/18/eventual-consistency-ec2-api/) -- documented consistency behavior
- [boto3-post-conditions for Eventual Consistency](https://github.com/jeking3/boto3-post-conditions) -- workaround patterns
- [DuckDB Memory Management](https://duckdb.org/2024/07/09/memory-management) -- streaming execution, when memory spikes occur
- [DuckDB High Memory with Parquet](https://github.com/duckdb/duckdb/issues/17262) -- 4GB RAM for 120MB Parquet file
- [Hidden Risks of AI-Driven Firewall Policy Management](https://www.titania.com/about-us/news/hidden-risks-of-ai-driven-firewall-policy-management) -- lack of contextual awareness, operationally flawed rules
- [LLM Security Risks 2026](https://sombrainc.com/blog/llm-security-risks-2026) -- hallucination in production systems
- [OWASP LLM Top 10 2025](https://deepstrike.io/blog/owasp-llm-top-10-vulnerabilities-2025) -- LLM-specific vulnerability patterns
- [Event Sourcing Pitfalls](https://dzone.com/articles/event-sourcing-guide-when-to-use-avoid-pitfalls) -- schema versioning, GDPR, replay complexity
- [Event Sourcing with SQLite](https://www.sqliteforum.com/p/building-event-sourcing-systems-with) -- append-only design patterns

---
*Pitfalls research for: AI-powered firewall policy management (PolicyFoundry)*
*Researched: 2026-03-07*