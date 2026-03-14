---
id: T02
parent: S07
milestone: M001
provides:
  - assess_stage async node function (Stage 2) reading TrafficAnalysis + SG rules
  - generate_stage async node function (Stage 3) producing up to 20 PolicyProposals
  - validate_proposals non-LLM filtering step via adapter.validate()
  - ASSESS_SYSTEM_PROMPT and format_assess_user_message prompt layer
  - GENERATE_SYSTEM_PROMPT and format_generate_user_message prompt layer
  - PolicyProposalList wrapper model for LLM structured list output
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 11min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---
# T02: 07-pipeline-core 02

**# Phase 7 Plan 2: Assess, Generate, and Validate Stages Summary**

## What Happened

# Phase 7 Plan 2: Assess, Generate, and Validate Stages Summary

**Assess stage comparing traffic to SG rules for gap analysis, Generate stage producing up to 20 vendor-neutral PolicyProposals with adapter capabilities, and non-LLM Validate step filtering invalid proposals through adapter.validate()**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-11T18:37:03Z
- **Completed:** 2026-03-11T18:48:09Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Implemented Assess stage (Stage 2) reading TrafficAnalysis from state and full SG rules from adapter, calling LLM with SecurityAssessment response model for gap analysis
- Implemented Generate stage (Stage 3) reading SecurityAssessment and adapter capabilities, producing up to 20 vendor-neutral PolicyProposals with impact_analysis
- Implemented Validate step (non-LLM) filtering proposals through adapter.validate() before Decide, passing current_rule_count for quota awareness
- Created comprehensive prompt templates with structured JSON formatting for both Assess and Generate stages
- Expanded test suite from 29 to 48 pipeline tests covering all three new stages

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for assess/generate stages and prompts** - `6dc01e0` (test)
2. **Task 1 (GREEN): Implement assess and generate stages with prompts** - `c7e5f8a` (feat)
3. **Task 2 (RED): Failing tests for validate_proposals step** - `93d701b` (test)
4. **Task 2 (GREEN): Implement validate_proposals with adapter filtering** - `45b983e` (feat)

_Both tasks followed TDD flow (RED then GREEN)._

## Files Created/Modified
- `src/policyfoundry/pipeline/prompts/assess.py` - ASSESS_SYSTEM_PROMPT + format_assess_user_message() for gap analysis
- `src/policyfoundry/pipeline/prompts/generate.py` - GENERATE_SYSTEM_PROMPT + format_generate_user_message() with adapter constraints
- `src/policyfoundry/pipeline/stages/assess.py` - Assess stage replacing stub, reads analysis + rules, calls LLM
- `src/policyfoundry/pipeline/stages/generate.py` - Generate stage replacing stub, reads assessment + capabilities, caps at 20
- `src/policyfoundry/pipeline/stages/validate.py` - Validate step replacing stub, filters via adapter.validate()
- `src/policyfoundry/pipeline/stages/__init__.py` - Added assess_stage, generate_stage, validate_proposals exports
- `src/policyfoundry/pipeline/prompts/__init__.py` - Added assess and generate prompt exports
- `tests/test_pipeline/test_stages.py` - Added TestAssessStage (4), TestGenerateStage (4), TestValidateProposals (5) test classes
- `tests/test_pipeline/test_prompts.py` - Added TestAssessPrompt (3), TestGeneratePrompt (3) test classes
- `tests/test_pipeline/conftest.py` - Added sample_universal_rules, sample_traffic_analysis_dict, sample_policy_proposals fixtures

## Decisions Made
- Used PolicyProposalList wrapper BaseModel because Instructor/LLM structured output needs a single response_model, and we need a list of proposals
- Temperature 0.3 for Generate stage (more creative than Assess's 0.1, since proposal generation benefits from diversity)
- Validate step is non-LLM by design -- saves tokens and prevents the Decide stage from reasoning about impossible rules
- Adapter capabilities serialized as "adapter_constraints" key in generate prompt so LLM sees limits clearly
- Targeted pyright type: ignore for PipelineState dict field access (consistent with Plan 01 pattern)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff TC001 flagged PolicyProposal import in generate.py as type-only, but it is needed at runtime for Pydantic model field resolution -- resolved with noqa: TC001 comment
- Ruff I001 import sorting triggered by noqa comment placement -- resolved with ruff --fix

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Three of five pipeline stages now implemented (Analyze, Assess, Generate) plus Validate filter step
- Only Decide stage remains as stub -- Plan 03 target
- All stage patterns established: prompt/stage separation, partial dict return, Runtime DI
- Full test infrastructure with mock fixtures for LLM, adapter, and state data

## Self-Check: PASSED

All files verified present. All 4 task commits verified in git log.

---
*Phase: 07-pipeline-core*
*Completed: 2026-03-11*
