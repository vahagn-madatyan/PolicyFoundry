---
id: T13
parent: S09
milestone: M001
provides:
  - "25 CLI integration tests covering analyze (rich/json/error/safety), rules, config, and help commands"
  - "Final slice verification gate — 349 tests pass across all modules"
key_files:
  - tests/test_cli/conftest.py
  - tests/test_cli/test_analyze.py
  - tests/test_cli/test_rules.py
  - tests/test_cli/test_config.py
key_decisions:
  - "T12 already implemented full CLI test stubs with real assertions — T13 added the remaining must-have tests (safety enforcement, help text)"
patterns_established:
  - "CLI safety test pattern: capture adapter kwarg from run_pipeline side_effect to assert isinstance(ReadOnlyAdapter)"
  - "CLI help text tests: invoke app with ['--help'] and assert command names present in output"
observability_surfaces:
  - "CLI integration tests exercise full error handling path — PolicyFoundryError subtypes produce structured Rich output at CLI boundary (exit code 1, error_code, details, no traceback)"
  - "Run `uv run pytest tests/test_cli/ -v` to see individual CLI test results; add `-s` to see captured CLI output"
duration: 15min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T13: Complete CLI integration tests and final slice verification

**Added safety enforcement and help text tests, verified entire 349-test suite passes — all S09 requirements proven.**

## What Happened

T12 had already implemented 22 CLI integration tests with real assertions (not stubs). T13 completed the remaining must-have tests specified in the task plan:

1. **`TestAnalyzeSafetyEnforced::test_analyze_safety_enforced`** — Captures the adapter kwarg passed to `run_pipeline` via a side_effect function and asserts it's an instance of `ReadOnlyAdapter`. This proves SAFE-01 at the integration level.

2. **`TestHelpText::test_help_text_shows_all_commands`** — Invokes `--help` and asserts "analyze", "rules", "config" all appear in output.

3. **`TestHelpText::test_analyze_help_shows_options`** — Invokes `analyze --help` and asserts `--source`, `--format`, `--sg-ids` appear.

Final test count: 25 CLI tests (14 analyze + 6 config + 5 rules).

Ran the complete test suite as the final verification gate: **349 tests pass** (318 pre-existing + 6 safety + 25 CLI).

## Verification

All slice-level verification checks pass:

- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ tests/test_adapters/ tests/test_output/ tests/test_pipeline/ -x` → **318 passed** (reconstruction fidelity confirmed)
- `uv run pytest tests/test_safety/ -x` → **6 passed** (SAFE-01: ReadOnlyAdapter + SafetyError)
- `uv run pytest tests/test_cli/ -x -v` → **25 passed** (OUT-01, OUT-02, SAFE-01, SAFE-02, D030 error handling)
- `uv run policyfoundry --help` → exits 0, shows commands: analyze, rules, config
- `uv run policyfoundry analyze --help` → exits 0, shows --source, --format, --sg-ids options
- `uv run pytest tests/ -x -q` → **349 passed in 10.85s** (full suite green)

Requirement coverage proven by integration tests:
- **OUT-01**: `test_analyze_rich_output_contains_traffic_analysis`, `test_analyze_rich_output_contains_token_cost` — Rich output with traffic analysis + cost
- **OUT-02**: `test_analyze_json_output_is_valid_json`, `test_analyze_json_output_contains_pipeline_stages` — valid JSON with all stage data
- **SAFE-01**: `test_analyze_safety_enforced` — adapter wrapped in ReadOnlyAdapter
- **SAFE-02**: `test_analyze_rich_output_contains_token_cost` — token usage displayed
- **D030**: `test_analyze_config_error_shows_actionable_message` — Rich panel errors, no tracebacks

## Diagnostics

- Run `uv run pytest tests/test_cli/ -v` to see individual CLI test results
- Run `uv run pytest tests/test_cli/ -v -s` to see captured CLI output for debugging
- CliRunner captures exit_code + output — test assertions show exactly what the CLI produced vs. expected
- Safety test: `test_analyze_safety_enforced` captures the actual adapter object passed to run_pipeline, enabling inspection of the wrapping chain

## Deviations

T12 had already implemented most test stubs with real assertions rather than leaving them as `pytest.fail()` stubs. T13 focused on the remaining must-have tests (safety enforcement, help text) and the final verification gate rather than rewriting existing passing tests.

## Known Issues

None.

## Files Created/Modified

- `tests/test_cli/test_analyze.py` — Added `TestAnalyzeSafetyEnforced` class with `test_analyze_safety_enforced` (SAFE-01 proof)
- `tests/test_cli/test_config.py` — Added `TestHelpText` class with `test_help_text_shows_all_commands` and `test_analyze_help_shows_options`
