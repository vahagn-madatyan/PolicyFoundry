---
estimated_steps: 5
estimated_files: 7
---

# T01: Create test scaffolding and pipeline output fixtures

**Slice:** S08 — Output And Safety
**Milestone:** M001

## Description

Tests-first task. Create the test directories, realistic PipelineState fixtures, and initially-failing test files that define the verification targets for all S08 work. Tests import from modules that don't yet exist (`output.rich_output`, `output.json_output`, `output.models`, `adapters.safety`) — they should fail at import time, which is correct at this stage.

## Steps

1. Create `tests/test_output/__init__.py` and `tests/test_safety/__init__.py` as empty init files.
2. Create `tests/test_output/conftest.py` with realistic fixtures:
   - `sample_pipeline_state` — a full PipelineState dict with all 4 stage outputs populated (using the same model structures from `tests/test_pipeline/conftest.py`), plus a `token_usage` dict with prompt_tokens, completion_tokens, total_tokens, total_cost, and per-stage breakdown.
   - `sample_pipeline_state_no_tokens` — same state but without the `token_usage` key (tests graceful handling of absent field).
   - `sample_pipeline_state_empty` — minimal state with only `run_id`, `started_at`, `current_stage` (tests rendering with missing stage outputs).
   - Import `RiskLevel`, `PolicyProposal`, `RuleDecision`, `TrafficAnalysis`, `SecurityAssessment` for fixture building.
3. Create `tests/test_output/test_rich_output.py` with tests:
   - `test_format_rich_renders_summary_panel` — verifies Rich output includes run_id and summary text.
   - `test_format_rich_risk_colors` — verifies decisions table uses correct color per RiskLevel (LOW→green, MEDIUM→yellow, HIGH→red, CRITICAL→bold red).
   - `test_format_rich_token_usage_footer` — verifies token usage section shows prompt/completion tokens and cost.
   - `test_format_rich_missing_token_usage` — verifies graceful rendering when token_usage is absent (shows "N/A").
   - `test_format_rich_empty_state` — verifies rendering with minimal state doesn't crash.
   - Use `Console(file=StringIO())` to capture Rich output as plain text for assertions.
4. Create `tests/test_output/test_json_output.py` with tests:
   - `test_format_json_valid_json` — verifies output is valid JSON via `json.loads()`.
   - `test_format_json_contains_all_stages` — verifies JSON has analysis, assessment, proposals, decisions keys.
   - `test_format_json_roundtrips_through_pipeline_result` — verifies JSON can be loaded into PipelineResult model.
   - `test_format_json_includes_token_usage` — verifies token_usage is in JSON output.
   - `test_format_json_missing_stages` — verifies empty state produces valid JSON with null/empty fields.
5. Create `tests/test_output/test_models.py` with tests:
   - `test_pipeline_result_from_state` — verifies PipelineResult construction from PipelineState dict.
   - `test_pipeline_result_serialization` — verifies `model_dump_json()` produces valid JSON.
   - `test_token_usage_defaults` — verifies TokenUsage defaults to zeros.
   - `test_token_usage_accumulation` — verifies TokenUsage can sum multiple calls.
6. Create `tests/test_safety/test_readonly_adapter.py` with tests:
   - `test_readonly_delegates_get_rules` — verifies get_rules() is forwarded to wrapped adapter.
   - `test_readonly_delegates_validate` — verifies validate() is forwarded.
   - `test_readonly_delegates_capabilities` — verifies capabilities() is forwarded.
   - `test_readonly_blocks_apply_rule` — verifies apply_rule() raises SafetyError with correct error_code.
   - `test_readonly_blocks_apply_rules` — verifies apply_rules() raises SafetyError.
   - `test_safety_error_has_structured_details` — verifies SafetyError carries method name in details dict.

## Must-Haves

- [ ] `tests/test_output/conftest.py` has realistic PipelineState fixture with all 4 stages populated
- [ ] `tests/test_output/test_rich_output.py` has tests for summary, risk colors, token footer, missing tokens, empty state
- [ ] `tests/test_output/test_json_output.py` has tests for valid JSON, all stages, roundtrip, token usage, empty state
- [ ] `tests/test_output/test_models.py` has tests for PipelineResult and TokenUsage
- [ ] `tests/test_safety/test_readonly_adapter.py` has tests for delegation and write blocking
- [ ] All tests are discoverable by pytest (even if they fail at import)

## Verification

- `pytest tests/test_output/ tests/test_safety/ --collect-only 2>&1` shows test collection (may have import errors — expected since modules don't exist yet)
- All test files contain meaningful assertions, not placeholder `pass` stubs

## Observability Impact

- Signals added/changed: None (test scaffolding only)
- How a future agent inspects this: `pytest --collect-only` to verify test discovery
- Failure state exposed: Import errors from not-yet-created modules (expected)

## Inputs

- `tests/test_pipeline/conftest.py` — reuse fixture patterns (sample models, mock adapter, mock LLM client)
- `src/policyfoundry/pipeline/schema.py` — TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision model structures
- `src/policyfoundry/pipeline/state.py` — PipelineState TypedDict fields
- `src/policyfoundry/adapters/schema.py` — RiskLevel enum values

## Expected Output

- `tests/test_output/__init__.py` — empty init
- `tests/test_output/conftest.py` — 3 PipelineState fixtures (full, no-tokens, empty)
- `tests/test_output/test_rich_output.py` — 5 Rich formatter tests
- `tests/test_output/test_json_output.py` — 5 JSON formatter tests
- `tests/test_output/test_models.py` — 4 model tests
- `tests/test_safety/__init__.py` — empty init
- `tests/test_safety/test_readonly_adapter.py` — 6 safety tests
