---
estimated_steps: 5
estimated_files: 7
---

# T03: Generate + Validate + Decide Excel Stages with Prompts

**Slice:** S03 — Analysis Pipeline
**Milestone:** M002

## Description

Complete the remaining 3 Excel pipeline stages. Generate creates rule proposals using SubnetGroup candidates. Validate is non-LLM, filtering through adapter.validate() (NullAdapter passes all). Decide assigns final risk levels and actions. Together with T02's stages, these complete the 5-stage pipeline required by R106.

## Steps

1. **Generate prompts** — Create `src/policyfoundry/pipeline/excel_prompts/generate.py` with `EXCEL_GENERATE_SYSTEM_PROMPT` and `format_excel_generate_user_message()`. The prompt must: explain SubnetGroup shared_patterns keys (counterpart_ip, service_port, protocol), include CIDR format examples (e.g., "use 10.1.2.3/32 for individual IPs, 10.1.2.0/24 for subnets"), guide the LLM to prefer subnet rules when 2+ IPs share a pattern, require each proposal to include justification and risk_level (R107). Takes assessment dict, capabilities, analysis dict, and subnet_groups list.

2. **Decide prompts** — Create `src/policyfoundry/pipeline/excel_prompts/decide.py` with `EXCEL_DECIDE_SYSTEM_PROMPT` and `format_excel_decide_user_message()`. Mirror M01's decide prompt with Excel-specific context: "These proposals were generated from a firewall traffic export analysis. There are no existing rules to compare against — all proposals are for new rules (action should be CREATE or SKIP, not UPDATE)." Reuse M01's compact proposal summarization pattern (extract essential fields, truncate justification to 100 chars).

3. **Generate stage** — Create `src/policyfoundry/pipeline/excel_stages/generate.py`. Reads assessment + analysis from state, gets adapter capabilities, gets subnet_groups from context. Formats generate user message with subnet group data. Calls LLM with PolicyProposalList wrapper model, temperature=0.3 (D025). Limits to 20 proposals. Returns `{"proposals": [p.model_dump() for p in proposals], "current_stage": "generate"}`.

4. **Validate + Decide stages** — Create `validate.py` and `decide.py` in `excel_stages/`. Validate mirrors M01 exactly — filters through adapter.validate(), removes invalid proposals (NullAdapter passes all, preserving the seam). Decide mirrors M01 — short-circuits on empty proposals (D024), calls LLM with RuleDecisionList wrapper, temperature=0.1.

5. **Tests for generate + validate + decide** — Add test classes to `tests/test_pipeline/test_excel_stages.py`. Generate: mock LLM returns sample PolicyProposalList, verify correct output shape, verify subnet_groups passed in prompt context. Validate: test that NullAdapter passes all proposals through, test that a failing validation removes proposals. Decide: test with proposals → LLM called with RuleDecisionList, test empty proposals → short-circuit returns []. Verify full stage test file passes all 5 stage test classes.

## Must-Haves

- [ ] Generate prompt includes SubnetGroup patterns and CIDR format constraints
- [ ] Generate stage uses temperature=0.3, analyze/assess/decide use 0.1 (D025)
- [ ] Validate stage mirrors M01 non-LLM pattern exactly
- [ ] Decide stage short-circuits on empty proposals (D024)
- [ ] Decide prompt is Excel-aware (no UPDATE action expected)
- [ ] All 5 stage test classes pass in test_excel_stages.py
- [ ] All code passes pyright strict (src/ scope)

## Verification

- `pytest tests/test_pipeline/test_excel_stages.py -v` — all 5 stage test classes pass
- `npx pyright src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/excel_prompts/` — 0 errors

## Inputs

- `src/policyfoundry/pipeline/excel_stages/analyze.py` — Analyze stage from T02 (pattern reference)
- `src/policyfoundry/pipeline/excel_stages/assess.py` — Assess stage from T02
- `src/policyfoundry/pipeline/stages/generate.py` — M01 generate stage to mirror
- `src/policyfoundry/pipeline/stages/validate.py` — M01 validate stage to mirror
- `src/policyfoundry/pipeline/stages/decide.py` — M01 decide stage to mirror
- `tests/test_pipeline/test_excel_stages.py` — Test file from T02 to extend

## Expected Output

- `src/policyfoundry/pipeline/excel_stages/generate.py` — excel_generate_stage()
- `src/policyfoundry/pipeline/excel_stages/validate.py` — excel_validate_proposals()
- `src/policyfoundry/pipeline/excel_stages/decide.py` — excel_decide_stage()
- `src/policyfoundry/pipeline/excel_prompts/generate.py` — System prompt + user message formatter
- `src/policyfoundry/pipeline/excel_prompts/decide.py` — System prompt + user message formatter
- `tests/test_pipeline/test_excel_stages.py` — Complete with all 5 stage test classes
