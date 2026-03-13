---
id: T01
parent: S08
milestone: M001
provides:
  - test scaffolding for output formatters (Rich, JSON, models)
  - test scaffolding for safety adapter (ReadOnlyAdapter, SafetyError)
  - shared PipelineState fixtures (full, no-tokens, empty variants)
key_files:
  - tests/test_output/conftest.py
  - tests/test_output/test_rich_output.py
  - tests/test_output/test_json_output.py
  - tests/test_output/test_models.py
  - tests/test_safety/test_readonly_adapter.py
key_decisions:
  - PipelineState fixtures use model_dump() on real Pydantic models for realistic dicts
  - Token usage fixture includes per_stage breakdown matching planned TokenUsage model
  - TYPE_CHECKING guard used for PipelineState imports in tests to satisfy ruff TC001
patterns_established:
  - Console(file=StringIO()) pattern for capturing Rich output as plain text in tests
  - Three-tier fixture strategy (full state, no-tokens, empty) for backward compat testing
  - Test classes organized by feature (summary, risk colors, token footer, empty state)
observability_surfaces:
  - none (test scaffolding only)
duration: 15m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T01: Create test skeletons and shared fixtures for output, safety, and token tracking

**Created 20 failing tests across 4 test files with realistic PipelineState fixtures for S08 output and safety work.**

## What Happened

Created the test directory structure and all test files for S08. Built `tests/test_output/conftest.py` with three PipelineState fixture variants:
- `sample_pipeline_state` — full state with all 4 stage outputs (analysis, assessment, proposals, decisions) plus token_usage with per-stage breakdown
- `sample_pipeline_state_no_tokens` — same but without token_usage key (backward compat testing)
- `sample_pipeline_state_empty` — minimal state with only run_id/started_at/current_stage

Test files import from not-yet-existing modules (`output.rich_output`, `output.json_output`, `output.models`, `adapters.safety`, `exceptions.SafetyError`), so they fail at import time with `ModuleNotFoundError` — which is the correct expected state.

Merged the `init` branch into `gsd/M001/S08` to bring in source code that the branch was missing (diverged before source was added).

## Verification

- `pytest tests/test_output/ tests/test_safety/ --collect-only` → 4 collection errors (all `ModuleNotFoundError` for not-yet-created modules) ✅
- `grep -c "def test_"` confirms: 5 Rich tests + 5 JSON tests + 4 model tests + 6 safety tests = 20 total ✅
- `ruff check tests/test_output/ tests/test_safety/` → All checks passed ✅
- All test files contain meaningful assertions (no `pass` stubs) ✅

### Slice-level verification (T01 status):
- `pytest tests/test_output/ -v` — ❌ expected (modules don't exist yet)
- `pytest tests/test_safety/ -v` — ❌ expected (modules don't exist yet)
- `pytest tests/test_pipeline/test_llm.py -v` — not yet applicable (T03 scope)
- `ruff check tests/` on new files — ✅ clean

## Diagnostics

`pytest tests/test_output/ tests/test_safety/ --collect-only` verifies test discovery. Import errors will resolve as T02-T04 implement the target modules.

## Deviations

- Merged `init` branch into `gsd/M001/S08` to get source files — branch had diverged before code was committed to `init`.
- Used `/data/test-data/` instead of `/tmp/test-data/` for flow_log_path fixture to avoid ruff S108 temp-dir warning.

## Known Issues

None.

## Files Created/Modified

- `tests/test_output/__init__.py` — empty init for test package
- `tests/test_output/conftest.py` — 3 PipelineState fixtures (full, no-tokens, empty)
- `tests/test_output/test_rich_output.py` — 5 Rich formatter tests (summary, colors, token footer, missing tokens, empty state)
- `tests/test_output/test_json_output.py` — 5 JSON formatter tests (valid JSON, all stages, roundtrip, token usage, empty state)
- `tests/test_output/test_models.py` — 4 model tests (PipelineResult from_state, serialization, TokenUsage defaults, accumulation)
- `tests/test_safety/__init__.py` — empty init for test package
- `tests/test_safety/test_readonly_adapter.py` — 6 safety tests (delegation of get_rules/validate/capabilities, blocking apply_rule/apply_rules, structured error details)
