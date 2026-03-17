---
id: T01
parent: S03
milestone: M002
provides:
  - NullAdapter implementing FirewallAdapter ABC for no-FW pipeline mode
  - ExcelPipelineState TypedDict defining S03→S04 boundary contract
  - Pre-summarizer computing compact flow statistics within 3K token budget
key_files:
  - src/policyfoundry/adapters/null.py
  - src/policyfoundry/pipeline/excel_state.py
  - src/policyfoundry/pipeline/excel_summarizer.py
key_decisions:
  - Registered NullAdapter as built-in fallback in AdapterRegistry (alongside aws_sg) rather than leaving standalone
  - ExcelPipelineState stores aggregated_flows inline as list[dict] (Excel datasets small enough; no need for path references like M01)
  - Pre-summarizer uses Counter-based aggregation capped at top-20 for talkers and ports to keep output compact
patterns_established:
  - NullAdapter pattern for future adapters that need no-op behavior
  - Pre-summarization as a separate pure function consumed by pipeline stages (not embedded in stage logic)
observability_surfaces:
  - none
duration: fast
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: NullAdapter + Pre-summarizer + Excel Pipeline State

**Built NullAdapter (FirewallAdapter ABC), ExcelPipelineState TypedDict, and pre-summarizer with token-budget-constrained output — all passing pyright strict and 31 new tests.**

## What Happened

Implemented the three foundation pieces for the S03 analysis pipeline:

1. **NullAdapter** (`null.py`): Minimal FirewallAdapter implementation — empty rules, always-valid validation, generic capabilities. Registered in AdapterRegistry as a built-in `"null"` adapter with direct-import fallback (same pattern as `aws_sg`).

2. **ExcelPipelineState** (`excel_state.py`): TypedDict with `total=False` mirroring M01's PipelineState but carrying inline flow data (run_id, started_at, current_stage, aggregated_flows, subnet_groups, analysis, assessment, proposals, decisions, token_usage).

3. **Pre-summarizer** (`excel_summarizer.py`): Two pure functions — `summarize_flows()` computes total_flows, unique sources/destinations, direction breakdown, top-20 talkers, top-20 port distribution, and subnet candidates. `format_flow_summary_message()` serializes to compact JSON. The 600-flow test confirms output stays under 3K tokens.

## Verification

- `pytest tests/test_adapters/test_null_adapter.py -v` → 15 passed (ABC contract, registry integration)
- `pytest tests/test_pipeline/test_excel_summarizer.py -v` → 16 passed (aggregation, ordering, token budget, empty input, JSON serialization)
- `npx pyright src/policyfoundry/adapters/null.py src/policyfoundry/pipeline/excel_state.py src/policyfoundry/pipeline/excel_summarizer.py` → 0 errors
- `pytest tests/ -x -q` → 513 passed, 0 failures (full suite green)

### Slice-level verification status (T01 of 5 tasks):
- ✅ `pytest tests/test_adapters/test_null_adapter.py -v` — NullAdapter satisfies FirewallAdapter ABC
- ✅ `pytest tests/test_pipeline/test_excel_summarizer.py -v` — Pre-summarization within token budget
- ⬜ `pytest tests/test_pipeline/test_excel_stages.py -v` — not yet created (T02)
- ⬜ `pytest tests/test_pipeline/test_excel_pipeline.py -v` — not yet created (T03)
- ⬜ `pytest tests/test_output/test_excel_output.py -v` — not yet created (T04/T05)
- ✅ `npx pyright src/policyfoundry/` — 0 errors on new code
- ✅ `pytest tests/ -x -q` — 513 passed, 0 failures

## Diagnostics

None — these are pure data structures and functions with no runtime side effects.

## Deviations

Added NullAdapter to AdapterRegistry as a built-in (plan said "register if registry exists; otherwise standalone"). Registry exists, so registered it.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/adapters/null.py` — NullAdapter implementing FirewallAdapter ABC
- `src/policyfoundry/adapters/registry.py` — Added null adapter as built-in fallback
- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState TypedDict
- `src/policyfoundry/pipeline/excel_summarizer.py` — summarize_flows() + format_flow_summary_message()
- `tests/test_adapters/test_null_adapter.py` — 15 NullAdapter contract + registry tests
- `tests/test_pipeline/test_excel_summarizer.py` — 16 pre-summarizer tests
