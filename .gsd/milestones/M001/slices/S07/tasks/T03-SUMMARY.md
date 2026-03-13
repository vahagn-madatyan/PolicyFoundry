---
id: T03
parent: S07
milestone: M001
provides:
  - decide_stage async node function (Stage 4) with cross-proposal reasoning
  - DECIDE_SYSTEM_PROMPT and format_decide_user_message prompt layer
  - RuleDecisionList wrapper model for LLM structured list output
  - Full pipeline integration tests proving 5-stage end-to-end execution
  - Pipeline __init__.py public API for Phase 8 and 9 consumption
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 7min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---
# T03: 07-pipeline-core 03

**# Phase 7 Plan 3: Decide Stage + Pipeline Integration Tests Summary**

## What Happened

# Phase 7 Plan 3: Decide Stage + Pipeline Integration Tests Summary

**Decide stage with cross-proposal reasoning in single LLM call, token-efficient proposal summarization, and 7 integration tests proving full 5-stage pipeline executes end-to-end**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-11T18:53:54Z
- **Completed:** 2026-03-11T19:01:01Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Implemented Decide stage (Stage 4) processing all proposals in a single LLM call for cross-proposal reasoning (redundancy/conflict detection)
- Created token-efficient prompt that summarizes proposals to essential fields (proposal_id, rule name, direction, protocol, CIDRs, justification summary, risk_level) instead of full JSON
- Built 7 full pipeline integration tests proving 5-stage execution, state accumulation, stage ordering, error handling, and empty data edge cases
- Expanded pipeline test suite from 48 to 62 tests; full project suite at 297 tests all green

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for decide stage and prompts** - `a10df8a` (test)
2. **Task 1 (GREEN): Implement decide stage with prompts** - `d17b04d` (feat)
3. **Task 2: Full pipeline integration tests** - `0393c9b` (test)

_Task 1 followed TDD flow (RED then GREEN). Task 2 tests passed immediately since decide implementation was in place._

## Files Created/Modified
- `src/policyfoundry/pipeline/prompts/decide.py` - DECIDE_SYSTEM_PROMPT + format_decide_user_message() with token-efficient summarization
- `src/policyfoundry/pipeline/stages/decide.py` - decide_stage replacing stub, single LLM call with RuleDecisionList wrapper
- `src/policyfoundry/pipeline/stages/__init__.py` - Added decide_stage export
- `src/policyfoundry/pipeline/prompts/__init__.py` - Added DECIDE_SYSTEM_PROMPT, format_decide_user_message exports
- `tests/test_pipeline/test_graph.py` - 7 integration tests (TestPipelineExecution + TestPipelineErrorHandling)
- `tests/test_pipeline/test_stages.py` - Added TestDecideStage with 4 unit tests
- `tests/test_pipeline/test_prompts.py` - Added TestDecidePrompt with 3 unit tests
- `tests/test_pipeline/conftest.py` - Added sample_rule_decisions fixture (CREATE, UPDATE, SKIP variants)

## Decisions Made
- RuleDecisionList wrapper BaseModel consistent with PolicyProposalList pattern established in Plan 02
- Temperature 0.1 for Decide stage matching Analyze and Assess (precision over creativity for risk decisions)
- format_decide_user_message uses `dict[str, Any]` explicit typing instead of `dict` with `type: ignore` for cleaner pyright compliance
- Empty proposals short-circuit pattern: return early without LLM call when proposals list is empty
- Integration test LLM mock routes responses by response_model type for realistic multi-stage testing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff I001 import sorting on decide.py -- resolved with `ruff check --fix` (same pattern as Plans 01/02)
- Pre-existing pyright errors in assess.py and generate.py (4 errors from `dict[Unknown]` types) confirmed out-of-scope; all new files clean

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 5 pipeline stages implemented and tested: analyze -> assess -> generate -> validate -> decide
- Pipeline __init__.py exports full public API (run_pipeline, PipelineContext, build_pipeline, LLMClient, create_llm_client)
- 62 pipeline tests + 297 total project tests all green
- Pipeline ready for consumption by Phase 8 (Output formatting) and Phase 9 (CLI integration)

## Self-Check: PASSED

All files verified present. All 3 task commits verified in git log.

---
*Phase: 07-pipeline-core*
*Completed: 2026-03-11*
