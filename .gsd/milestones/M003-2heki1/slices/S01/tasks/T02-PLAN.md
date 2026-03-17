---
estimated_steps: 3
estimated_files: 2
---

# T02: Fix generate prompt to reference actual shared_patterns field names

**Slice:** S01 — Pipeline Correctness & Observability
**Milestone:** M003-2heki1

## Description

The generate prompt in `src/policyfoundry/pipeline/excel_prompts/generate.py` (lines 18-22) tells the LLM that `shared_patterns` contains a `counterpart_ip` key. This key doesn't exist — the actual keys are `dst_ip` (for source-side subnet groups) and `src_ip` (for destination-side subnet groups), along with `service_port` and `protocol`. This mismatch causes the LLM to hallucinate or misinterpret subnet data.

## Steps

1. **Read the prompt file**: `src/policyfoundry/pipeline/excel_prompts/generate.py`. Find the section describing `shared_patterns` (around lines 18-22). Understand how `counterpart_ip` is referenced.

2. **Read the data model**: `src/policyfoundry/analysis/models.py` to confirm the actual `SubnetGroup` / `shared_patterns` field names. The research found the keys are `dst_ip`, `src_ip`, `service_port`, and `protocol`. Both `dst_ip` and `src_ip` can appear in the same list of subnet groups because:
   - When grouping by source IP → shared patterns include `dst_ip` (the destination IPs they share)
   - When grouping by destination IP → shared patterns include `src_ip` (the source IPs they share)
   The prompt must describe BOTH variants accurately.

3. **Fix the prompt text**: Replace the `counterpart_ip` reference with accurate description of `dst_ip`/`src_ip`. The prompt should explain that each subnet group's `shared_patterns` dict contains either `dst_ip` or `src_ip` (depending on grouping direction), plus `service_port` and `protocol`. Add a **test** in `tests/test_pipeline/test_excel_stages.py` (or a new dedicated test file) that:
   - Imports or constructs the system prompt string from the generate prompt module
   - Asserts `"dst_ip"` is in the prompt text
   - Asserts `"src_ip"` is in the prompt text
   - Asserts `"counterpart_ip"` is NOT in the prompt text

## Must-Haves

- [ ] Prompt text references `dst_ip` and `src_ip` (not `counterpart_ip`)
- [ ] Prompt accurately describes both grouping directions
- [ ] Test asserts prompt contains correct field names and does not contain `counterpart_ip`

## Verification

- `python3 -m pytest tests/test_pipeline/ -v` — all tests pass including new prompt content test
- `rg 'counterpart_ip' src/policyfoundry/pipeline/excel_prompts/` — returns no results

## Inputs

- `src/policyfoundry/pipeline/excel_prompts/generate.py` — the prompt file to fix
- `src/policyfoundry/analysis/models.py` — data model confirming actual field names (`dst_ip`, `src_ip`, `service_port`, `protocol`)
- T01 completed — stage files have been edited but this task's changes are in a different file (`excel_prompts/generate.py`)

## Expected Output

- `src/policyfoundry/pipeline/excel_prompts/generate.py` — prompt text accurately describes `dst_ip`/`src_ip` field names
- Test file updated — new test asserting prompt content correctness
