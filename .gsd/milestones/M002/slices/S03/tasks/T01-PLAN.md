---
estimated_steps: 5
estimated_files: 7
---

# T01: NullAdapter + Pre-summarizer + Excel Pipeline State

**Slice:** S03 — Analysis Pipeline
**Milestone:** M002

## Description

Build the three foundation pieces that the pipeline stages depend on: (1) NullAdapter implementing FirewallAdapter ABC for no-FW mode (R112), (2) a pre-summarizer that computes compact statistics from AggregatedFlow/SubnetGroup data to stay within LLM context window budgets, and (3) ExcelPipelineState TypedDict defining the S03→S04 boundary contract.

## Steps

1. **NullAdapter** — Create `src/policyfoundry/adapters/null.py`. Implement `FirewallAdapter` ABC: `get_rules() → []`, `validate() → ValidationResult(valid=True)`, `capabilities() → AdapterCapabilities(name="null", vendor="none", ...)`. Keep it minimal — the adapter's job is to preserve the pipeline contract for future M03 FW integration. Register it if there's an adapter registry; otherwise leave it standalone.

2. **ExcelPipelineState** — Create `src/policyfoundry/pipeline/excel_state.py`. TypedDict with `total=False`: `run_id`, `started_at`, `current_stage`, `aggregated_flows` (list of dicts), `subnet_groups` (list of dicts), `analysis` (dict), `assessment` (dict), `proposals` (list of dicts), `decisions` (list of dicts), `token_usage` (dict). Mirrors M01's PipelineState pattern.

3. **Pre-summarizer** — Create `src/policyfoundry/pipeline/excel_summarizer.py`. Pure function `summarize_flows(flows: list[AggregatedFlow], subnet_groups: list[SubnetGroup]) -> dict[str, Any]` that computes: total_flows (sum of flow_count), unique_sources, unique_destinations, direction_breakdown (INBOUND/OUTBOUND/UNKNOWN counts), top_talkers (top 20 by flow_count), port_distribution (top 20 ports by aggregate flow_count), subnet_candidates (from SubnetGroup list). Also `format_flow_summary_message(summary: dict[str, Any]) -> str` that serializes to JSON. Target: output stays under 3K tokens for the 600-flow sample data.

4. **NullAdapter tests** — Create `tests/test_adapters/test_null_adapter.py`. Test ABC contract: get_rules returns empty list, validate returns valid for any rule, capabilities returns expected shape. Test that NullAdapter is a proper subclass of FirewallAdapter.

5. **Pre-summarizer tests** — Create `tests/test_pipeline/test_excel_summarizer.py`. Test with realistic AggregatedFlow fixtures (build 20-30 flows): verify direction breakdown, top talker ordering, port distribution counts. Verify output token estimate (len(json)/4 < 3000). Test empty input edge case.

## Must-Haves

- [ ] NullAdapter satisfies FirewallAdapter ABC with `get_rules() → []`, `validate() → valid`, generic capabilities
- [ ] ExcelPipelineState TypedDict with all pipeline stage fields (total=False)
- [ ] Pre-summarizer produces compact statistics from AggregatedFlow + SubnetGroup lists
- [ ] Pre-summarizer output stays under 3K tokens for 600-flow input
- [ ] All code passes pyright strict (src/ scope)

## Verification

- `pytest tests/test_adapters/test_null_adapter.py -v` — all NullAdapter tests pass
- `pytest tests/test_pipeline/test_excel_summarizer.py -v` — all summarizer tests pass
- `npx pyright src/policyfoundry/adapters/null.py src/policyfoundry/pipeline/excel_state.py src/policyfoundry/pipeline/excel_summarizer.py` — 0 errors

## Inputs

- `src/policyfoundry/adapters/base.py` — FirewallAdapter ABC to implement
- `src/policyfoundry/adapters/schema.py` — UniversalRule, ValidationResult, AdapterCapabilities models
- `src/policyfoundry/analysis/models.py` — AggregatedFlow, SubnetGroup models (S02 output)
- `src/policyfoundry/pipeline/state.py` — M01 PipelineState pattern to mirror

## Expected Output

- `src/policyfoundry/adapters/null.py` — NullAdapter class
- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState TypedDict
- `src/policyfoundry/pipeline/excel_summarizer.py` — summarize_flows() + format_flow_summary_message()
- `tests/test_adapters/test_null_adapter.py` — NullAdapter contract tests
- `tests/test_pipeline/test_excel_summarizer.py` — Pre-summarizer tests
