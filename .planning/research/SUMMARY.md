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
