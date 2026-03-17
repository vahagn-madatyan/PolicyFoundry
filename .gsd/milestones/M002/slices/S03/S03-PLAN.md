# S03: Analysis Pipeline

**Goal:** Full LangGraph pipeline (Analyze → Assess → Generate → Validate → Decide) produces risk-scored FW rule proposals with AI-generated justifications from Excel traffic data, displayed as Rich terminal report with token usage footer.
**Demo:** `run_excel_pipeline()` with mocked LLM produces an `ExcelPipelineState` containing analysis, assessment, proposals, and decisions — rendered as Rich terminal output and serializable as JSON. NullAdapter handles no-FW mode.

## Must-Haves

- NullAdapter implements FirewallAdapter ABC: `get_rules() → []`, `validate() → valid`, generic capabilities
- Pre-summarizer computes compact statistics from AggregatedFlow list (~2-3K tokens, not ~40K of raw flows)
- ExcelPipelineState TypedDict with aggregated_flows, analysis, assessment, proposals, decisions, token_usage
- ExcelPipelineContext dataclass carrying llm_client, adapter, aggregated_flows, subnet_groups
- build_excel_pipeline() creates a 5-node linear LangGraph: Analyze → Assess → Generate → Validate → Decide
- run_excel_pipeline() creates context (defaulting to NullAdapter), invokes graph, wraps errors
- Analyze stage pre-summarizes flows in Python, calls LLM → TrafficAnalysis
- Assess stage handles NullAdapter (empty rules) by inferring likely existing rules from traffic patterns → SecurityAssessment
- Generate stage uses SubnetGroup candidates to inform rule proposals → PolicyProposalList
- Validate stage is non-LLM, filters through adapter.validate() (NullAdapter passes all)
- Decide stage reviews proposals, assigns risk/action, detects redundancy → RuleDecisionList
- Each proposed rule includes AI-generated business justification and risk classification (R107)
- Rich output formatter renders ExcelPipelineState with shared section renderers
- JSON output formatter serializes ExcelPipelineState via ExcelPipelineResult
- Reuses M01 schema models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision) — same output shape
- All code passes pyright strict (src/ scope per D001)

## Proof Level

- This slice proves: contract + integration (pipeline stages compose via LangGraph, output renders correctly)
- Real runtime required: no (mocked LLM — real LLM integration is S05 UAT)
- Human/UAT required: no (S05 UAT covers live verification)

## Verification

- `pytest tests/test_adapters/test_null_adapter.py -v` — NullAdapter satisfies FirewallAdapter ABC contract
- `pytest tests/test_pipeline/test_excel_summarizer.py -v` — Pre-summarization produces compact stats within token budget
- `pytest tests/test_pipeline/test_excel_stages.py -v` — All 5 stages work with mock LLM, correct output types
- `pytest tests/test_pipeline/test_excel_pipeline.py -v` — Full graph compiles, runner executes end-to-end with mock LLM
- `pytest tests/test_output/test_excel_output.py -v` — Rich and JSON formatters render ExcelPipelineState correctly
- `npx pyright src/policyfoundry/` — 0 errors, 0 warnings on all new code
- `pytest tests/ -x -q` — Full suite passes (482 baseline + new tests, 0 failures)

## Observability / Diagnostics

- Runtime signals: Token usage tracked per-stage via LLMClient (reuses M01 infrastructure)
- Inspection surfaces: `format_excel_json()` exposes full pipeline state as JSON; `ExcelPipelineResult.from_state()` for programmatic access
- Failure visibility: PipelineError with stage name, error_code, and chained exception details
- Redaction constraints: none (no secrets in pipeline data)

## Integration Closure

- Upstream surfaces consumed: `AggregatedFlow`, `SubnetGroup` from `analysis/models.py` (S02); `FirewallAdapter` ABC from `adapters/base.py`; `LLMClient` from `pipeline/llm.py`; `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision` from `pipeline/schema.py`
- New wiring introduced: `build_excel_pipeline()` graph, `run_excel_pipeline()` entry point, `NullAdapter`, `format_excel_rich()`, `format_excel_json()`
- What remains before the milestone is truly usable end-to-end: S04 (export formatters for xlsx/pdf), S05 (CLI wiring + integration tests)

## Tasks

- [x] **T01: NullAdapter + Pre-summarizer + Excel Pipeline State** `est:40m`
  - Why: Foundation pieces — NullAdapter satisfies R112, pre-summarizer solves the context window risk (40K→2-3K tokens), ExcelPipelineState defines the S03→S04 boundary contract
  - Files: `src/policyfoundry/adapters/null.py`, `src/policyfoundry/pipeline/excel_state.py`, `src/policyfoundry/pipeline/excel_summarizer.py`, `tests/test_adapters/test_null_adapter.py`, `tests/test_pipeline/test_excel_summarizer.py`
  - Do: NullAdapter returns empty rules, valid validation, generic capabilities. Pre-summarizer computes total flows, direction breakdown, top talkers by flow count, port distribution, subnet grouping summary from `list[AggregatedFlow]` + `list[SubnetGroup]`. ExcelPipelineState TypedDict with all optional fields.
  - Verify: `pytest tests/test_adapters/test_null_adapter.py tests/test_pipeline/test_excel_summarizer.py -v && npx pyright src/policyfoundry/adapters/null.py src/policyfoundry/pipeline/excel_state.py src/policyfoundry/pipeline/excel_summarizer.py`
  - Done when: NullAdapter passes ABC contract tests, pre-summarizer output is under 3K tokens for 600 flows, pyright clean

- [x] **T02: Analyze + Assess Excel Stages with Prompts** `est:50m`
  - Why: The two novel stages — analyze needs pre-summarized data instead of DuckDB, assess must infer likely existing rules from traffic patterns instead of comparing against adapter.get_rules() results. These are the highest-risk prompts.
  - Files: `src/policyfoundry/pipeline/excel_stages/__init__.py`, `src/policyfoundry/pipeline/excel_stages/analyze.py`, `src/policyfoundry/pipeline/excel_stages/assess.py`, `src/policyfoundry/pipeline/excel_prompts/__init__.py`, `src/policyfoundry/pipeline/excel_prompts/analyze.py`, `src/policyfoundry/pipeline/excel_prompts/assess.py`, `tests/test_pipeline/test_excel_stages.py`
  - Do: Mirror M01 stage signature `async def stage(state, runtime) -> dict[str, Any]`. Analyze calls pre-summarizer then LLM. Assess prompt must explicitly guide: "assume high-volume traffic on well-known ports is already permitted." Handle DirectionLabel.UNKNOWN gracefully. Include CIDR format examples in prompts.
  - Verify: `pytest tests/test_pipeline/test_excel_stages.py -v -k "analyze or assess" && npx pyright src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/excel_prompts/`
  - Done when: Both stages produce correct output types from mock LLM, prompts stay under 3K input tokens, pyright clean

- [x] **T03: Generate + Validate + Decide Excel Stages with Prompts** `est:40m`
  - Why: Complete the 5-stage pipeline. Generate uses SubnetGroup candidates for rule proposals, validate is non-LLM (NullAdapter passes all), decide mirrors M01 with cross-proposal reasoning.
  - Files: `src/policyfoundry/pipeline/excel_stages/generate.py`, `src/policyfoundry/pipeline/excel_stages/validate.py`, `src/policyfoundry/pipeline/excel_stages/decide.py`, `src/policyfoundry/pipeline/excel_prompts/generate.py`, `src/policyfoundry/pipeline/excel_prompts/decide.py`, `tests/test_pipeline/test_excel_stages.py`
  - Do: Generate prompt includes SubnetGroup patterns and CIDR format constraints. Validate mirrors M01 exactly. Decide prompt includes Excel-specific context (no existing rules baseline). Short-circuit on empty proposals (D024).
  - Verify: `pytest tests/test_pipeline/test_excel_stages.py -v && npx pyright src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/excel_prompts/`
  - Done when: All 5 stages pass unit tests with mock LLM, validate passes all NullAdapter proposals, decide handles empty proposals, pyright clean

- [x] **T04: Pipeline Graph + Runner + Output Formatters** `est:50m`
  - Why: Wire everything together — graph composes stages, runner is the async entry point, output formatters close the slice demo. Extract shared Rich renderers from M01 so both pipelines reuse them.
  - Files: `src/policyfoundry/pipeline/excel_graph.py`, `src/policyfoundry/pipeline/excel_runner.py`, `src/policyfoundry/output/excel_rich_output.py`, `src/policyfoundry/output/excel_json_output.py`, `src/policyfoundry/output/rich_output.py`, `src/policyfoundry/output/models.py`, `tests/test_pipeline/test_excel_pipeline.py`, `tests/test_output/test_excel_output.py`
  - Do: Graph mirrors M01's build_pipeline(). Runner defaults adapter to NullAdapter, creates ExcelPipelineContext with aggregated_flows + subnet_groups. Refactor M01 section renderers to public (remove underscore prefix). Excel Rich formatter composes: custom Excel summary panel + shared section renderers. ExcelPipelineResult wraps ExcelPipelineState for JSON serialization. Full pipeline integration test with mock LLM proving all stages compose.
  - Verify: `pytest tests/test_pipeline/test_excel_pipeline.py tests/test_output/test_excel_output.py -v && pytest tests/test_output/ -v && npx pyright src/policyfoundry/pipeline/excel_graph.py src/policyfoundry/pipeline/excel_runner.py src/policyfoundry/output/ && pytest tests/ -x -q`
  - Done when: Full pipeline produces valid ExcelPipelineState from mock LLM, Rich output renders without errors, JSON output is valid, M01 output tests still pass after refactor, full suite green

## Files Likely Touched

- `src/policyfoundry/adapters/null.py`
- `src/policyfoundry/pipeline/excel_state.py`
- `src/policyfoundry/pipeline/excel_summarizer.py`
- `src/policyfoundry/pipeline/excel_graph.py`
- `src/policyfoundry/pipeline/excel_runner.py`
- `src/policyfoundry/pipeline/excel_stages/__init__.py`
- `src/policyfoundry/pipeline/excel_stages/analyze.py`
- `src/policyfoundry/pipeline/excel_stages/assess.py`
- `src/policyfoundry/pipeline/excel_stages/generate.py`
- `src/policyfoundry/pipeline/excel_stages/validate.py`
- `src/policyfoundry/pipeline/excel_stages/decide.py`
- `src/policyfoundry/pipeline/excel_prompts/__init__.py`
- `src/policyfoundry/pipeline/excel_prompts/analyze.py`
- `src/policyfoundry/pipeline/excel_prompts/assess.py`
- `src/policyfoundry/pipeline/excel_prompts/generate.py`
- `src/policyfoundry/pipeline/excel_prompts/decide.py`
- `src/policyfoundry/output/rich_output.py`
- `src/policyfoundry/output/models.py`
- `src/policyfoundry/output/excel_rich_output.py`
- `src/policyfoundry/output/excel_json_output.py`
- `tests/test_adapters/test_null_adapter.py`
- `tests/test_pipeline/test_excel_summarizer.py`
- `tests/test_pipeline/test_excel_stages.py`
- `tests/test_pipeline/test_excel_pipeline.py`
- `tests/test_output/test_excel_output.py`
