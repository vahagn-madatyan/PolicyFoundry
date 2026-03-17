---
estimated_steps: 5
estimated_files: 8
---

# T02: Analyze + Assess Excel Stages with Prompts

**Slice:** S03 — Analysis Pipeline
**Milestone:** M002

## Description

Build the two most novel Excel pipeline stages: Analyze (summarizes traffic from pre-computed stats instead of DuckDB) and Assess (infers likely existing rules from traffic patterns instead of comparing against real FW rules). These are the highest-risk prompts because they must produce quality output with NullAdapter returning empty rules.

## Steps

1. **Excel prompts package** — Create `src/policyfoundry/pipeline/excel_prompts/__init__.py`. Create `analyze.py` with `EXCEL_ANALYZE_SYSTEM_PROMPT` and `format_excel_analyze_user_message()` that takes the pre-summarizer output dict. The system prompt should orient the LLM: "You are analyzing traffic from a firewall traffic export (not VPC flow logs). Direction inference and subnet grouping have already been performed. Focus on traffic patterns, top talkers, port distribution, and anomalies." Include the UNKNOWN direction note.

2. **Assess prompts** — Create `src/policyfoundry/pipeline/excel_prompts/assess.py` with `EXCEL_ASSESS_SYSTEM_PROMPT` and `format_excel_assess_user_message()`. This is the most novel prompt: with NullAdapter returning empty rules, the LLM must infer likely existing rules from traffic patterns. System prompt guidance: "No existing firewall rules are available for comparison. Infer likely existing rules: high-volume traffic on well-known ports (443, 80, 53, 22) is likely already permitted. Focus on identifying gaps — traffic that is probably NOT covered by existing rules and would need new rules." Include analysis dict and adapter rules (empty list).

3. **Excel stages package** — Create `src/policyfoundry/pipeline/excel_stages/__init__.py`. Create `analyze.py` mirroring M01 stage signature: `async def excel_analyze_stage(state: ExcelPipelineState, runtime: Runtime[ExcelPipelineContext]) -> dict[str, Any]`. Reads aggregated_flows + subnet_groups from context, calls `summarize_flows()` to get compact stats, formats user message, calls `llm_client.complete(messages, TrafficAnalysis, temperature=0.1)`. Returns `{"analysis": analysis.model_dump(), "current_stage": "analyze"}`.

4. **Assess stage** — Create `src/policyfoundry/pipeline/excel_stages/assess.py`. Reads analysis from state, fetches rules from adapter (empty with NullAdapter), formats assess prompt including flow summary for context. Calls `llm_client.complete(messages, SecurityAssessment, temperature=0.1)`. Returns `{"assessment": assessment.model_dump(), "current_stage": "assess"}`.

5. **Tests for analyze + assess** — Add to `tests/test_pipeline/test_excel_stages.py`. For each stage: mock LLM to return sample TrafficAnalysis / SecurityAssessment, verify stage returns correct dict shape, verify LLM was called with correct model and temperature, verify prompts include expected context (summarized flows for analyze, empty rules mention for assess). Create an ExcelPipelineContext fixture with mock deps. Include test that verify UNKNOWN direction flows appear in the summarizer output passed to analyze.

## Must-Haves

- [ ] Analyze stage calls pre-summarizer, not raw flow serialization
- [ ] Analyze prompt explicitly mentions Excel traffic export context
- [ ] Assess prompt handles empty rules from NullAdapter with inference guidance
- [ ] Both stages use correct temperature (0.1 per D025)
- [ ] Both stages return correct dict shape matching ExcelPipelineState fields
- [ ] Prompts handle DirectionLabel.UNKNOWN gracefully
- [ ] All code passes pyright strict (src/ scope)

## Verification

- `pytest tests/test_pipeline/test_excel_stages.py -v -k "analyze or assess"` — analyze + assess stage tests pass
- `npx pyright src/policyfoundry/pipeline/excel_stages/ src/policyfoundry/pipeline/excel_prompts/` — 0 errors

## Inputs

- `src/policyfoundry/pipeline/excel_summarizer.py` — summarize_flows(), format_flow_summary_message() from T01
- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState from T01
- `src/policyfoundry/pipeline/schema.py` — TrafficAnalysis, SecurityAssessment models (reused from M01)
- `src/policyfoundry/pipeline/stages/analyze.py` — M01 pattern to mirror
- `src/policyfoundry/pipeline/stages/assess.py` — M01 pattern to mirror

## Expected Output

- `src/policyfoundry/pipeline/excel_stages/__init__.py` — Package init
- `src/policyfoundry/pipeline/excel_stages/analyze.py` — excel_analyze_stage()
- `src/policyfoundry/pipeline/excel_stages/assess.py` — excel_assess_stage()
- `src/policyfoundry/pipeline/excel_prompts/__init__.py` — Package init
- `src/policyfoundry/pipeline/excel_prompts/analyze.py` — System prompt + user message formatter
- `src/policyfoundry/pipeline/excel_prompts/assess.py` — System prompt + user message formatter
- `tests/test_pipeline/test_excel_stages.py` — Analyze + assess stage tests (partial — T03 adds remaining)
