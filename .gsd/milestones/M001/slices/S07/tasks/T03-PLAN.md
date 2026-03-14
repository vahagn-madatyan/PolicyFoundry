# T03: 07-pipeline-core 03

**Slice:** S07 — **Milestone:** M001

## Description

Implement the Decide stage (Stage 4) and create full pipeline integration tests proving the entire 5-stage graph executes end-to-end with mocked dependencies. This plan completes the pipeline core.

Purpose: Delivers the final stage where the LLM assigns risk levels and actions to each proposal, and proves the full pipeline works as a cohesive unit. Integration tests verify the graph wiring, state accumulation, and error handling.

Output: Complete Decide stage, full integration tests, pipeline ready for consumption by Phase 8 (Output) and Phase 9 (CLI).

## Must-Haves

- [ ] "Decide stage processes all validated proposals in a single LLM call with cross-proposal reasoning"
- [ ] "Each decision includes risk_level (LOW/MEDIUM/HIGH/CRITICAL), action (CREATE/UPDATE/SKIP), and approval_required flag"
- [ ] "Full pipeline executes all 5 nodes in order: analyze -> assess -> generate -> validate -> decide"
- [ ] "Pipeline returns completed PipelineState with all stage outputs populated"
- [ ] "Pipeline failure at any stage returns partial results with clear error identifying failed stage"
- [ ] "Pipeline handles empty/sparse data gracefully without crashing"

## Files

- `src/policyfoundry/pipeline/stages/decide.py`
- `src/policyfoundry/pipeline/prompts/decide.py`
- `src/policyfoundry/pipeline/prompts/__init__.py`
- `src/policyfoundry/pipeline/stages/__init__.py`
- `src/policyfoundry/pipeline/__init__.py`
- `tests/test_pipeline/test_stages.py`
- `tests/test_pipeline/test_prompts.py`
- `tests/test_pipeline/test_graph.py`
- `tests/test_pipeline/conftest.py`
