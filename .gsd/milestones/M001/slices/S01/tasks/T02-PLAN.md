# T02: 01-project-foundation 02

**Slice:** S01 — **Milestone:** M001

## Description

Implement the pipeline LLM output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision), the PipelineState TypedDict, and the complete exception hierarchy with tests for all three.

Purpose: These are the remaining domain types that every pipeline phase (6, 7, 8) depends on. The exception hierarchy provides structured error handling for all subsequent phases. Completing this plan means Phase 1's foundation is fully in place.
Output: All domain models defined, all exceptions importable, all Phase 1 success criteria met.

## Must-Haves

- [ ] "TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision can all be instantiated with valid data"
- [ ] "LLM output models reject invalid data (negative counts, out-of-range confidence, missing required fields)"
- [ ] "PolicyProposal contains a nested UniversalRule (cross-module import works)"
- [ ] "PipelineState TypedDict stores flow_log_path as a string, not raw log data"
- [ ] "PipelineState can be instantiated as a plain dict conforming to the TypedDict shape"
- [ ] "All 7 exception classes are importable from policyfoundry.exceptions"
- [ ] "PolicyFoundryError carries optional error_code and details dict"
- [ ] "Exception hierarchy: ConfigError -> PolicyFoundryError, ConfigFileNotFound -> ConfigError, etc."

## Files

- `src/policyfoundry/pipeline/schema.py`
- `src/policyfoundry/pipeline/state.py`
- `src/policyfoundry/exceptions.py`
- `tests/test_models/test_pipeline_schema.py`
- `tests/test_models/test_pipeline_state.py`
- `tests/test_exceptions/__init__.py`
- `tests/test_exceptions/test_exceptions.py`
