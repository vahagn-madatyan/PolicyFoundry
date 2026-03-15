---
estimated_steps: 5
estimated_files: 10
---

# T04: Pipeline Graph + Runner + Output Formatters

**Slice:** S03 — Analysis Pipeline
**Milestone:** M002

## Description

Wire everything together: LangGraph graph composes the 5 stages, runner provides the async entry point (defaulting to NullAdapter), and output formatters render ExcelPipelineState as Rich terminal output and JSON. Refactor M01's private Rich renderers to shared public functions so both pipelines reuse them. This task closes the slice demo — full pipeline integration test with mock LLM.

## Steps

1. **ExcelPipelineContext + graph** — Create `src/policyfoundry/pipeline/excel_graph.py`. Define `ExcelPipelineContext` dataclass with `llm_client`, `adapter`, `aggregated_flows: list[AggregatedFlow]`, `subnet_groups: list[SubnetGroup]`. Define `build_excel_pipeline() -> CompiledStateGraph` — 5-node linear graph mirroring M01: `StateGraph(ExcelPipelineState, context_schema=ExcelPipelineContext)` with edges analyze→assess→generate→validate→decide.

2. **Runner** — Create `src/policyfoundry/pipeline/excel_runner.py`. `async def run_excel_pipeline(llm_client, records: list[ExcelTrafficRecord], adapter=None) -> ExcelPipelineState`. If adapter is None, default to NullAdapter(). Calls `aggregate_flows(records)` and `group_to_subnets(aggregated_flows)` to prepare data. Creates ExcelPipelineContext and initial state (run_id, started_at, current_stage). Invokes `build_excel_pipeline().ainvoke()`. Wraps errors in PipelineError. Note: token_usage is NOT attached inside the runner — the CLI layer calls `llm_client.get_usage()` after execution (matching M01 pattern).

3. **Refactor shared Rich renderers** — In `src/policyfoundry/output/rich_output.py`, rename private renderers to public: `_render_traffic_analysis` → `render_traffic_analysis`, `_render_security_assessment` → `render_security_assessment`, `_render_proposals` → `render_proposals`, `_render_decisions` → `render_decisions`, `_render_token_usage` → `render_token_usage`, `_risk_text` → `risk_text`. Update `format_rich()` to call the renamed functions. Update `__init__.py` exports if needed. Verify M01 output tests still pass.

4. **Excel output formatters** — Create `src/policyfoundry/output/excel_rich_output.py` with `format_excel_rich(state: ExcelPipelineState, *, console=None) -> None`. Renders an Excel-specific summary panel (source: Excel traffic export, total aggregated flows, direction breakdown, subnet candidates count) then reuses shared `render_traffic_analysis`, `render_security_assessment`, `render_proposals`, `render_decisions`, `render_token_usage`. Create `src/policyfoundry/output/excel_json_output.py` with `format_excel_json(state: ExcelPipelineState) -> str` via an `ExcelPipelineResult` model in `models.py` (or inline). Update `output/__init__.py` with new exports.

5. **Integration + output tests** — Create `tests/test_pipeline/test_excel_pipeline.py`: test graph compiles, test full runner with mock LLM produces valid state with all fields, test runner defaults to NullAdapter, test runner wraps errors in PipelineError. Create `tests/test_output/test_excel_output.py`: test Rich formatter renders without errors, test JSON formatter produces valid JSON with expected keys, test Excel summary panel content. Run full test suite to verify no regressions.

## Must-Haves

- [ ] ExcelPipelineContext carries aggregated_flows and subnet_groups (not data_dir)
- [ ] build_excel_pipeline() creates a compilable 5-node LangGraph
- [ ] run_excel_pipeline() defaults to NullAdapter when adapter=None
- [ ] run_excel_pipeline() wraps errors in PipelineError with stage context
- [ ] M01 Rich renderers renamed to public — format_rich() still works
- [ ] Excel Rich formatter reuses shared renderers + adds Excel summary panel
- [ ] Excel JSON formatter produces valid JSON from ExcelPipelineState
- [ ] Full pipeline integration test passes with mock LLM
- [ ] All M01 output tests still pass after refactor
- [ ] All code passes pyright strict (src/ scope)

## Verification

- `pytest tests/test_pipeline/test_excel_pipeline.py -v` — pipeline integration tests pass
- `pytest tests/test_output/test_excel_output.py -v` — Excel output tests pass
- `pytest tests/test_output/ -v` — M01 output tests still pass after refactor
- `npx pyright src/policyfoundry/pipeline/excel_graph.py src/policyfoundry/pipeline/excel_runner.py src/policyfoundry/output/` — 0 errors
- `pytest tests/ -x -q` — full suite passes, 0 failures

## Observability Impact

- Signals added/changed: PipelineError with `error_code="PIPELINE_STAGE_FAILED"` and stage name in details (mirrors M01)
- How a future agent inspects this: `format_excel_json()` serializes full pipeline state; `ExcelPipelineResult.from_state()` for typed access
- Failure state exposed: Failed stage name, original exception chained

## Inputs

- `src/policyfoundry/pipeline/excel_stages/` — All 5 stage functions from T02 + T03
- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState from T01
- `src/policyfoundry/adapters/null.py` — NullAdapter from T01
- `src/policyfoundry/analysis/aggregator.py` — aggregate_flows() from S02
- `src/policyfoundry/analysis/subnet.py` — group_to_subnets() from S02
- `src/policyfoundry/output/rich_output.py` — M01 renderers to refactor
- `src/policyfoundry/output/models.py` — TokenUsage, PipelineResult patterns

## Expected Output

- `src/policyfoundry/pipeline/excel_graph.py` — ExcelPipelineContext + build_excel_pipeline()
- `src/policyfoundry/pipeline/excel_runner.py` — run_excel_pipeline() async entry point
- `src/policyfoundry/output/rich_output.py` — Refactored with public renderers
- `src/policyfoundry/output/excel_rich_output.py` — format_excel_rich()
- `src/policyfoundry/output/excel_json_output.py` — format_excel_json()
- `src/policyfoundry/output/models.py` — ExcelPipelineResult added
- `src/policyfoundry/output/__init__.py` — Updated exports
- `tests/test_pipeline/test_excel_pipeline.py` — Pipeline graph + runner integration tests
- `tests/test_output/test_excel_output.py` — Excel Rich + JSON output tests
