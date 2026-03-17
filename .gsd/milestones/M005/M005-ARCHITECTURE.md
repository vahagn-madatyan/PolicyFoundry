# M005: Architecture Improvement Plan

## Overview

This document outlines architectural improvements for PolicyFoundry, informed by the M001/M002 implementation experience and forward requirements. The goal is to reduce duplication, improve observability, harden the LLM layer for multi-model support, and prepare the pipeline for conditional branching via LangGraph.

---

## 1. Unified Pipeline — DataProvider Abstraction

### Problem

The VPC and Excel pipelines are near-identical: same 5 stages, same graph wiring, same LLM call pattern, same output schemas. The only real differences are data sourcing (DuckDB vs. in-memory) and prompt framing. This shows up as:

- **10 duplicated stage files** (`stages/` and `excel_stages/` are 1:1 mirrors)
- **8 duplicated prompt files** (`prompts/` and `excel_prompts/`)
- **2 duplicated graph files**, **2 runners**, **2 output formatters**

Bug fixes and schema changes must be applied in two places. As new source types are added (e.g., Palo Alto syslog, Fortinet CSV), this scales linearly — every source would need its own parallel tree.

### Solution

Introduce a `DataProvider` protocol that abstracts data sourcing:

```python
class DataProvider(Protocol):
    """Abstracts where traffic data comes from."""

    async def get_flow_summary(self) -> dict[str, Any]: ...
    def get_system_prompt(self, stage: str) -> str: ...
    def get_source_label(self) -> str: ...
    async def get_current_rules(self, adapter: FirewallAdapter) -> list[UniversalRule]: ...
```

**Concrete implementations:**
- `DuckDBProvider` — wraps existing `storage.queries` calls (VPC mode)
- `InMemoryProvider` — wraps `summarize_flows()` from aggregated flows (Excel mode)
- Future: `SyslogProvider`, `CSVProvider`, etc.

**One graph, one set of stages.** Each stage calls `provider.get_flow_summary()` and `provider.get_system_prompt(stage)` instead of importing source-specific modules.

### Files eliminated

| Current (duplicated) | Unified |
|---|---|
| `pipeline/stages/*.py` + `pipeline/excel_stages/*.py` | `pipeline/stages/*.py` (parameterized) |
| `pipeline/prompts/*.py` + `pipeline/excel_prompts/*.py` | `pipeline/prompts/` (registry or templates) |
| `pipeline/graph.py` + `pipeline/excel_graph.py` | `pipeline/graph.py` (single builder) |
| `pipeline/runner.py` + `pipeline/excel_runner.py` | `pipeline/runner.py` (single runner) |
| `pipeline/state.py` + `pipeline/excel_state.py` | `pipeline/state.py` (unified state) |

Estimated reduction: ~40% of pipeline code.

### Prompts as data

Source-specific prompts move from Python module constants to a registry pattern:

```python
PROMPTS: dict[str, dict[str, str]] = {
    "vpc": {
        "analyze": ANALYZE_SYSTEM_PROMPT,
        "assess": ASSESS_SYSTEM_PROMPT,
        ...
    },
    "excel": {
        "analyze": EXCEL_ANALYZE_SYSTEM_PROMPT,
        ...
    },
}
```

Or YAML/Jinja templates if prompt iteration velocity matters. Stages pull prompts by source type and stage name.

---

## 2. LangGraph Branching — Conditional Pipeline Logic

### Current state

The pipeline is a straight line: `START → analyze → assess → generate → validate → decide → END`. LangGraph adds no value over a simple `for stage in stages` loop in this configuration.

### Planned branches

LangGraph earns its keep when the pipeline needs conditional routing:

#### 2a. Risk-based routing after Assess

```
analyze → assess →┬→ generate (normal path)
                   ├→ deep_analyze → generate (HIGH risk triggers deeper analysis)
                   └→ END (CRITICAL risk, halt + alert)
```

When `SecurityAssessment.overall_risk` is CRITICAL, skip rule generation entirely — the pipeline should flag the situation for human review rather than auto-generating proposals for a fundamentally broken posture.

#### 2b. Validation loop-back

```
generate → validate →┬→ decide (all proposals valid)
                      └→ generate (invalid proposals filtered, re-generate with feedback)
```

When `validate` drops >50% of proposals due to adapter constraints, loop back to `generate` with the validation errors as additional context. Capped at 1 retry to prevent infinite loops.

#### 2c. Human-in-the-loop gate

```
decide →┬→ export (auto-approve for LOW risk)
        └→ human_review → export (MEDIUM/HIGH require approval)
```

For interactive CLI sessions, HIGH-risk decisions pause for user confirmation before export. In CI/batch mode, all decisions are exported with an `approval_required: true` flag.

#### 2d. Multi-source fan-out (future)

```
START →┬→ ingest_vpc ──────┐
       ├→ ingest_excel ────┤→ merge → analyze → ...
       └→ ingest_syslog ───┘
```

Multiple data sources analyzed together, merged into a unified flow summary before the LLM stages.

### Implementation

Conditional edges use LangGraph's `add_conditional_edges`:

```python
def route_after_assess(state: PipelineState) -> str:
    risk = state["assessment"]["overall_risk"]
    if risk == "CRITICAL":
        return "halt"
    if risk == "HIGH":
        return "deep_analyze"
    return "generate"

builder.add_conditional_edges("assess", route_after_assess, {
    "generate": "generate",
    "deep_analyze": "deep_analyze",
    "halt": END,
})
```

---

## 3. LangSmith Observability Stack

### Why

Current observability is limited to:
- Token usage counters per stage (prompt/completion/total/cost)
- Generic error codes (`LLM_PARSE_FAILED`, `LLM_CALL_FAILED`)
- Debug flag dumps raw data to console

Missing:
- **Trace visualization** — which stage took how long, what prompts were sent, what the LLM returned before validation failed
- **Prompt/response inspection** — debugging structured output failures requires seeing the raw LLM response
- **Cost tracking over time** — per-run costs are logged but not aggregated
- **Latency breakdown** — no per-stage timing
- **Regression detection** — no way to compare prompt quality across model changes

### LangSmith integration plan

#### 3a. Tracing

LangGraph has first-class LangSmith support. Enable by setting environment variables:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=policyfoundry
```

This automatically traces:
- Every graph invocation (run ID, input, output, timing)
- Every node execution (stage name, state in/out, latency)
- LLM calls via LiteLLM callback (prompt, response, tokens, model, cost)

#### 3b. LLM call instrumentation

Add LangSmith callback to the LLMClient:

```python
from langsmith import traceable

@traceable(run_type="llm", name="policyfoundry.llm.complete")
async def complete(self, messages, response_model, ...):
    ...
```

Or use LiteLLM's built-in callback:

```python
litellm.success_callback = ["langsmith"]
litellm.failure_callback = ["langsmith"]
```

This captures every LLM call — including Instructor validation retries — with full prompt/response payloads.

#### 3c. Custom metadata per trace

Tag each pipeline run with actionable metadata:

```python
from langsmith import trace

with trace(
    name="policyfoundry.analyze",
    metadata={
        "source_type": "excel",
        "model": config.llm.model,
        "provider": config.llm.provider,
        "flow_count": len(aggregated_flows),
        "file": input_file.name,
    },
    tags=["production", "excel-pipeline"],
):
    result = await graph.ainvoke(initial_state, config=run_config)
```

#### 3d. Evaluation datasets

Build evaluation datasets from production runs:
- Capture (input_summary, expected_analysis) pairs from validated good runs
- Run prompt regression tests when changing models or prompt text
- Compare GPT-4o vs GPT-5-mini vs Claude output quality on the same inputs

#### 3e. Dashboard metrics

LangSmith provides out-of-the-box:
- **Latency p50/p95/p99** per stage and overall
- **Token usage trends** over time
- **Error rate** by stage, model, and error code
- **Cost per run** aggregated by source type and model
- **Feedback loops** — rate outputs and track quality over time

#### 3f. Configuration

Add to `PolicyFoundryConfig`:

```python
class ObservabilityConfig(BaseModel):
    """LangSmith observability configuration."""
    enabled: bool = False
    project: str = "policyfoundry"
    api_key: str | None = None  # LANGCHAIN_API_KEY env var fallback
    tags: list[str] = Field(default_factory=list)
```

Enable via config:

```yaml
observability:
  enabled: true
  project: policyfoundry-prod
  tags: [production]
```

Or env var:

```bash
POLICYFOUNDRY_OBSERVABILITY__ENABLED=true
LANGCHAIN_API_KEY=ls_...
```

---

## 4. Reasoning Model Awareness

### Problem

GPT-5-mini revealed two issues the current LLM client doesn't handle:

1. **Temperature rejection** — reasoning models (o1, o3, gpt-5) don't support temperature. LiteLLM throws `UnsupportedParamsError`, which Instructor swallows into a generic retry failure.
2. **Token budget mismatch** — reasoning models use tokens for chain-of-thought internally. `max_tokens: 4096` gets consumed by thinking before the JSON output is complete, producing `"output is incomplete due to max_tokens"`.

Both failures surface as `LLM_PARSE_FAILED` with no indication of the root cause.

### Solution

#### 4a. `litellm.drop_params = True` (done)

Already applied. LiteLLM silently drops unsupported parameters (temperature, top_p, etc.) for models that don't accept them.

#### 4b. Model profiles

Define sensible defaults per model class:

```python
MODEL_PROFILES: dict[str, dict] = {
    "reasoning": {
        # o1, o3, gpt-5, gpt-5-mini
        "temperature": None,        # not supported
        "min_max_tokens": 16384,    # needs headroom for chain-of-thought
        "supports_system_role": True,  # o1 didn't, o3+ does
    },
    "chat": {
        # gpt-4o, claude-3.5, llama3
        "temperature": 0.1,
        "min_max_tokens": 4096,
        "supports_system_role": True,
    },
}
```

The LLM client auto-detects model class via LiteLLM's `get_model_info()` and applies appropriate defaults. User config overrides are respected but validated against model capabilities.

#### 4c. Better error surfacing

The `LLM_PARSE_FAILED` error should include the actual failure reason from Instructor/LiteLLM, not just the last message content:

```python
except InstructorRetryException as exc:
    # Extract the real error from the failed attempt chain
    root_causes = [
        str(attempt.exception)
        for attempt in exc.failed_attempts
        if attempt.exception
    ]
    raise PipelineError(
        f"Structured output failed after {exc.n_attempts} attempts",
        error_code="LLM_PARSE_FAILED",
        details={
            "model": self._model_name,
            "response_model": response_model.__name__,
            "attempts": exc.n_attempts,
            "root_causes": root_causes,  # actual errors, not prompt content
        },
    )
```

---

## 5. Implementation Priority

| # | Change | Effort | Impact | Depends on |
|---|---|---|---|---|
| 1 | LangSmith tracing integration | Small | Immediate observability for all runs | — |
| 2 | Better error surfacing (4c) | Small | Faster debugging | — |
| 3 | Model profiles (4b) | Small | Prevents config foot-guns | — |
| 4 | DataProvider unification (1) | Medium | ~40% code reduction, easier to add sources | — |
| 5 | Risk-based branching (2a) | Medium | Smarter pipeline behavior | 4 |
| 6 | Validation loop-back (2b) | Small | Better proposal quality | 4 |
| 7 | Human-in-the-loop gate (2c) | Medium | Safety for high-risk changes | 5 |
| 8 | LangSmith eval datasets (3d) | Medium | Prompt regression testing | 1 |
| 9 | Multi-source fan-out (2d) | Large | Cross-source analysis | 4 |

Items 1–3 can ship independently and immediately. Item 4 is the prerequisite for the branching work (5–7). Item 9 is future scope.

---

## 6. Migration notes

- **Backwards compatible:** All changes are internal. CLI interface (`analyze --source excel|local|s3`) stays the same.
- **Decision register:** New decisions from this work append to `.gsd/DECISIONS.md` per convention.
- **Test coverage:** 623 tests must continue to pass. Unified pipeline tests replace duplicated VPC/Excel test suites.
- **LangSmith is opt-in:** Disabled by default. No external dependency unless `observability.enabled: true`.

---

*Created: 2026-03-17*
*Status: Draft — pending milestone planning*
