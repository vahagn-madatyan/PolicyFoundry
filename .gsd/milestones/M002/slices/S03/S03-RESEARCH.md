# S03: Analysis Pipeline — Research

**Date:** 2026-03-15

## Summary

S03 builds the full LangGraph pipeline for Excel traffic analysis: 5 stages (Analyze → Assess → Generate → Validate → Decide), a NullAdapter for no-FW mode, and Rich/JSON output formatters. The primary risk is **context window limits** — 600 aggregated flows serialize to ~40K tokens as JSON, far exceeding practical context budgets. The solution is to follow M01's proven pattern: pre-summarize data in Python and send compact statistics to the LLM, not raw flow lists.

The existing M01 pipeline provides a complete, tested template to follow. The `PipelineContext` dataclass + `Runtime[PipelineContext]` DI pattern, the `TypedDict(total=False)` state container, the `PolicyProposalList`/`RuleDecisionList` wrapper model pattern for Instructor lists, and the stage function signature `async def stage(state, runtime) -> dict[str, Any]` are all established and working (D021, D022, D023). The new Excel pipeline creates a parallel graph (`build_excel_pipeline()` per D039), not a modification of M01's graph.

M01's schema models (`TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision`) can be **reused directly** — the output shape is identical. The difference is in the prompts and input formatting, not the output contracts. The existing `format_rich()` section renderers (`_render_traffic_analysis`, `_render_security_assessment`, etc.) can also be shared — the Excel formatter needs only an Excel-specific summary panel.

## Recommendation

Follow M01's architecture exactly, creating a parallel pipeline with Excel-specific prompts and a pre-summarization layer:

1. **Pre-summarize flows in Python** before any LLM call: compute statistics (totals, top talkers, port distribution, direction breakdown) from the `AggregatedFlow` list. Send ~2-3K tokens of statistics to the LLM, not ~40K tokens of raw flows.
2. **Reuse M01 schema models** — `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision` work for both pipelines.
3. **NullAdapter** implements `FirewallAdapter` ABC: `get_rules() → []`, `validate() → valid`, generic capabilities.
4. **Excel-specific prompts** that understand: no existing rules to compare (NullAdapter), subnet grouping candidates are pre-computed, direction inference is already done, traffic is from a firewall export not VPC flow logs.
5. **Refactor shared output renderers** from `rich_output.py` — make `_render_traffic_analysis`, `_render_security_assessment`, `_render_proposals`, `_render_decisions`, `_render_token_usage` importable. The Excel formatter composes them with an Excel-specific summary panel.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Structured LLM output | `LLMClient.complete()` with Instructor | Already handles retries, validation, token tracking (D018, D031) |
| Pipeline orchestration | LangGraph `StateGraph` + `context_schema` | Established pattern (D021), proven in M01 with 62 tests |
| List output from LLM | `PolicyProposalList` / `RuleDecisionList` wrapper BaseModel | Instructor needs single `response_model` for lists (D023) |
| Token usage tracking | `TokenUsage.add_call()` with per-stage labels | Automatic via LLMClient (reuse as-is) |
| Risk-colored Rich output | `RISK_COLORS` dict + `_risk_text()` helper in `rich_output.py` | Already handles LOW/MEDIUM/HIGH/CRITICAL styling |
| Pipeline error handling | `PipelineError` with `error_code` and `details` | Established error hierarchy with CLI boundary rendering (D030) |

## Existing Code and Patterns

- `pipeline/graph.py` — `PipelineContext` dataclass + `build_pipeline()` using `StateGraph(PipelineState, context_schema=PipelineContext)`. Mirror this pattern for `ExcelPipelineContext` + `build_excel_pipeline()`.
- `pipeline/runner.py` — `run_pipeline()` creates context, initial state, invokes graph, catches errors. Mirror for `run_excel_pipeline()`.
- `pipeline/state.py` — `PipelineState(TypedDict, total=False)` with all optional fields. Mirror for `ExcelPipelineState`.
- `pipeline/stages/analyze.py` — Stage pattern: takes `(state, runtime)`, queries data, formats user message, calls `ctx.llm_client.complete(messages, ResponseModel, temperature=X)`, returns `dict[str, Any]`.
- `pipeline/stages/validate.py` — Non-LLM stage: filters proposals through `adapter.validate()` (D026). Reuse exact pattern — NullAdapter will pass everything through, but the seam is preserved for M03.
- `pipeline/stages/decide.py` — Short-circuits on empty proposals (D024). Uses `format_decide_user_message()` to compress proposals before LLM call. Follow this token-efficiency pattern.
- `pipeline/prompts/decide.py` — `format_decide_user_message()` extracts essential fields and truncates justification to 100 chars. Critical pattern for staying within token budgets.
- `adapters/safety.py` — `ReadOnlyAdapter` wraps `FirewallAdapter`. Shows the adapter wrapper pattern; NullAdapter is simpler (no wrapping, just returns empty/valid).
- `adapters/base.py` — `FirewallAdapter` ABC: `get_rules()`, `validate()`, `capabilities()`. NullAdapter implements all three.
- `output/rich_output.py` — Section renderers are private functions. These need to be made importable (rename to remove underscore prefix, or extract to a shared module) for the Excel formatter to reuse.
- `output/models.py` — `PipelineResult.from_state()` reconstructs typed models from state dicts. Need an `ExcelPipelineResult` or modify to handle both state shapes.
- `analysis/models.py` — `AggregatedFlow`, `SubnetGroup` are the S02→S03 input contract. `AggregatedFlow` has `flow_count`, `service_port`, `direction`, `src_interface`, `dst_interface`.
- `analysis/aggregator.py` — `aggregate_flows()` returns `list[AggregatedFlow]` sorted by `flow_count` descending (S02 Forward Intelligence).
- `analysis/subnet.py` — `group_to_subnets()` returns `list[SubnetGroup]` with `shared_patterns: list[dict]`.

## Constraints

- **Context window budget**: 600 flows × 267 chars/flow = ~40K tokens in JSON. Even compact CSV = ~6K tokens. Must pre-summarize to ~2-3K tokens for the analyze/assess prompts. The generate stage can include top-N flow details (~50 flows) for specific rule proposals.
- **LangGraph `context_schema`**: Must be a dataclass or TypedDict. `ExcelPipelineContext` should be a dataclass mirroring `PipelineContext` but carrying `aggregated_flows` and `subnet_groups` instead of `data_dir`.
- **Instructor `response_model`**: Must be a single Pydantic `BaseModel`. Lists require a wrapper model (D023). Reuse `PolicyProposalList`, `RuleDecisionList`.
- **Temperature settings**: 0.1 for precision stages (Analyze, Assess, Decide), 0.3 for creative stages (Generate) per D025.
- **`dict[str, Any]` return type**: Stage functions return `dict[str, Any]` for pyright strict compatibility (D022).
- **asyncio.run() in CLI**: Typer commands are sync with internal `asyncio.run()` (D027). The Excel runner is async; the CLI wraps it.
- **Pyright strict on `src/`**: All new code under `src/` must pass pyright strict (D001).
- **NullAdapter must satisfy `FirewallAdapter` ABC exactly**: `get_rules() -> list[UniversalRule]`, `validate(rule, *, current_rule_count, allow_wide_open) -> ValidationResult`, `capabilities() -> AdapterCapabilities`.

## Common Pitfalls

- **Sending raw flows to LLM** — 40K tokens will exceed context windows on smaller models (8K-32K). Pre-summarize in Python: compute statistics, send top-N flows. The analyze stage should compute stats before calling the LLM, just like M01 queries DuckDB first.
- **NullAdapter assess stage assumes rules exist** — M01's assess stage compares traffic against `adapter.get_rules()`. With NullAdapter returning `[]`, the assess prompt must be rewritten to infer likely existing rules from traffic patterns (high-volume well-known port traffic is probably already allowed) rather than comparing against actual rules.
- **PolicyProposal.rule requires valid UniversalRule** — The LLM must produce `UniversalRule` with valid `NetworkEndpoint` (at least one of cidr/security_group_id/tag/is_any per D015). Prompts must include the schema constraints. For Excel analysis, cidr-based endpoints are the only sensible option.
- **DirectionLabel.UNKNOWN flows** — ~770 records from the sample data have UNKNOWN direction (both ephemeral ports). The analyze prompt must handle these gracefully — either skip or flag for human review. Don't force the LLM to invent a direction.
- **SubnetGroup.shared_patterns dict keys** — Keys are `counterpart_ip`, `service_port`, `protocol` (strings from attribute names). The prompts must explain what these mean so the LLM can reason about subnet grouping.
- **Token usage not attached to state** — In M01, `llm_client.get_usage()` is called *after* pipeline execution and manually attached to state in the CLI. The Excel runner must do the same. Don't try to attach usage inside a stage function.

## Open Risks

- **Prompt quality for the assess stage without real FW rules** — This is the most novel part. M01's assess stage had real SG rules to compare against. The Excel pipeline must infer "likely existing rules" from traffic volume patterns. If the prompts are poorly crafted, the LLM may produce low-quality assessments. Mitigate by being explicit: "assume high-volume traffic on well-known ports is already permitted."
- **LLM-generated UniversalRule validity** — The LLM must produce CIDRs (not bare IPs) for `NetworkEndpoint.cidr`. If it produces `10.1.2.3` instead of `10.1.2.3/32`, Pydantic validation will fail. The Instructor retry mechanism (D018) handles this via validation feedback, but poor initial prompts will waste retries. Include explicit CIDR format examples in the prompt.
- **SubnetGroup to rule mapping** — The generate stage must map `SubnetGroup` candidates (pre-computed /24 suggestions) to actual rule proposals. The LLM needs to decide whether a subnet rule is appropriate or whether individual IP rules are better. This requires clear prompt guidance about when to use subnet rules (2+ IPs sharing a pattern) vs. individual rules.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| LangGraph | `langchain-ai/deepagents@langgraph-docs` (1.9K installs) | available — not installed (existing M01 patterns sufficient) |
| LangGraph | `langchain-ai/langchain-skills@langgraph-fundamentals` (1.6K installs) | available — not installed (existing M01 patterns sufficient) |

## Sources

- LangGraph `context_schema` + `Runtime` DI pattern confirmed via Context7 docs and existing `pipeline/graph.py` implementation
- Token estimates computed empirically: `AggregatedFlow` JSON = 267 chars/flow, compact CSV = 42 chars/flow
- M01 pipeline patterns from `pipeline/stages/*.py`, `pipeline/graph.py`, `pipeline/runner.py`, `pipeline/schema.py`
- 482 passing tests as baseline (verified via `pytest tests/ -x -q`)
