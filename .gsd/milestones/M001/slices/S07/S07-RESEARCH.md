# Phase 7: Pipeline Core - Research

**Researched:** 2026-03-11
**Domain:** LangGraph StateGraph pipeline with async LLM stages, Instructor structured output
**Confidence:** HIGH

## Summary

Phase 7 wires the 4-stage AI pipeline (Analyze, Assess, Generate Policy, Decide) using LangGraph's StateGraph with the project's existing TypedDict-based PipelineState. All stage functions are async, calling `LLMClient.complete()` from Phase 6 for structured Pydantic output. The pipeline consumes DuckDB pre-aggregated stats (Phase 4) and adapter rules/capabilities (Phase 5) as inputs, producing justified rule recommendations.

LangGraph 1.1.0 is the current stable release. It requires `langchain-core` as a transitive dependency (14 new packages total). The StateGraph API supports TypedDict state, async node functions, and a `context_schema` mechanism for injecting runtime dependencies (LLMClient, FirewallAdapter) without polluting graph state. Nodes return partial dict updates that merge into state -- this matches the existing `PipelineState(total=False)` design perfectly.

The pipeline is a simple linear graph (START -> analyze -> assess -> generate -> validate -> decide -> END) with no branching or conditional edges. Adapter validation between Generate and Decide is a non-LLM step that filters proposals. Error handling follows the CONTEXT.md decision: on stage failure, stop the pipeline and return partial results from completed stages.

**Primary recommendation:** Use LangGraph 1.1.0 StateGraph with `context_schema` dataclass for dependency injection, async node functions returning partial dict updates, and try/except within a runner function to capture partial state on failure.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use all 4 DuckDB named queries as input: top_talkers(20), denied_flows(), traffic_by_protocol(), traffic_summary()
- Top 20 talkers and all denied flow groups -- comprehensive coverage
- Format query results as structured JSON (serialize Pydantic models to JSON) in LLM prompt
- LLM interprets pre-aggregated stats, never sees raw flow log records
- Pass full rules list from adapter.get_rules() to Assess stage -- SGs max out at 60 rules
- Balanced grouping stance: LLM decides CIDR grouping with adapter capabilities in prompt
- Denied traffic with consistent patterns flagged as ALLOW rule candidates
- Every proposal must include impact_analysis -- required field
- Cap at 20 proposals per pipeline run
- Run adapter.validate() on each proposal after Generate produces them
- Invalid proposals removed before Decide stage
- Process all proposals in a single LLM call for Decide -- cross-proposal reasoning
- Three actions: CREATE, UPDATE, SKIP
- Each decision includes risk_level and approval_required flag
- On stage failure: stop pipeline, return partial results plus clear error
- Empty/sparse data: pipeline adapts -- no minimum data requirements
- No checkpointing for v1 -- all stages run in-memory via PipelineState TypedDict
- Pydantic-only validation on LLM output -- no additional semantic checks

### Claude's Discretion
- LangGraph StateGraph wiring details (edges, conditional routing if any)
- System prompt content and structure for each stage
- Temperature tuning per stage (via LLMClient.complete temperature override)
- How partial results are structured on stage failure
- Stage function signatures and internal implementation
- Test fixture design for mocking LLM responses in pipeline tests

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | User can run a 4-stage LangGraph AI pipeline: Analyze -> Assess -> Generate Policy -> Decide | LangGraph 1.1.0 StateGraph with linear edges, async ainvoke, context_schema for dependency injection |
| PIPE-02 | Stage 1 (Analyze) interprets pre-aggregated traffic statistics to identify patterns, anomalies, and top talkers | DuckDB queries (top_talkers, denied_flows, traffic_by_protocol, traffic_summary) serialized to JSON in system prompt; TrafficAnalysis response model |
| PIPE-03 | Stage 2 (Assess) compares traffic patterns against current SG rules to identify gaps and risk | adapter.get_rules() output + TrafficAnalysis from Stage 1 in prompt; SecurityAssessment response model |
| PIPE-04 | Stage 3 (Generate) produces vendor-neutral rule proposals with business justification and impact analysis | adapter.capabilities() injected in prompt; PolicyProposal response model with impact_analysis; capped at 20 proposals |
| PIPE-05 | Stage 4 (Decide) assigns risk levels and determines CREATE/UPDATE/SKIP for each proposal | All validated proposals in single LLM call; RuleDecision response model with risk_level + approval_required |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langgraph | 1.1.0 | StateGraph pipeline orchestration | Project decision; provides typed state graph, async execution, compile-time validation |
| instructor | 1.14.5 (installed) | Structured LLM output via Pydantic | Already in use via LLMClient; all stages use response_model parameter |
| litellm | 1.82.1 (installed) | LLM provider abstraction | Already in use; handles Ollama/OpenAI routing |
| pydantic | 2.12.5 (installed) | Response models and validation | Already in use; TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision defined |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langchain-core | 1.2.18 | Transitive dependency of langgraph | Pulled in automatically; not used directly in pipeline code |
| langgraph-checkpoint | 4.0.1 | Transitive dependency of langgraph | Pulled in automatically; not used in v1 (no checkpointing) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph StateGraph | Plain async functions chained manually | Loses compile-time graph validation, state management, future checkpointing path |
| context_schema (dataclass) | config["configurable"] dict | config["configurable"] works but is stringly-typed; context_schema gives type safety |
| Runtime[Context] in nodes | Closures capturing dependencies | Closures couple factory and node definitions; context_schema is cleaner for testing |

**Installation:**
```bash
uv add langgraph>=1.1.0
```

This pulls in 14 new packages including langchain-core (transitive). No conflicts with existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
src/policyfoundry/pipeline/
  __init__.py          # Export run_pipeline, PipelineResult
  llm.py               # LLMClient (existing, Phase 6)
  schema.py            # Response models (existing, Phase 1)
  state.py             # PipelineState TypedDict (existing, Phase 1)
  graph.py             # StateGraph definition, compile, build_pipeline()
  runner.py            # run_pipeline() async entry point with error handling
  stages/
    __init__.py
    analyze.py         # Stage 1: analyze_stage(state, runtime) -> dict
    assess.py          # Stage 2: assess_stage(state, runtime) -> dict
    generate.py        # Stage 3: generate_stage(state, runtime) -> dict
    validate.py        # Adapter validation step (not LLM, between Generate and Decide)
    decide.py          # Stage 4: decide_stage(state, runtime) -> dict
  prompts/
    __init__.py
    analyze.py         # ANALYZE_SYSTEM_PROMPT, format_analyze_user_message()
    assess.py          # ASSESS_SYSTEM_PROMPT, format_assess_user_message()
    generate.py        # GENERATE_SYSTEM_PROMPT, format_generate_user_message()
    decide.py          # DECIDE_SYSTEM_PROMPT, format_decide_user_message()
```

### Pattern 1: Context Schema for Dependency Injection
**What:** Define a dataclass with LLMClient, FirewallAdapter, and config as fields. Pass to graph at invocation time via `context=` parameter.
**When to use:** Always -- avoids putting non-serializable objects in state, keeps state purely data.
**Example:**
```python
# Source: LangGraph docs (context_schema pattern)
from dataclasses import dataclass
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.pipeline.llm import LLMClient

@dataclass
class PipelineContext:
    llm_client: LLMClient
    adapter: FirewallAdapter
    data_dir: str

async def analyze_stage(
    state: PipelineState, runtime: Runtime[PipelineContext]
) -> dict:  # type: ignore[type-arg]
    llm = runtime.context.llm_client
    data_dir = runtime.context.data_dir
    # ... call DuckDB queries, format prompt, call llm.complete()
    return {"analysis": result.model_dump(), "current_stage": "analyze"}

builder = StateGraph(PipelineState, context_schema=PipelineContext)
builder.add_node("analyze", analyze_stage)
# ... add more nodes and edges
graph = builder.compile()

# At invocation:
result = await graph.ainvoke(
    initial_state,
    context=PipelineContext(llm_client=client, adapter=adapter, data_dir="/data"),
)
```

### Pattern 2: Linear Graph with No Conditional Edges
**What:** Simple START -> A -> B -> C -> D -> E -> END chain. Each node runs sequentially.
**When to use:** When pipeline stages are strictly sequential with no branching logic.
**Example:**
```python
# Source: LangGraph docs (linear graph)
from langgraph.graph import StateGraph, START, END

builder = StateGraph(PipelineState, context_schema=PipelineContext)
builder.add_node("analyze", analyze_stage)
builder.add_node("assess", assess_stage)
builder.add_node("generate", generate_stage)
builder.add_node("validate", validate_proposals)  # Non-LLM step
builder.add_node("decide", decide_stage)

builder.add_edge(START, "analyze")
builder.add_edge("analyze", "assess")
builder.add_edge("assess", "generate")
builder.add_edge("generate", "validate")
builder.add_edge("validate", "decide")
builder.add_edge("decide", END)

pipeline = builder.compile()
```

### Pattern 3: Stage Functions Return Partial Dict Updates
**What:** Each node returns only the fields it modifies, not the full state. LangGraph merges these into state automatically.
**When to use:** Always with TypedDict state. This is the standard LangGraph pattern.
**Example:**
```python
async def analyze_stage(
    state: PipelineState, runtime: Runtime[PipelineContext]
) -> dict:  # type: ignore[type-arg]
    # ... perform analysis ...
    return {
        "analysis": traffic_analysis.model_dump(),
        "current_stage": "analyze",
    }
    # Only "analysis" and "current_stage" are updated in state
```

### Pattern 4: Prompt Formatting Separated from Stage Logic
**What:** Each stage has a corresponding prompts module with the system prompt constant and a user message formatting function.
**When to use:** Always -- keeps prompt engineering separate from pipeline logic, enables prompt iteration without touching stage code.
**Example:**
```python
# prompts/analyze.py
ANALYZE_SYSTEM_PROMPT = """You are a network traffic analyst..."""

def format_analyze_user_message(
    summary: TrafficSummary,
    top_talkers: list[TopTalkerResult],
    denied_flows: list[DeniedFlowResult],
    protocol_breakdown: list[TrafficByProtocolResult],
) -> str:
    return json.dumps({
        "traffic_summary": summary.model_dump(),
        "top_talkers": [t.model_dump() for t in top_talkers],
        "denied_flows": [d.model_dump() for d in denied_flows],
        "protocol_breakdown": [p.model_dump() for p in protocol_breakdown],
    }, indent=2)

# stages/analyze.py
async def analyze_stage(state, runtime):
    ctx = runtime.context
    summary = await traffic_summary(ctx.data_dir)
    talkers = await top_talkers(20, ctx.data_dir)
    denied = await denied_flows(ctx.data_dir)
    protocols = await traffic_by_protocol(ctx.data_dir)

    messages = [
        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
        {"role": "user", "content": format_analyze_user_message(
            summary, talkers, denied, protocols
        )},
    ]
    result = await ctx.llm_client.complete(messages, TrafficAnalysis, temperature=0.1)
    return {"analysis": result.model_dump(), "current_stage": "analyze"}
```

### Pattern 5: Non-LLM Validation Node
**What:** The adapter validation step between Generate and Decide is a regular async function (no LLM call). It filters proposals through adapter.validate().
**When to use:** When a pipeline step is deterministic, not LLM-based.
**Example:**
```python
async def validate_proposals(
    state: PipelineState, runtime: Runtime[PipelineContext]
) -> dict:  # type: ignore[type-arg]
    adapter = runtime.context.adapter
    proposals = state.get("proposals", [])
    current_rules = await adapter.get_rules()
    current_count = len(current_rules)

    valid_proposals = []
    for proposal_dict in proposals:
        proposal = PolicyProposal.model_validate(proposal_dict)
        result = await adapter.validate(
            proposal.rule, current_rule_count=current_count
        )
        if result.valid:
            valid_proposals.append(proposal_dict)
        # Invalid proposals silently dropped (saves tokens in Decide)

    return {"proposals": valid_proposals, "current_stage": "validate"}
```

### Pattern 6: Pipeline Runner with Partial Result Capture
**What:** A top-level `run_pipeline()` function handles error recovery by catching PipelineError and returning whatever state was accumulated before the failure.
**When to use:** Matches the CONTEXT.md decision for pipeline resilience.
**Example:**
```python
from policyfoundry.exceptions import PipelineError

async def run_pipeline(
    llm_client: LLMClient,
    adapter: FirewallAdapter,
    data_dir: str,
    sg_ids: list[str],
) -> PipelineState:
    context = PipelineContext(
        llm_client=llm_client, adapter=adapter, data_dir=data_dir
    )
    initial_state: PipelineState = {
        "run_id": str(uuid.uuid4()),
        "started_at": datetime.now(tz=UTC).isoformat(),
        "current_stage": "starting",
        "flow_log_path": data_dir,
        "sg_ids": sg_ids,
    }
    try:
        return await pipeline.ainvoke(initial_state, context=context)
    except PipelineError:
        raise  # Re-raise with partial state info in details
    except Exception as exc:
        raise PipelineError(
            f"Pipeline failed at stage: {initial_state.get('current_stage', 'unknown')}",
            error_code="PIPELINE_STAGE_FAILED",
            details={"stage": initial_state.get("current_stage", "unknown"),
                      "error": str(exc)},
        ) from exc
```

### Anti-Patterns to Avoid
- **Putting LLMClient in PipelineState:** Non-serializable objects must not go in TypedDict state. Use context_schema instead.
- **Returning full state from nodes:** Always return only the modified fields as a dict. LangGraph handles merging.
- **Embedding prompts inline in stage functions:** Prompts are the most frequently iterated artifact. Keep them in separate modules.
- **Using conditional edges for this linear pipeline:** The 4-stage pipeline has no branching. Conditional edges add complexity without benefit.
- **Catching and swallowing LLM errors in stages:** Let PipelineError propagate from LLMClient up to the runner. The runner handles partial results.
- **Using Annotated reducers on PipelineState fields:** The pipeline writes each field once (not appending). Default overwrite behavior is correct.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph orchestration | Custom async stage chaining with state passing | LangGraph StateGraph | Compile-time graph validation, built-in state management, future checkpointing path |
| Structured LLM output | Manual JSON parsing + Pydantic validation | Instructor via LLMClient.complete() | Automatic retry-with-repair on validation failures, schema in prompt generation |
| Dependency injection to stages | Global singletons or closure factories | LangGraph context_schema + Runtime | Type-safe, testable, no global state |
| Adapter constraint checking | Custom rule validator | adapter.validate() from Phase 5 | Already implements all AWS SG constraints, collects all errors |
| Prompt templating | Jinja2 or f-string template engine | Simple Python functions with json.dumps | Prompts are structured JSON data, not natural language templates; json.dumps is sufficient |

**Key insight:** The project already has LLMClient, PipelineState, response models, DuckDB queries, and adapter ABC fully implemented. Phase 7 is purely wiring -- connecting existing building blocks through LangGraph orchestration and writing the prompts.

## Common Pitfalls

### Pitfall 1: LangGraph State TypedDict with total=False and Runtime
**What goes wrong:** LangGraph expects state keys to exist when nodes access them. With `total=False`, accessing `state["analysis"]` in the Assess stage before Analyze has run raises KeyError.
**Why it happens:** TypedDict total=False makes all fields optional at the type level, but dict access still requires the key to exist at runtime.
**How to avoid:** Use `state.get("analysis")` or ensure the linear graph order guarantees each field is populated before the next stage reads it. The linear edge order (analyze -> assess -> generate -> validate -> decide) ensures this naturally.
**Warning signs:** KeyError in stage functions during testing.

### Pitfall 2: Serialization of Pydantic Models in State
**What goes wrong:** Storing Pydantic model instances directly in PipelineState (TypedDict). LangGraph may attempt to serialize state for checkpointing or debugging.
**Why it happens:** PipelineState fields are typed as `dict` and `list[dict]`, but developers might forget to call `.model_dump()`.
**How to avoid:** Always call `.model_dump()` on Pydantic results before putting them in state. When reading from state, use `Model.model_validate(state["field"])` to reconstruct.
**Warning signs:** Serialization errors, type mismatches in downstream stages.

### Pitfall 3: LLM Token Budget for Single-Call Decide
**What goes wrong:** Passing 20 proposals to a single Decide LLM call exceeds token limits, especially with Ollama and smaller models.
**Why it happens:** Each PolicyProposal includes a nested UniversalRule, justification, and impact_analysis -- substantial text.
**How to avoid:** Keep proposals capped at 20 (CONTEXT.md decision). In the Decide prompt, summarize proposals to essential fields (proposal_id, rule name, justification summary, risk_level) rather than passing full proposal JSON.
**Warning signs:** LLM timeout errors or truncated responses in Decide stage.

### Pitfall 4: Pyright Strict Mode with LangGraph
**What goes wrong:** LangGraph's `Runtime`, `StateGraph`, and related types may not have complete type stubs, causing pyright strict errors.
**Why it happens:** LangGraph depends on langchain-core which uses dynamic typing extensively.
**How to avoid:** Use targeted `# type: ignore[...]` comments consistent with project patterns (Phase 06 precedent: `# type: ignore[reportUnknownVariableType]`). Add a comment explaining the ignore.
**Warning signs:** pyright errors on imports from langgraph modules.

### Pitfall 5: Adapter Validation Current Rule Count
**What goes wrong:** Passing 0 as current_rule_count to adapter.validate() when the actual SG has rules, causing the rule limit check to be ineffective.
**Why it happens:** Forgetting to fetch current rules before validation.
**How to avoid:** In the validate_proposals step, call `adapter.get_rules()` to get current count, then pass `current_rule_count=len(current_rules)` to each validate call.
**Warning signs:** Invalid proposals passing validation that should have been caught.

### Pitfall 6: Empty Data Handling in Analyze Stage
**What goes wrong:** All DuckDB queries return empty results (no Parquet files), and the LLM receives an empty data prompt.
**Why it happens:** Pipeline run before ingestion, or data directory is wrong.
**How to avoid:** CONTEXT.md says "no minimum data requirements -- run with whatever is available." The Analyze prompt should handle empty inputs gracefully, instructing the LLM to report "no data available" rather than hallucinating patterns.
**Warning signs:** LLM hallucinating traffic patterns from empty data.

## Code Examples

Verified patterns from official sources and project codebase:

### LangGraph StateGraph Definition (Linear Pipeline)
```python
# Source: LangGraph 1.1.0 docs + project PipelineState
from dataclasses import dataclass
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.pipeline.llm import LLMClient
from policyfoundry.pipeline.state import PipelineState


@dataclass
class PipelineContext:
    """Runtime dependencies injected into pipeline stages."""
    llm_client: LLMClient
    adapter: FirewallAdapter
    data_dir: str


def build_pipeline() -> StateGraph:  # type: ignore[type-arg]
    """Build and compile the 4-stage pipeline graph."""
    builder = StateGraph(PipelineState, context_schema=PipelineContext)

    builder.add_node("analyze", analyze_stage)
    builder.add_node("assess", assess_stage)
    builder.add_node("generate", generate_stage)
    builder.add_node("validate", validate_proposals)
    builder.add_node("decide", decide_stage)

    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "assess")
    builder.add_edge("assess", "generate")
    builder.add_edge("generate", "validate")
    builder.add_edge("validate", "decide")
    builder.add_edge("decide", END)

    return builder.compile()
```

### Async Stage Function Signature
```python
# Source: LangGraph docs (async node with Runtime)
from policyfoundry.pipeline.schema import TrafficAnalysis
from policyfoundry.pipeline.state import PipelineState
from policyfoundry.pipeline.prompts.analyze import (
    ANALYZE_SYSTEM_PROMPT,
    format_analyze_user_message,
)
from policyfoundry.storage.queries import (
    denied_flows,
    top_talkers,
    traffic_by_protocol,
    traffic_summary,
)


async def analyze_stage(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:  # type: ignore[type-arg]
    """Stage 1: Analyze traffic patterns from DuckDB pre-aggregated stats."""
    ctx = runtime.context
    data_dir = ctx.data_dir

    # Gather all 4 DuckDB query results
    summary = await traffic_summary(data_dir)
    talkers = await top_talkers(20, data_dir)
    denied = await denied_flows(data_dir)
    protocols = await traffic_by_protocol(data_dir)

    # Format as structured JSON in prompt
    user_message = format_analyze_user_message(
        summary, talkers, denied, protocols
    )
    messages = [
        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # LLM call with structured output
    analysis = await ctx.llm_client.complete(
        messages, TrafficAnalysis, temperature=0.1
    )

    return {
        "analysis": analysis.model_dump(),
        "current_stage": "analyze",
    }
```

### LLMClient.complete() Call Pattern (Already Exists)
```python
# Source: pipeline/llm.py (Phase 6)
# All stages use the same pattern:
result = await llm_client.complete(
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ],
    response_model=TrafficAnalysis,  # Pydantic model class
    temperature=0.1,  # Optional per-call override
)
# result is a validated Pydantic instance
```

### Adapter Capabilities in Prompt
```python
# Source: adapters/schema.py AdapterCapabilities + adapter.capabilities()
capabilities = adapter.capabilities()
# AdapterCapabilities(
#     name="aws_sg", vendor="AWS",
#     supports_deny_rules=False,
#     max_rules_per_direction=60,
#     supports_l7_app_filtering=False,
#     allows_all_outbound_default=True,
# )
caps_json = capabilities.model_dump()
# Inject into Stage 3 (Generate) prompt as context
```

### Test Fixture Pattern for Mocking LLM Responses
```python
# Source: tests/test_pipeline/conftest.py (established pattern)
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mock LLMClient that returns pre-built Pydantic objects."""
    client = MagicMock(spec=LLMClient)
    client.complete = AsyncMock()
    return client

@pytest.fixture
def mock_adapter() -> MagicMock:
    """Mock FirewallAdapter for pipeline tests."""
    adapter = MagicMock(spec=FirewallAdapter)
    adapter.get_rules = AsyncMock(return_value=[])
    adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
    adapter.capabilities = MagicMock(return_value=AdapterCapabilities(
        name="aws_sg", vendor="AWS",
        supports_deny_rules=False,
        max_rules_per_direction=60,
    ))
    return adapter
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| config["configurable"] for passing deps | context_schema + Runtime[Context] | LangGraph v0.6.0 (2025) | Type-safe dependency injection, no stringly-typed dict access |
| config_schema parameter on StateGraph | context_schema parameter | LangGraph v0.6.0 (deprecated config_schema) | Must use context_schema, not config_schema |
| LangGraph 0.x | LangGraph 1.1.0 | October 2025 (1.0), March 2026 (1.1) | Stable API, version="v2" streaming, production-ready |
| Pydantic v1 in langchain | Pydantic v2 native | 2024 | Project already uses Pydantic v2 throughout |

**Deprecated/outdated:**
- `config_schema` parameter on StateGraph: deprecated in v0.6.0, use `context_schema` instead
- `MessageGraph`: deprecated, use `StateGraph` with `MessagesState` if needed (not needed for this pipeline)

## Open Questions

1. **Pyright compatibility with LangGraph types**
   - What we know: LangGraph depends on langchain-core which uses dynamic typing; the project uses pyright strict mode on src/
   - What's unclear: Exact set of type: ignore comments needed for LangGraph imports and Runtime usage
   - Recommendation: Follow Phase 06 precedent -- use targeted type: ignore with explanatory comments. Test during implementation.

2. **context_schema with non-serializable objects**
   - What we know: context_schema is designed for "static context like user_id, db_conn" per LangGraph docs. LLMClient and FirewallAdapter are non-serializable.
   - What's unclear: Whether LangGraph attempts to serialize context in any code path (logging, debugging)
   - Recommendation: Use context_schema as documented. If serialization issues arise, fall back to config["configurable"] pattern. LOW risk given this is the documented use case.

3. **Temperature tuning per stage**
   - What we know: LLMClient.complete() accepts optional temperature override. Lower temperature for Analyze/Assess (precision), slightly higher for Generate (creativity).
   - What's unclear: Optimal temperature values per stage for Ollama llama3.2
   - Recommendation: Start with 0.1 for Analyze/Assess/Decide, 0.3 for Generate. These are tunable without code changes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ with pytest-asyncio 1.3.0+ |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_pipeline/ -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Full pipeline runs 4 stages in order | integration | `uv run pytest tests/test_pipeline/test_graph.py::TestPipelineExecution -x` | Wave 0 |
| PIPE-02 | Analyze stage produces TrafficAnalysis from DuckDB stats | unit | `uv run pytest tests/test_pipeline/test_stages.py::TestAnalyzeStage -x` | Wave 0 |
| PIPE-03 | Assess stage compares patterns to SG rules, finds gaps | unit | `uv run pytest tests/test_pipeline/test_stages.py::TestAssessStage -x` | Wave 0 |
| PIPE-04 | Generate stage produces vendor-neutral proposals with impact_analysis | unit | `uv run pytest tests/test_pipeline/test_stages.py::TestGenerateStage -x` | Wave 0 |
| PIPE-05 | Decide stage assigns risk levels and CREATE/UPDATE/SKIP actions | unit | `uv run pytest tests/test_pipeline/test_stages.py::TestDecideStage -x` | Wave 0 |
| -- | Adapter validation filters invalid proposals | unit | `uv run pytest tests/test_pipeline/test_stages.py::TestValidateProposals -x` | Wave 0 |
| -- | Pipeline returns partial results on stage failure | integration | `uv run pytest tests/test_pipeline/test_graph.py::TestPipelineErrorHandling -x` | Wave 0 |
| -- | Prompts format DuckDB results as structured JSON | unit | `uv run pytest tests/test_pipeline/test_prompts.py -x` | Wave 0 |
| -- | Empty/sparse data handled gracefully | unit | `uv run pytest tests/test_pipeline/test_stages.py::TestEmptyDataHandling -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_pipeline/ -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/test_pipeline/test_stages.py` -- covers PIPE-02 through PIPE-05 (individual stage unit tests with mocked LLM)
- [ ] `tests/test_pipeline/test_graph.py` -- covers PIPE-01 (full pipeline integration with all mocked deps)
- [ ] `tests/test_pipeline/test_prompts.py` -- covers prompt formatting functions (pure functions, no LLM)
- [ ] `tests/test_pipeline/conftest.py` -- needs expansion with mock_adapter, mock_pipeline_context, sample stage outputs fixtures
- [ ] langgraph dependency: `uv add langgraph>=1.1.0` -- must be added before tests can import graph modules

## Sources

### Primary (HIGH confidence)
- LangGraph 1.1.0 official docs: StateGraph API, context_schema, Runtime, async patterns -- https://docs.langchain.com/oss/python/langgraph/graph-api, https://docs.langchain.com/oss/python/langgraph/use-graph-api
- PyPI langgraph 1.1.0: version, Python 3.10+ requirement -- https://pypi.org/project/langgraph/1.1.0/
- Project codebase: PipelineState, LLMClient, response models, DuckDB queries, FirewallAdapter ABC, AdapterCapabilities -- direct file reads

### Secondary (MEDIUM confidence)
- LangGraph GitHub releases: version history, 1.1.0 release notes -- https://github.com/langchain-ai/langgraph/releases
- LangGraph discussion on using without langchain: confirmed context_schema is the recommended pattern -- https://github.com/langchain-ai/langgraph/discussions/1645
- Real Python LangGraph tutorial: node patterns, state update patterns -- https://realpython.com/langgraph-python/

### Tertiary (LOW confidence)
- Temperature tuning values: based on general LLM best practices, not empirically validated for this pipeline
- Pyright compatibility details: inferred from Phase 06 patterns, not tested with LangGraph imports

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - LangGraph 1.1.0 verified on PyPI, existing project deps confirmed via uv pip list, dry-run install shows no conflicts
- Architecture: HIGH - Context_schema + Runtime pattern verified in official docs; linear StateGraph with TypedDict verified; matches existing PipelineState design
- Pitfalls: MEDIUM - TypedDict access patterns and serialization concerns are well-known; token budget for Decide is project-specific and needs empirical validation
- Prompts/temperatures: LOW - Prompt content and temperature values will need empirical tuning

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (LangGraph 1.x API is stable post-1.0)