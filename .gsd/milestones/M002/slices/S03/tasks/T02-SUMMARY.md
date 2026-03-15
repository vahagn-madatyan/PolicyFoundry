---
id: T02
parent: S03
milestone: M002
provides:
  - excel_analyze_stage() — pre-summarizer-driven traffic analysis from Excel data
  - excel_assess_stage() — inference-based security assessment for empty-rules mode
  - Excel-specific system prompts and user message formatters for both stages
key_files:
  - src/policyfoundry/pipeline/excel_stages/analyze.py
  - src/policyfoundry/pipeline/excel_stages/assess.py
  - src/policyfoundry/pipeline/excel_prompts/analyze.py
  - src/policyfoundry/pipeline/excel_prompts/assess.py
  - tests/test_pipeline/test_excel_stages.py
key_decisions:
  - Assess stage appends compact flow summary as additional context beyond analysis dict — gives LLM raw traffic signals for rule inference when rules are empty
  - Runtime type for stage functions is `Any` (not `Runtime[ExcelPipelineContext]`) since ExcelPipelineContext is not yet defined — T04 will create context dataclass and tighten
patterns_established:
  - Excel stages reconstruct domain models (AggregatedFlow, SubnetGroup) from state dicts before calling summarizer
  - Assess stage builds composite user message (JSON analysis + flow summary text) rather than single JSON blob
observability_surfaces:
  - none — pure LLM-calling stages with no runtime side effects beyond state mutations
duration: 20m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Analyze + Assess Excel Stages with Prompts

**Built excel_analyze_stage and excel_assess_stage with Excel-specific prompts — 15 tests pass, pyright clean.**

## What Happened

Created the two highest-risk Excel pipeline stages. The analyze stage reads aggregated flows from state, runs them through the pre-summarizer (T01), and passes compact stats to the LLM with a system prompt oriented to firewall traffic exports (not VPC flow logs). The assess stage is the most novel: with NullAdapter returning empty rules, the system prompt explicitly instructs the LLM to infer likely existing rules from traffic patterns — high-volume well-known ports are probably already permitted, focus on gaps.

Both stages mirror M01's async signature (`async def stage(state, runtime) -> dict[str, Any]`) and return the same output shape (`{"analysis": ..., "current_stage": "analyze"}` / `{"assessment": ..., "current_stage": "assess"}`). DirectionLabel.UNKNOWN flows appear in both the analyze summary and the assess flow context.

## Verification

- `pytest tests/test_pipeline/test_excel_stages.py -v -k "analyze or assess"` — **15 passed** (7 analyze + 8 assess)
- `npx pyright src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/excel_prompts/` — **0 errors, 0 warnings**
- `pytest tests/ -x -q` — **528 passed**, 0 failures (full suite including all T01 + T02 tests)

### Slice-level checks status (intermediate — T02 of T04):
- ✅ `pytest tests/test_adapters/test_null_adapter.py -v` — 15 passed
- ✅ `pytest tests/test_pipeline/test_excel_summarizer.py -v` — 16 passed
- ✅ `pytest tests/test_pipeline/test_excel_stages.py -v` — 15 passed (partial — T03 adds remaining stages)
- ⬜ `pytest tests/test_pipeline/test_excel_pipeline.py -v` — not yet created (T04)
- ⬜ `pytest tests/test_output/test_excel_output.py -v` — not yet created (T04)
- ✅ `npx pyright` on new code — 0 errors
- ✅ `pytest tests/ -x -q` — 528 passed

## Diagnostics

None — these are pure LLM-calling stages with no runtime side effects. Prompt content can be inspected by examining the mock LLM call args in tests.

## Deviations

- Used `runtime: Any` type annotation instead of `Runtime[ExcelPipelineContext]` since ExcelPipelineContext dataclass doesn't exist yet (T04 creates it). This keeps pyright clean now; T04 will tighten the type.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_prompts/__init__.py` — Package init re-exporting system prompts
- `src/policyfoundry/pipeline/excel_prompts/analyze.py` — EXCEL_ANALYZE_SYSTEM_PROMPT + format_excel_analyze_user_message()
- `src/policyfoundry/pipeline/excel_prompts/assess.py` — EXCEL_ASSESS_SYSTEM_PROMPT + format_excel_assess_user_message()
- `src/policyfoundry/pipeline/excel_stages/__init__.py` — Package init re-exporting stage functions
- `src/policyfoundry/pipeline/excel_stages/analyze.py` — excel_analyze_stage() with pre-summarizer integration
- `src/policyfoundry/pipeline/excel_stages/assess.py` — excel_assess_stage() with rule inference prompting
- `tests/test_pipeline/test_excel_stages.py` — 15 tests covering both stages (T03 adds remaining)
