---
id: T03
parent: S03
milestone: M002
provides:
  - excel_generate_stage() — LLM-driven rule proposal generation with SubnetGroup context
  - excel_validate_proposals() — non-LLM adapter constraint filtering (NullAdapter passes all)
  - excel_decide_stage() — LLM-driven final risk/action decisions with D024 short-circuit
  - Excel-specific generate and decide prompts with CIDR format guidance and no-UPDATE constraint
key_files:
  - src/policyfoundry/pipeline/excel_stages/generate.py
  - src/policyfoundry/pipeline/excel_stages/validate.py
  - src/policyfoundry/pipeline/excel_stages/decide.py
  - src/policyfoundry/pipeline/excel_prompts/generate.py
  - src/policyfoundry/pipeline/excel_prompts/decide.py
  - tests/test_pipeline/test_excel_stages.py
key_decisions:
  - Generate prompt includes SubnetGroup shared_patterns key docs (counterpart_ip, service_port, protocol) and CIDR format examples (/32 for individual IPs, /24 for subnets)
  - Decide prompt constrains action to CREATE or SKIP only (no UPDATE since there are no existing rules in the Excel pipeline)
  - Reused M01's compact proposal summarization pattern in decide user message (extract essential fields, truncate justification to 100 chars)
patterns_established:
  - Excel stages use runtime typed as Any (consistent with T02) — ExcelPipelineContext will tighten this in T04
  - Validate stage mirrors M01 exactly — same adapter.validate() loop pattern preserves the seam for real adapters
observability_surfaces:
  - none — pure LLM-calling stages with no runtime side effects; prompt content inspectable via mock LLM call args in tests
duration: 15min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Generate + Validate + Decide Excel Stages with Prompts

**Built the remaining 3 Excel pipeline stages (generate, validate, decide) with Excel-specific prompts — 27 tests pass across all 5 stage test classes, pyright clean.**

## What Happened

Implemented the generate, validate, and decide stages that complete the 5-stage Excel pipeline (Analyze → Assess → Generate → Validate → Decide).

Generate prompt includes SubnetGroup shared_patterns key documentation and CIDR format guidance (prefer /24 subnet rules when 2+ IPs share a pattern). The stage reads assessment, analysis, and subnet_groups from state, passes all four data sections to the LLM with temperature=0.3 (D025), and caps output at 20 proposals.

Validate mirrors M01's non-LLM pattern exactly — loops through proposals calling adapter.validate(), filtering invalid ones. NullAdapter passes all, preserving the seam.

Decide prompt is Excel-aware: constrains actions to CREATE or SKIP (no UPDATE since no existing rules exist). Short-circuits on empty proposals (D024). Uses M01's compact proposal summarization (extract essential fields, truncate justification to 100 chars).

## Verification

- `pytest tests/test_pipeline/test_excel_stages.py -v` — 27 passed (7 analyze + 8 assess + 5 generate + 3 validate + 4 decide)
- `npx pyright src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/excel_prompts/` — 0 errors
- `pytest tests/ -x -q` — 540 passed, 0 failures

### Slice-level verification status (intermediate — T03 of 5):
- ✅ `pytest tests/test_adapters/test_null_adapter.py -v` — passes
- ✅ `pytest tests/test_pipeline/test_excel_summarizer.py -v` — passes
- ✅ `pytest tests/test_pipeline/test_excel_stages.py -v` — all 5 stage classes pass
- ⬜ `pytest tests/test_pipeline/test_excel_pipeline.py -v` — not yet created (T04)
- ⬜ `pytest tests/test_output/test_excel_output.py -v` — not yet created (T05)
- ✅ `npx pyright src/policyfoundry/` — 0 errors
- ✅ `pytest tests/ -x -q` — 540 passed

## Diagnostics

None — these are pure LLM-calling stages with no runtime side effects. Prompt content can be inspected by examining mock LLM call args in tests.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_prompts/generate.py` — Generate system prompt + user message formatter with SubnetGroup/CIDR context
- `src/policyfoundry/pipeline/excel_prompts/decide.py` — Decide system prompt (CREATE/SKIP only) + compact proposal summarizer
- `src/policyfoundry/pipeline/excel_prompts/__init__.py` — Updated exports
- `src/policyfoundry/pipeline/excel_stages/generate.py` — excel_generate_stage() with temp=0.3, 20 proposal cap
- `src/policyfoundry/pipeline/excel_stages/validate.py` — excel_validate_proposals() mirroring M01 pattern
- `src/policyfoundry/pipeline/excel_stages/decide.py` — excel_decide_stage() with D024 short-circuit
- `src/policyfoundry/pipeline/excel_stages/__init__.py` — Updated exports
- `tests/test_pipeline/test_excel_stages.py` — Extended with 3 new test classes (12 new tests)
