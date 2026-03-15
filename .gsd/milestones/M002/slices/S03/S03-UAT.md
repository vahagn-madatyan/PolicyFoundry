# S03: Analysis Pipeline — UAT

**Milestone:** M002
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S03 uses mocked LLM throughout — real LLM integration is deferred to S05 UAT. All verification is through contract tests proving stage composition, output shape, and renderer correctness.

## Preconditions

- Python 3.12+ virtualenv with all dependencies installed (`.venv/`)
- No running services required — all tests use mock LLM and in-memory data

## Smoke Test

Run `pytest tests/test_pipeline/test_excel_pipeline.py::TestRunExcelPipeline::test_full_pipeline_produces_all_outputs -v` — should pass in <1s, confirming the full 5-stage pipeline composes and produces analysis, assessment, proposals, and decisions.

## Test Cases

### 1. NullAdapter satisfies FirewallAdapter contract

1. `pytest tests/test_adapters/test_null_adapter.py -v`
2. **Expected:** 15 passed — get_rules returns empty list, validate returns valid, capabilities are generic, registered in AdapterRegistry

### 2. Pre-summarizer stays within token budget

1. `pytest tests/test_pipeline/test_excel_summarizer.py -v`
2. **Expected:** 16 passed — 600 flows produce summary under 3K tokens, top talkers/ports capped at 20, empty input handled

### 3. All 5 pipeline stages produce correct output types

1. `pytest tests/test_pipeline/test_excel_stages.py -v`
2. **Expected:** 27 passed — analyze returns TrafficAnalysis, assess returns SecurityAssessment, generate returns PolicyProposalList, validate filters by adapter, decide returns RuleDecisionList or short-circuits on empty proposals

### 4. Full pipeline graph compiles and executes end-to-end

1. `pytest tests/test_pipeline/test_excel_pipeline.py -v`
2. **Expected:** 9 passed — graph has 5 nodes, runner defaults to NullAdapter, stages execute in order, PipelineError wrapping works

### 5. Rich and JSON output formatters render correctly

1. `pytest tests/test_output/test_excel_output.py -v`
2. **Expected:** 15 passed — Excel summary panel shows source type and direction breakdown, shared sections render, JSON contains all stage keys, ExcelPipelineResult reconstructs typed models

### 6. No regressions in M01 output

1. `pytest tests/test_output/ -v`
2. **Expected:** 29 passed (14 M01 + 15 Excel) — shared renderer refactor (private → public) didn't break M01

### 7. Full test suite green

1. `pytest tests/ -x -q`
2. **Expected:** 564 passed, 0 failures

## Edge Cases

### Empty proposals short-circuit in Decide

1. `pytest tests/test_pipeline/test_excel_stages.py -k "empty_proposals_short_circuits" -v`
2. **Expected:** Decide stage returns empty decisions without calling LLM

### Empty state renders without errors

1. `pytest tests/test_output/test_excel_output.py -k "empty_state" -v`
2. **Expected:** Both Rich and JSON formatters handle state with no pipeline results

### Failing validation removes proposal

1. `pytest tests/test_pipeline/test_excel_stages.py -k "failing_validation_removes_proposal" -v`
2. **Expected:** Invalid proposals filtered out by adapter.validate() (only visible with non-NullAdapter)

## Failure Signals

- Any test in test_excel_pipeline.py failing — indicates stage composition is broken
- Pre-summarizer token budget test failing — context window risk resurfaced
- M01 output tests regressing — shared renderer refactor caused breakage
- pyright errors on new files — type safety violated

## Requirements Proved By This UAT

- R106 — Multi-stage LangGraph pipeline: 5 stages compose, graph compiles, runner executes e2e (mock LLM)
- R107 — AI-generated justification and risk: generate stage produces proposals with justification, decide stage assigns risk/action
- R112 — NullAdapter: implements ABC, registered in registry, pipeline defaults to it

## Not Proven By This UAT

- Real LLM output quality — all tests use mock LLM with predetermined responses
- Prompt effectiveness with actual models — whether the system prompts produce good traffic analysis
- Token usage accuracy with real LLM calls — cost tracking infrastructure is reused from M01 but not exercised with actual API calls
- Rich terminal visual quality — tests verify text content, not visual appearance
- End-to-end CLI integration — S05 UAT will verify `policyfoundry analyze --source excel` flow

## Notes for Tester

- The pre-summarizer is the key innovation in this slice — it compresses 40K tokens of raw flow data into ~2-3K tokens of statistics. If you want to inspect what the LLM actually sees, call `format_flow_summary_message()` directly.
- The assess stage's prompt is the highest-risk component — it must infer "likely existing rules" from traffic patterns alone. Real LLM testing in S05 will reveal whether this prompt is effective.
- NullAdapter is intentionally minimal — it exists to satisfy the adapter interface contract. Real adapter integration is M003.
