---
id: T04
parent: S08
milestone: M001
provides:
  - format_rich() Rich terminal formatter with 6-section pipeline report and risk-colored decision table
  - format_json() JSON serializer via PipelineResult.from_state() with OutputError on failure
  - RISK_COLORS mapping (LOW→green, MEDIUM→yellow, HIGH→red, CRITICAL→bold red)
  - rich>=14.0 as explicit direct dependency
key_files:
  - src/policyfoundry/output/rich_output.py
  - src/policyfoundry/output/json_output.py
  - src/policyfoundry/output/__init__.py
  - pyproject.toml
key_decisions:
  - Token usage footer renders N/A when token_usage is absent (not silently omitting the section) — tests assert on this
  - Schema dict fields (top_talkers, risk_scores, rule_gaps) cast to list[dict[str, Any]] at render boundary to satisfy pyright strict without modifying upstream schema types
patterns_established:
  - Console(file=StringIO()) capture pattern for testing Rich output as plain text
  - _risk_text() helper returns Rich Text with RISK_COLORS style for consistent risk coloring
  - Per-section try/except with logger.warning for graceful degradation — degraded output beats no output
observability_surfaces:
  - format_rich() logs WARNING with exc_info on section reconstruction failure (graceful skip)
  - format_json() raises OutputError with error_code="OUTPUT_SERIALIZE_FAILED" on serialization failure
duration: 12m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T04: Implement Rich and JSON formatters with risk-colored output

**Built format_rich() with 6-section pipeline report (summary, traffic, security, proposals, risk-colored decisions, token footer) and format_json() with PipelineResult JSON serialization.**

## What Happened

Created two output formatters consumed by S09 CLI. `format_rich()` reconstructs typed Pydantic models from PipelineState dicts and renders six sections: summary panel (run_id, started_at, sg_ids), traffic analysis table (flows, sources, destinations, top talkers), security assessment (overall risk with color, scores, gaps, compliance), proposal details (rule name, justification, risk, confidence), decision table (with RISK_COLORS-styled risk_level cells and overflow="fold" on reason column), and token usage footer (or N/A when absent). Each section is wrapped in try/except for graceful degradation — a malformed stage dict logs a warning and skips that section instead of crashing.

`format_json()` delegates to `PipelineResult.from_state()` and calls `model_dump_json(indent=2)`. On construction or serialization failure, it raises `OutputError` with `error_code="OUTPUT_SERIALIZE_FAILED"`.

Added `rich>=14.0` as an explicit direct dependency (was previously only transitive via instructor). Updated `output/__init__.py` to export `format_rich`, `format_json`, `PipelineResult`, `TokenUsage`, and `RISK_COLORS`.

## Verification

- `uv run pytest tests/test_output/test_rich_output.py -v` — 5/5 passed (summary panel, risk colors, token footer, missing tokens, empty state)
- `uv run pytest tests/test_output/test_json_output.py -v` — 5/5 passed (valid JSON, all stages, roundtrip, token usage, missing stages)
- `uv run pytest tests/test_output/ tests/test_pipeline/test_llm.py -v` — 39/39 passed (all output + model + LLM tests)
- `uv run pyright src/policyfoundry/output/` — 0 errors, 0 warnings
- `uv run ruff check src/policyfoundry/output/ tests/test_output/` — all checks passed
- Safety tests skipped (T05 module not yet implemented — expected ImportError)

### Slice-Level Verification Status (intermediate task)

| Check | Status |
|-------|--------|
| `pytest tests/test_output/ -v` | ✅ 14 passed |
| `pytest tests/test_safety/ -v` | ⏳ ImportError — T05 (ReadOnlyAdapter) not yet implemented |
| `pytest tests/test_pipeline/test_llm.py -v` | ✅ 25 passed |
| `pyright src/policyfoundry/output/` | ✅ 0 errors |
| `ruff check src/ tests/` | ✅ clean |
| backward compat (missing token_usage) | ✅ test_format_rich_missing_token_usage + test_format_json_missing_stages pass |

## Diagnostics

- **Rich output inspection:** In tests, use `Console(file=StringIO(), force_terminal=False, width=120)` to capture plain text; use `force_terminal=True, color_system="truecolor"` to capture ANSI escape sequences for color verification.
- **JSON output inspection:** `json.loads(format_json(state))` returns a dict; `PipelineResult(**parsed)` round-trips it back to typed model.
- **Failure visibility:** `OutputError` with `error_code="OUTPUT_SERIALIZE_FAILED"` on JSON serialization failure; Rich formatter logs `WARNING` per skipped section on reconstruction errors.

## Deviations

- Test file `test_rich_output.py` has 5 tests (T01 skeleton count said 7) — the T01 skeleton created 5 tests which all pass. No gap in coverage; the 5 tests cover all required scenarios (summary, colors, token footer, missing tokens, empty state).

## Known Issues

- Safety test suite (`tests/test_safety/`) cannot run yet — `policyfoundry.adapters.safety` module is T05 work.

## Files Created/Modified

- `src/policyfoundry/output/rich_output.py` — Created: format_rich() with 6 rendering sections, RISK_COLORS dict, _risk_text() helper
- `src/policyfoundry/output/json_output.py` — Created: format_json() with PipelineResult serialization and OutputError handling
- `src/policyfoundry/output/__init__.py` — Updated: exports format_rich, format_json, PipelineResult, TokenUsage, RISK_COLORS
- `pyproject.toml` — Added rich>=14.0 to direct dependencies
