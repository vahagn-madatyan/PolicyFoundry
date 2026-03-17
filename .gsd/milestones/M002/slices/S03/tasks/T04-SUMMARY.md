---
id: T04
parent: S03
milestone: M002
provides:
  - ExcelPipelineContext dataclass with llm_client, adapter, aggregated_flows, subnet_groups
  - build_excel_pipeline() — compilable 5-node LangGraph (analyze→assess→generate→validate→decide)
  - run_excel_pipeline() — async entry point defaulting to NullAdapter, PipelineError wrapping
  - format_excel_rich() — Rich terminal output with Excel-specific summary panel + shared renderers
  - format_excel_json() — JSON serialization via ExcelPipelineResult
  - Public shared renderers (render_traffic_analysis, render_security_assessment, etc.) reusable across pipelines
key_files:
  - src/policyfoundry/pipeline/excel_graph.py
  - src/policyfoundry/pipeline/excel_runner.py
  - src/policyfoundry/output/excel_rich_output.py
  - src/policyfoundry/output/excel_json_output.py
  - src/policyfoundry/output/models.py
  - src/policyfoundry/output/rich_output.py
key_decisions:
  - build_excel_pipeline() returns Any to work around LangGraph's invariant CompiledStateGraph generics (same pattern as M01)
  - Refactored M01 Rich renderers from private (_render_*) to public (render_*) with local variable rename (risk_text → risk_styled) to avoid shadowing the now-public function
  - ExcelPipelineResult follows PipelineResult pattern exactly — from_state() reconstructs typed models from state dicts
patterns_established:
  - Public shared renderers (render_traffic_analysis, render_decisions, etc.) consumed by both M01 format_rich() and new format_excel_rich()
  - Pipeline-specific summary panels (_render_excel_summary) alongside shared section renderers
  - ExcelPipelineContext carries domain models (AggregatedFlow, SubnetGroup) directly instead of data_dir (data small enough for inline)
observability_surfaces:
  - PipelineError with error_code="PIPELINE_STAGE_FAILED" and stage name in details
  - format_excel_json() serializes full pipeline state; ExcelPipelineResult.from_state() for typed access
  - Failed stage name and original exception chained in PipelineError
duration: 1 session
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T04: Pipeline Graph + Runner + Output Formatters

**Built ExcelPipelineContext, 5-node LangGraph, async runner with NullAdapter default, and Excel Rich/JSON output formatters reusing refactored shared renderers — 24 new tests pass, all 564 total pass, pyright clean on new files.**

## What Happened

1. Created `excel_graph.py` with `ExcelPipelineContext` dataclass (llm_client, adapter, aggregated_flows, subnet_groups) and `build_excel_pipeline()` composing the 5 Excel stages into a linear LangGraph.

2. Created `excel_runner.py` with `run_excel_pipeline()` — aggregates raw ExcelTrafficRecords via `aggregate_flows()` + `group_to_subnets()`, seeds initial state with flows/subnets inline, defaults to NullAdapter when adapter=None, wraps errors in PipelineError with stage context.

3. Refactored M01 Rich renderers from private to public: `_render_traffic_analysis` → `render_traffic_analysis`, `_render_security_assessment` → `render_security_assessment`, `_render_proposals` → `render_proposals`, `_render_decisions` → `render_decisions`, `_render_token_usage` → `render_token_usage`, `_risk_text` → `risk_text`. Fixed local variable shadowing (renamed `risk_text` locals to `risk_styled`). Updated `__init__.py` exports. All 14 M01 output tests pass unchanged.

4. Created `excel_rich_output.py` with Excel-specific summary panel (source type, aggregated flow count, direction breakdown, subnet candidates count) then delegates to shared renderers. Created `excel_json_output.py` + `ExcelPipelineResult` model in `models.py` following the PipelineResult pattern.

5. Fixed pyright strict issues: annotated `raw` dicts as `dict[str, Any]` in both PipelineResult and ExcelPipelineResult `from_state()` methods, and in `format_rich()`. Used `Any` return type for `build_excel_pipeline()` to avoid LangGraph generic invariance issue.

## Verification

- `pytest tests/test_pipeline/test_excel_pipeline.py -v` — 9 passed (graph compiles, runner end-to-end, NullAdapter default, metadata, stage order, error handling)
- `pytest tests/test_output/test_excel_output.py -v` — 15 passed (Rich summary panel, direction breakdown, shared sections, empty state, JSON valid, all keys, aggregated flows, ExcelPipelineResult reconstruction)
- `pytest tests/test_output/ -v` — 29 passed (14 M01 + 15 Excel, no regressions)
- `npx pyright src/policyfoundry/pipeline/excel_graph.py src/policyfoundry/pipeline/excel_runner.py src/policyfoundry/output/` — 0 errors
- `pytest tests/ -x -q` — 564 passed, 0 failures

### Slice-level verification (all pass):
- `pytest tests/test_adapters/test_null_adapter.py -v` — 15 passed ✓
- `pytest tests/test_pipeline/test_excel_summarizer.py -v` — 16 passed ✓
- `pytest tests/test_pipeline/test_excel_stages.py -v` — 27 passed ✓
- `pytest tests/test_pipeline/test_excel_pipeline.py -v` — 9 passed ✓
- `pytest tests/test_output/test_excel_output.py -v` — 15 passed ✓
- `npx pyright` on new files — 0 errors ✓
- `pytest tests/ -x -q` — 564 passed, 0 failures ✓

## Diagnostics

- `format_excel_json(state)` serializes full pipeline state as JSON for inspection
- `ExcelPipelineResult.from_state(state)` provides typed programmatic access to all stage outputs
- PipelineError includes `error_code="PIPELINE_STAGE_FAILED"`, stage name in details dict, and original exception chained

## Deviations

- Fixed pre-existing pyright issues in `PipelineResult.from_state()` (annotated `raw` as `dict[str, Any]`) as part of the same pattern fix for ExcelPipelineResult — not in plan but necessary for clean pyright on the output module.

## Known Issues

- 18 pre-existing pyright errors in src/policyfoundry/ (boto3 stubs, litellm exports, parser IP types, main.py) — none in new or modified files.

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_graph.py` — ExcelPipelineContext + build_excel_pipeline() (created)
- `src/policyfoundry/pipeline/excel_runner.py` — run_excel_pipeline() async entry point (created)
- `src/policyfoundry/output/rich_output.py` — Refactored renderers from private to public (modified)
- `src/policyfoundry/output/excel_rich_output.py` — format_excel_rich() with Excel summary panel (created)
- `src/policyfoundry/output/excel_json_output.py` — format_excel_json() via ExcelPipelineResult (created)
- `src/policyfoundry/output/models.py` — ExcelPipelineResult added, pyright fix for raw dict typing (modified)
- `src/policyfoundry/output/__init__.py` — Updated exports for shared renderers + Excel formatters (modified)
- `tests/test_pipeline/test_excel_pipeline.py` — 9 integration tests: graph, runner, errors (created)
- `tests/test_output/test_excel_output.py` — 15 output tests: Rich + JSON + ExcelPipelineResult (created)
