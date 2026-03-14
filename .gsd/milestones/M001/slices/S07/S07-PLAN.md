# S07: Pipeline Core

**Goal:** Install LangGraph, define the StateGraph skeleton with PipelineContext dependency injection, implement the Analyze stage (Stage 1), and create the pipeline runner with partial-result error handling.
**Demo:** Install LangGraph, define the StateGraph skeleton with PipelineContext dependency injection, implement the Analyze stage (Stage 1), and create the pipeline runner with partial-result error handling.

## Must-Haves


## Tasks

- [x] **T01: 07-pipeline-core 01** `est:10min`
  - Install LangGraph, define the StateGraph skeleton with PipelineContext dependency injection, implement the Analyze stage (Stage 1), and create the pipeline runner with partial-result error handling.

Purpose: Establishes the pipeline framework and delivers the first working stage. The graph definition with stub edges enables Plan 02 to implement remaining stages against a known contract. The runner provides the error-handling shell all stages execute within.

Output: Compiled LangGraph StateGraph, working Analyze stage, pipeline runner, test scaffolds for stage and prompt testing.
- [x] **T02: 07-pipeline-core 02** `est:11min`
  - Implement Assess (Stage 2), Generate (Stage 3), and Validate (adapter filtering step) replacing the stubs created in Plan 01. These three stages form the analysis-to-proposal pipeline: Assess identifies gaps between traffic and rules, Generate creates proposals, and Validate filters out invalid proposals before the Decide stage.

Purpose: Delivers the middle of the pipeline where the core intelligence lives -- comparing traffic to rules, generating proposals with justification, and ensuring proposals are valid before decision-making.

Output: Three fully implemented stage modules with prompts and tests.
- [x] **T03: 07-pipeline-core 03** `est:7min`
  - Implement the Decide stage (Stage 4) and create full pipeline integration tests proving the entire 5-stage graph executes end-to-end with mocked dependencies. This plan completes the pipeline core.

Purpose: Delivers the final stage where the LLM assigns risk levels and actions to each proposal, and proves the full pipeline works as a cohesive unit. Integration tests verify the graph wiring, state accumulation, and error handling.

Output: Complete Decide stage, full integration tests, pipeline ready for consumption by Phase 8 (Output) and Phase 9 (CLI).

## Files Likely Touched

- `pyproject.toml`
- `src/policyfoundry/pipeline/graph.py`
- `src/policyfoundry/pipeline/runner.py`
- `src/policyfoundry/pipeline/stages/analyze.py`
- `src/policyfoundry/pipeline/prompts/analyze.py`
- `tests/test_pipeline/conftest.py`
- `tests/test_pipeline/test_stages.py`
- `tests/test_pipeline/test_prompts.py`
- `src/policyfoundry/pipeline/stages/assess.py`
- `src/policyfoundry/pipeline/stages/generate.py`
- `src/policyfoundry/pipeline/stages/validate.py`
- `src/policyfoundry/pipeline/prompts/assess.py`
- `src/policyfoundry/pipeline/prompts/generate.py`
- `src/policyfoundry/pipeline/prompts/__init__.py`
- `src/policyfoundry/pipeline/stages/__init__.py`
- `src/policyfoundry/pipeline/stages/decide.py`
- `src/policyfoundry/pipeline/prompts/decide.py`
- `src/policyfoundry/pipeline/prompts/__init__.py`
- `src/policyfoundry/pipeline/stages/__init__.py`
- `src/policyfoundry/pipeline/__init__.py`
- `tests/test_pipeline/test_stages.py`
- `tests/test_pipeline/test_prompts.py`
- `tests/test_pipeline/test_graph.py`
- `tests/test_pipeline/conftest.py`
