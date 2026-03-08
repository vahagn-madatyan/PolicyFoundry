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
