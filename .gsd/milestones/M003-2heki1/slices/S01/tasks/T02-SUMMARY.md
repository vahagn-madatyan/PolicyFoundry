---
id: T02
parent: S01
milestone: M003-2heki1
provides:
  - Generate prompt accurately describes shared_patterns field names (dst_ip/src_ip, not counterpart_ip)
  - Regression test preventing reintroduction of counterpart_ip in prompt
key_files:
  - src/policyfoundry/pipeline/excel_prompts/generate.py
  - tests/test_pipeline/test_excel_stages.py
key_decisions:
  - Prompt describes both grouping directions explicitly (source-side → dst_ip, destination-side → src_ip) rather than using a generic "counterpart" term
patterns_established:
  - Prompt content regression tests as sync tests importing the constant directly — no LLM mock needed
observability_surfaces:
  - rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/ returns empty — confirms no stale field references
  - TestExcelGeneratePromptContent class in test_excel_stages.py guards prompt field name accuracy
duration: 8m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Fix generate prompt to reference actual shared_patterns field names

**Replaced `counterpart_ip` with accurate `dst_ip`/`src_ip` descriptions in the generate system prompt and added 5 regression tests.**

## What Happened

The generate prompt told the LLM that `shared_patterns` entries contain a `counterpart_ip` key. This key doesn't exist in the data model — `SubnetGroup.shared_patterns` dicts contain either `dst_ip` (for source-side subnet groups) or `src_ip` (for destination-side groups), plus `service_port` and `protocol`.

Replaced the single `counterpart_ip` description with an accurate explanation of both grouping directions:
- Source-side groups: patterns contain `dst_ip` (the common destination they all talk to)
- Destination-side groups: patterns contain `src_ip` (the common source sending to all of them)

Added `TestExcelGeneratePromptContent` class with 5 sync tests that import `EXCEL_GENERATE_SYSTEM_PROMPT` directly and assert field name correctness.

## Verification

- `rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/` — returns no results ✅
- `python3 -m pytest tests/test_pipeline/test_excel_stages.py::TestExcelGeneratePromptContent -v` — 5/5 passed ✅
- `python3 -m pytest tests/test_pipeline/ -v` — 134/134 passed ✅
- `python3 -m pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — 618 passed, zero failures ✅

## Diagnostics

- `rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/` — should always return empty
- `TestExcelGeneratePromptContent` tests guard against future regressions on prompt field names

## Deviations

None — added 5 tests (2 more than planned) to cover both grouping direction descriptions and `service_port`/`protocol` mentions.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/excel_prompts/generate.py` — replaced `counterpart_ip` prompt text with accurate `dst_ip`/`src_ip` descriptions for both grouping directions
- `tests/test_pipeline/test_excel_stages.py` — added `TestExcelGeneratePromptContent` class with 5 prompt content regression tests
- `.gsd/milestones/M003-2heki1/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
