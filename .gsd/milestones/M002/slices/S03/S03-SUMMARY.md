---
id: S03
parent: M002
milestone: M002
provides:
  - NullAdapter implementing FirewallAdapter ABC for no-FW pipeline mode (R112)
  - 5-node LangGraph pipeline (Analyze → Assess → Generate → Validate → Decide) for Excel traffic data (R106)
  - AI-generated business justifications and risk classifications per proposed rule (R107)
  - Pre-summarizer compressing 600 flows into ~2-3K tokens for LLM context windows
  - ExcelPipelineState TypedDict defining S03→S04 boundary contract
  - ExcelPipelineContext dataclass carrying llm_client, adapter, aggregated_flows, subnet_groups
  - run_excel_pipeline() async entry point with NullAdapter default and PipelineError wrapping
  - format_excel_rich() Rich terminal output with Excel-specific summary panel + shared renderers
  - format_excel_json() JSON serialization via ExcelPipelineResult
  - Public shared Rich renderers (render_traffic_analysis, render_decisions, etc.) reusable across pipelines
requires:
  - slice: S02
    provides: AggregatedFlow, SubnetGroup models and aggregate_flows/group_to_subnets/infer_direction functions
affects:
  - S04 (consumes ExcelPipelineState for xlsx/pdf export)
  - S05 (consumes pipeline runner + output formatters for CLI wiring)
key_files:
  - src/policyfoundry/adapters/null.py
  - src/policyfoundry/pipeline/excel_state.py
  - src/policyfoundry/pipeline/excel_summarizer.py
  - src/policyfoundry/pipeline/excel_graph.py
  - src/policyfoundry/pipeline/excel_runner.py
  - src/policyfoundry/pipeline/excel_stages/analyze.py
  - src/policyfoundry/pipeline/excel_stages/assess.py
  - src/policyfoundry/pipeline/excel_stages/generate.py
  - src/policyfoundry/pipeline/excel_stages/validate.py
  - src/policyfoundry/pipeline/excel_stages/decide.py
  - src/policyfoundry/output/excel_rich_output.py
  - src/policyfoundry/output/excel_json_output.py
  - src/policyfoundry/output/rich_output.py
  - src/policyfoundry/output/models.py
key_decisions:
  - D048: Shared Rich renderers made public (remove underscore prefix) for cross-pipeline reuse
  - D049: Pre-summarizer before LLM context — Python-computed statistics (~2-3K tokens) instead of raw flow serialization (~40K tokens)
  - D050: ExcelPipelineContext carries flow data inline (not data_dir) — Excel datasets small enough for in-memory
  - NullAdapter registered as built-in in AdapterRegistry (alongside aws_sg)
  - Assess stage infers likely existing rules from traffic patterns when adapter returns empty rules
  - Decide prompt constrains actions to CREATE or SKIP only (no UPDATE — no existing rules baseline)
  - Generate prompt includes SubnetGroup shared_patterns and CIDR format guidance
patterns_established:
  - Excel pipeline mirrors M01 architecture (context DI, 5-stage graph, stage → dict[str, Any]) but with inline flow data instead of DuckDB queries
  - Pre-summarization as a separate pure function consumed by pipeline stages (not embedded in stage logic)
  - Pipeline-specific summary panels alongside shared section renderers for output formatting
  - ExcelPipelineResult follows PipelineResult pattern (from_state() for typed reconstruction)
observability_surfaces:
  - PipelineError with error_code="PIPELINE_STAGE_FAILED", stage name in details, chained original exception
  - format_excel_json() serializes full pipeline state as JSON for inspection
  - ExcelPipelineResult.from_state() for programmatic typed access to all stage outputs
  - Token usage tracked per-stage via LLMClient (reuses M01 infrastructure)
drill_down_paths:
  - .gsd/milestones/M002/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T04-SUMMARY.md
duration: 4 tasks across 1 session
verification_result: passed
completed_at: 2026-03-15
---

# S03: Analysis Pipeline

**Full 5-stage LangGraph pipeline (Analyze → Assess → Generate → Validate → Decide) producing risk-scored FW rule proposals with AI-generated justifications from Excel traffic data — with NullAdapter for no-FW mode, pre-summarizer for context window safety, Rich terminal output, and JSON export.**

## What Happened

Built the core intelligence layer for Excel traffic analysis across 4 tasks:

**T01 — Foundation pieces.** NullAdapter satisfies FirewallAdapter ABC (empty rules, valid validation, generic capabilities) and is registered in AdapterRegistry as built-in. ExcelPipelineState TypedDict defines the pipeline data contract. Pre-summarizer computes compact flow statistics (direction breakdown, top-20 talkers, top-20 ports, subnet candidates) that fit within ~2-3K tokens — solving the context window risk (600 flows × 267 chars = ~40K tokens of raw data).

**T02 — Analyze + Assess stages.** Analyze calls the pre-summarizer then passes compact stats to the LLM with an Excel-specific system prompt (not VPC-oriented). Assess is the most novel stage: with NullAdapter returning empty rules, the prompt instructs the LLM to infer likely existing rules from traffic patterns (high-volume well-known ports are probably already permitted). Both stages follow M01's async signature.

**T03 — Generate + Validate + Decide stages.** Generate includes SubnetGroup shared_patterns and CIDR format guidance in its prompt. Validate mirrors M01 exactly (non-LLM adapter.validate() loop). Decide constrains actions to CREATE or SKIP only (no UPDATE since there's no existing rules baseline) and short-circuits on empty proposals (D024).

**T04 — Pipeline graph + runner + output formatters.** ExcelPipelineContext carries llm_client, adapter, aggregated_flows, and subnet_groups. build_excel_pipeline() composes the 5 stages into a linear LangGraph. run_excel_pipeline() aggregates raw records via S02's functions, defaults to NullAdapter, and wraps errors in PipelineError. Refactored M01's private Rich renderers to public (D048) so both pipelines share them. Excel Rich formatter adds a custom summary panel (source type, flow counts, direction breakdown) then delegates to shared renderers.

## Verification

- `pytest tests/test_adapters/test_null_adapter.py -v` — 15 passed (ABC contract, registry integration)
- `pytest tests/test_pipeline/test_excel_summarizer.py -v` — 16 passed (aggregation, ordering, token budget, empty input)
- `pytest tests/test_pipeline/test_excel_stages.py -v` — 27 passed (all 5 stages with mock LLM)
- `pytest tests/test_pipeline/test_excel_pipeline.py -v` — 9 passed (graph compiles, runner e2e, NullAdapter default, error handling)
- `pytest tests/test_output/test_excel_output.py -v` — 15 passed (Rich panels, shared sections, JSON valid, ExcelPipelineResult)
- `npx pyright` on all new/modified files — 0 errors (1 pre-existing langgraph import stub issue, same as M01)
- `pytest tests/ -x -q` — 564 passed, 0 failures (full suite green, up from 482 baseline)

## Requirements Advanced

- R106 — 5-stage LangGraph pipeline built and tested with mock LLM (5 nodes: analyze, assess, generate, validate, decide)
- R107 — Generate and Decide stages produce justification text and risk classification per rule
- R112 — NullAdapter implemented, registered, tested; adapter interface preserved for M003

## Requirements Validated

- R106 — Multi-stage LangGraph pipeline: 5-node graph compiles, all stages compose end-to-end with mock LLM, correct output types at each stage boundary. 9 pipeline integration tests + 27 stage unit tests prove the contract.
- R107 — AI-generated justification and risk: Generate stage produces PolicyProposal with justification field, Decide stage assigns risk classification and action. Verified through mock LLM structured output tests.
- R112 — NullAdapter: implements FirewallAdapter ABC, registered in AdapterRegistry, 15 contract tests pass. Pipeline defaults to NullAdapter when no adapter provided.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Used `runtime: Any` type annotation in stage functions instead of `Runtime[ExcelPipelineContext]` because stages were built before the context dataclass (T02/T03 before T04). T04 created ExcelPipelineContext but the runtime type annotation stays `Any` to match M01's pattern (LangGraph's context typing doesn't enforce this at runtime anyway).
- Fixed pre-existing pyright issues in `PipelineResult.from_state()` (annotated `raw` as `dict[str, Any]`) while applying the same fix for ExcelPipelineResult — not in plan but necessary for clean pyright.

## Known Limitations

- All testing is with mock LLM — real LLM prompt quality is unverified until S05 UAT
- 18 pre-existing pyright errors in src/policyfoundry/ (boto3 stubs, litellm exports, parser IP types, main.py, langgraph import) — none in new code
- Assess stage's inference heuristic ("assume high-volume traffic is already permitted") is prompt-based — accuracy depends on LLM quality

## Follow-ups

- none — S04 (export formatters) and S05 (CLI integration + UAT) are planned next slices

## Files Created/Modified

- `src/policyfoundry/adapters/null.py` — NullAdapter implementing FirewallAdapter ABC (created)
- `src/policyfoundry/adapters/registry.py` — Added null adapter as built-in (modified)
- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState TypedDict (created)
- `src/policyfoundry/pipeline/excel_summarizer.py` — summarize_flows() + format_flow_summary_message() (created)
- `src/policyfoundry/pipeline/excel_stages/__init__.py` — Package init re-exporting all 5 stage functions (created)
- `src/policyfoundry/pipeline/excel_stages/analyze.py` — excel_analyze_stage() (created)
- `src/policyfoundry/pipeline/excel_stages/assess.py` — excel_assess_stage() (created)
- `src/policyfoundry/pipeline/excel_stages/generate.py` — excel_generate_stage() (created)
- `src/policyfoundry/pipeline/excel_stages/validate.py` — excel_validate_proposals() (created)
- `src/policyfoundry/pipeline/excel_stages/decide.py` — excel_decide_stage() (created)
- `src/policyfoundry/pipeline/excel_prompts/__init__.py` — Package init re-exporting all prompts (created)
- `src/policyfoundry/pipeline/excel_prompts/analyze.py` — EXCEL_ANALYZE_SYSTEM_PROMPT + formatter (created)
- `src/policyfoundry/pipeline/excel_prompts/assess.py` — EXCEL_ASSESS_SYSTEM_PROMPT + formatter (created)
- `src/policyfoundry/pipeline/excel_prompts/generate.py` — EXCEL_GENERATE_SYSTEM_PROMPT + formatter (created)
- `src/policyfoundry/pipeline/excel_prompts/decide.py` — EXCEL_DECIDE_SYSTEM_PROMPT + formatter (created)
- `src/policyfoundry/pipeline/excel_graph.py` — ExcelPipelineContext + build_excel_pipeline() (created)
- `src/policyfoundry/pipeline/excel_runner.py` — run_excel_pipeline() async entry point (created)
- `src/policyfoundry/output/rich_output.py` — Refactored renderers from private to public (modified)
- `src/policyfoundry/output/excel_rich_output.py` — format_excel_rich() (created)
- `src/policyfoundry/output/excel_json_output.py` — format_excel_json() (created)
- `src/policyfoundry/output/models.py` — ExcelPipelineResult added (modified)
- `src/policyfoundry/output/__init__.py` — Updated exports (modified)
- `tests/test_adapters/test_null_adapter.py` — 15 tests (created)
- `tests/test_pipeline/test_excel_summarizer.py` — 16 tests (created)
- `tests/test_pipeline/test_excel_stages.py` — 27 tests (created)
- `tests/test_pipeline/test_excel_pipeline.py` — 9 tests (created)
- `tests/test_output/test_excel_output.py` — 15 tests (created)

## Forward Intelligence

### What the next slice should know
- `ExcelPipelineState` is the boundary contract — S04 consumes it for xlsx/pdf export. Key fields: `decisions` (list of RuleDecision dicts), `proposals` (list of PolicyProposal dicts), `analysis`, `assessment`, `token_usage`.
- `run_excel_pipeline()` returns the completed state dict. S05 wires this into the CLI command.
- `format_excel_rich()` and `format_excel_json()` are ready for S05 CLI integration — they accept ExcelPipelineState directly.

### What's fragile
- Prompt quality is untested with real LLMs — the mock LLM returns predetermined structured output. Real model output may not match the Pydantic schemas perfectly, though Instructor handles retries.
- The assess stage's inference heuristic is entirely prompt-driven — poor LLM reasoning could produce bad "likely existing rules" inferences.

### Authoritative diagnostics
- `pytest tests/test_pipeline/test_excel_pipeline.py -v` — proves all stages compose end-to-end
- `format_excel_json(state)` — dumps full pipeline state for inspection at any point
- PipelineError includes stage name where failure occurred

### What assumptions changed
- Pre-summarizer token budget assumed ~3K max — actual output for 600 flows is well under that (verified by test_600_flow_summary_under_3k_tokens).
- Planned `Runtime[ExcelPipelineContext]` type annotation wasn't practical during incremental build — `Any` works and matches M01's actual pattern.
