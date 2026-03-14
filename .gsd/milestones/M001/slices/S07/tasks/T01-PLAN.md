# T01: 07-pipeline-core 01

**Slice:** S07 — **Milestone:** M001

## Description

Install LangGraph, define the StateGraph skeleton with PipelineContext dependency injection, implement the Analyze stage (Stage 1), and create the pipeline runner with partial-result error handling.

Purpose: Establishes the pipeline framework and delivers the first working stage. The graph definition with stub edges enables Plan 02 to implement remaining stages against a known contract. The runner provides the error-handling shell all stages execute within.

Output: Compiled LangGraph StateGraph, working Analyze stage, pipeline runner, test scaffolds for stage and prompt testing.

## Must-Haves

- [ ] "Pipeline framework compiles and can be invoked as a 5-stage linear graph"
- [ ] "Pipeline context provides LLM, adapter, and data_dir to all stages via dependency injection"
- [ ] "Analyze stage produces a structured traffic analysis from pre-aggregated DuckDB statistics"
- [ ] "Analyze stage consumes all 4 DuckDB query results and formats them as JSON for the LLM"
- [ ] "Pipeline runner catches stage failures and surfaces clear error with failed stage identity"
- [ ] "Empty or sparse data does not crash the analyze stage"

## Files

- `pyproject.toml`
- `src/policyfoundry/pipeline/graph.py`
- `src/policyfoundry/pipeline/runner.py`
- `src/policyfoundry/pipeline/stages/analyze.py`
- `src/policyfoundry/pipeline/prompts/analyze.py`
- `tests/test_pipeline/conftest.py`
- `tests/test_pipeline/test_stages.py`
- `tests/test_pipeline/test_prompts.py`
