---
estimated_steps: 4
estimated_files: 4
---

# T13: Complete CLI integration tests and final slice verification

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Completes the CLI integration test stubs created in T01 with real assertions that exercise the full stack through the Typer CLI entrypoint. These tests are the final proof that all requirements (OUT-01, OUT-02, SAFE-01, SAFE-02) are met at the integration level. Uses `typer.testing.CliRunner` to invoke commands in-process with mocked LLM and adapter boundaries.

After tests pass, runs the complete test suite (all pre-existing 300+ tests + safety tests + CLI tests) as the final verification gate for S09.

## Steps

1. **Complete `tests/test_cli/conftest.py`** — Shared fixtures:
   - `cli_runner` — `typer.testing.CliRunner` instance
   - `mock_llm_client` — A mock `LLMClient` that returns predetermined `TokenUsage` and doesn't call a real LLM
   - `mock_adapter` — A mock `FirewallAdapter` that returns sample `UniversalRule` data
   - `sample_pipeline_state` — Reuse or adapt the pattern from `tests/test_output/conftest.py`
   - Monkeypatch fixtures to replace `create_llm_client`, `AdapterRegistry.get_adapter`, and `run_pipeline` at the CLI boundary so the full command flow executes without real LLM/AWS calls

2. **Complete `tests/test_cli/test_analyze.py`** — Integration tests:
   - `test_analyze_rich_output` — Invoke `analyze --format rich` with mocked pipeline returning `sample_pipeline_state` → exit 0, output contains risk table headers, traffic analysis section, token usage/cost display (OUT-01, SAFE-02)
   - `test_analyze_json_output` — Invoke `analyze --format json` with mocked pipeline → exit 0, output is valid JSON parseable as dict, contains all pipeline stage keys (OUT-02)
   - `test_analyze_error_handling` — Invoke `analyze` with mocked pipeline raising `PipelineError` → exit 1, output contains actionable error message, output does NOT contain "Traceback" (D030)
   - `test_analyze_safety_enforced` — Verify that the adapter passed to `run_pipeline` is wrapped in `ReadOnlyAdapter` (SAFE-01)

3. **Complete `tests/test_cli/test_rules.py` + `test_config.py`** — Integration tests:
   - `test_rules_display` — Invoke `rules --adapter aws_sg --sg-id sg-test` with mocked adapter → exit 0, output contains rule data
   - `test_config_display` — Invoke `config` → exit 0, output contains config keys (e.g., "llm", "sources", "output")
   - `test_help_text` — Invoke `--help` → exit 0, output contains "analyze", "rules", "config"

4. **Run complete test suite** — `uv run pytest tests/ -x -q`. All tests must pass: 300+ pre-existing + 6 safety + ~7 CLI integration. Report exact counts. This is the final verification gate for S09.

## Must-Haves

- [ ] CLI tests mock LLM and adapter at boundary (no real external calls)
- [ ] `test_analyze_rich_output` verifies Rich output contains traffic analysis + token cost (OUT-01, SAFE-02)
- [ ] `test_analyze_json_output` verifies JSON is valid and contains pipeline stage data (OUT-02)
- [ ] `test_analyze_error_handling` verifies errors render as Rich panels, not tracebacks (D030)
- [ ] `test_analyze_safety_enforced` verifies ReadOnlyAdapter wraps the real adapter (SAFE-01)
- [ ] Full test suite passes: all pre-existing tests + safety tests + CLI tests

## Verification

- `uv run pytest tests/test_cli/ -x -v` → all CLI integration tests pass
- `uv run pytest tests/ -x -q 2>&1 | tail -3` → entire suite passes (300+ tests total)
- `uv run policyfoundry --help` → exit 0 (proves entry point works outside of test harness)

## Observability Impact

- Signals added/changed: CLI integration tests exercise the full error handling path, proving that `PolicyFoundryError` subtypes produce structured Rich output at the CLI boundary
- How a future agent inspects this: Run `uv run pytest tests/test_cli/ -v` to see individual CLI test results; add `-s` to see captured CLI output
- Failure state exposed: CliRunner captures exit_code + output — test assertions show exactly what the CLI produced vs. what was expected

## Inputs

- `tests/test_cli/` stubs from T01 (test structure and function names)
- `src/policyfoundry/main.py` from T12 (the Typer app being tested)
- `tests/test_output/conftest.py` from T10 (sample_pipeline_state fixture pattern)
- `src/policyfoundry/adapters/safety.py` from T12 (ReadOnlyAdapter)
- All reconstructed and new source files from T01–T12

## Expected Output

- `tests/test_cli/conftest.py` — completed with CliRunner, mock fixtures, monkeypatch setup
- `tests/test_cli/test_analyze.py` — completed with 4+ integration tests
- `tests/test_cli/test_rules.py` — completed with 1+ test
- `tests/test_cli/test_config.py` — completed with 2+ tests
- Full test suite result: all tests pass (300+ pre-existing + 6 safety + 7+ CLI)

After T13, all S09 must-haves are met:
- ✅ All 48 src files reconstructed (T02–T07)
- ✅ All 44 test files reconstructed (T08–T11)
- ✅ pyproject.toml reconstructed (T01)
- ✅ Full pre-existing test suite passes (T11)
- ✅ SafetyError + ReadOnlyAdapter + 6 safety tests pass (T12)
- ✅ CLI commands work with --help (T12)
- ✅ CLI integration tests prove OUT-01, OUT-02, SAFE-01, SAFE-02 (T13)
