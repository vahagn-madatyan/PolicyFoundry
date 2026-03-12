---
id: T12
parent: S09
milestone: M001
provides:
  - "SafetyError exception in policyfoundry.exceptions with error_code='SAFETY_VIOLATION'"
  - "ReadOnlyAdapter in policyfoundry.adapters.safety — delegates reads, blocks writes with SafetyError"
  - "Typer CLI app with analyze, rules, config commands in policyfoundry.main"
  - "__main__.py entry point matching policyfoundry.__main__:main registration"
  - "22 CLI integration tests replacing T01 stubs (analyze: 13, config: 4, rules: 5)"
key_files:
  - src/policyfoundry/exceptions.py
  - src/policyfoundry/adapters/safety.py
  - src/policyfoundry/main.py
  - src/policyfoundry/__main__.py
  - tests/test_cli/conftest.py
  - tests/test_cli/test_analyze.py
  - tests/test_cli/test_config.py
  - tests/test_cli/test_rules.py
key_decisions:
  - "D027 confirmed: CLI commands are sync with internal asyncio.run() for the async pipeline"
  - "D030 confirmed: PolicyFoundryError caught at each command boundary → Rich error panel with error_code and details, not raw traceback"
  - "JSON output uses typer.echo() not console.print() to avoid Rich escape characters in JSON"
  - "API key redaction in config command: first 4 chars visible + asterisks for remainder"
patterns_established:
  - "CLI error boundary pattern: try/except PolicyFoundryError → _render_error(exc) Rich panel + typer.Exit(code=1); generic Exception → 'Unexpected error' panel"
  - "CLI mock pattern: module-level imports in main.py enable patch('policyfoundry.main.load_config') etc; MagicMock (not AsyncMock) for LLM client since get_usage() is sync"
  - "ReadOnlyAdapter pattern: wraps FirewallAdapter, delegates get_rules/validate/capabilities, raises SafetyError(error_code='SAFETY_WRITE_BLOCKED', details={'method': name}) on apply_rule/apply_rules"
observability_surfaces:
  - "policyfoundry config — dumps resolved configuration with sensitive value redaction"
  - "policyfoundry analyze --debug — enables full tracebacks on error"
  - "policyfoundry analyze --format json — machine-parseable pipeline output"
  - "PolicyFoundryError subtypes render as Rich panels with error_code + details dict at CLI boundary"
  - "Token usage (prompt/completion/total tokens + cost) displayed in Rich output footer and JSON output"
duration: ~25min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T12: Implement SafetyError, ReadOnlyAdapter, and build Typer CLI

**Built the PolicyFoundry CLI — SafetyError exception, ReadOnlyAdapter safety wrapper, Typer app with analyze/rules/config commands, entry point, and 22 passing CLI integration tests.**

## What Happened

1. **Added SafetyError to exceptions.py** — `class SafetyError(PolicyFoundryError)` with default `error_code="SAFETY_VIOLATION"`. Importable from `policyfoundry.exceptions`.

2. **Created adapters/safety.py** — `ReadOnlyAdapter(FirewallAdapter)` wraps any adapter, delegates `get_rules()`, `validate()`, `capabilities()` to the wrapped adapter, and raises `SafetyError(error_code="SAFETY_WRITE_BLOCKED", details={"method": ...})` on `apply_rule()` or `apply_rules()`. All 6 pre-existing safety tests pass.

3. **Created main.py with Typer app** — Three commands:
   - `analyze`: loads config → creates LLM client → wraps adapter in ReadOnlyAdapter → runs pipeline with Rich Status spinner → formats output as Rich tables or JSON. Token usage displayed in footer.
   - `rules`: fetches rules via adapter → displays Rich table or JSON. Shows "No rules found" panel when empty.
   - `config`: shows resolved config in Rich panel or JSON. Redacts API keys (first 4 chars visible).
   - Global `--debug` and `--verbose` flags. Error boundary catches `PolicyFoundryError` → Rich error panel with error_code + details; generic exceptions → "Unexpected error" panel.

4. **Created __main__.py** — Simple entry point matching `policyfoundry.__main__:main` registration.

5. **Implemented 22 CLI integration tests** replacing the T01 stub tests: 13 analyze tests (5 Rich output, 4 JSON output, 4 error handling), 4 config tests, 5 rules tests. All use patched dependencies to prevent real API calls.

## Verification

- `uv run pytest tests/test_safety/ -x -v` → **6 passed** (SAFE-01 proven)
- `uv run pytest tests/test_cli/ -x -v` → **22 passed** (OUT-01, OUT-02, SAFE-02, error handling proven)
- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ tests/test_adapters/ tests/test_output/ tests/test_pipeline/ -x` → **318 passed** (reconstruction fidelity preserved)
- `uv run policyfoundry --help` → exit 0, shows analyze/rules/config commands ✓
- `uv run policyfoundry analyze --help` → exit 0, shows --source/--format/--sg-ids/--debug ✓
- `uv run python -c "from policyfoundry.exceptions import SafetyError; print(SafetyError.__bases__)"` → shows PolicyFoundryError ✓

### Slice Verification Status (all checks pass — final task)
- ✅ Pre-existing 318 tests pass (reconstruction fidelity)
- ✅ 6 safety tests pass (ReadOnlyAdapter + SafetyError)
- ✅ 22 CLI integration tests pass (analyze/rules/config commands + error handling)
- ✅ `policyfoundry --help` exits 0, shows commands
- ✅ `policyfoundry analyze --help` exits 0, shows expected options
- ✅ Error handling test verifies PolicyFoundryError → exit 1 + actionable message (not traceback)

## Diagnostics

- Run `uv run policyfoundry config` to see resolved configuration
- Run `uv run policyfoundry analyze --debug --sg-ids sg-xxx` to see full tracebacks on error
- Run `uv run policyfoundry analyze --format json --sg-ids sg-xxx` for machine-parseable output
- Import safety: `from policyfoundry.adapters.safety import ReadOnlyAdapter`
- Import error: `from policyfoundry.exceptions import SafetyError`

## Deviations

- Test fixture data in conftest needed `port_distribution`, `anomalies`, `bandwidth_outliers` fields for TrafficAnalysis and `from_port`/`to_port` for PortRange, `description` + `impact_analysis` for PolicyProposal, `source` as list — all aligned to actual Pydantic schema models discovered during test execution.
- JSON output uses `typer.echo()` instead of `console.print()` to avoid Rich escape characters corrupting JSON.
- Rules table test checks for "allow-ht" prefix instead of "allow-https" because Rich truncates long cell values in narrow terminals.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/exceptions.py` — added SafetyError class with default error_code="SAFETY_VIOLATION"
- `src/policyfoundry/adapters/safety.py` — new ReadOnlyAdapter wrapping FirewallAdapter for suggest-only mode
- `src/policyfoundry/main.py` — new Typer CLI app with analyze/rules/config commands
- `src/policyfoundry/__main__.py` — new entry point for `policyfoundry` CLI
- `tests/test_cli/conftest.py` — updated with schema-accurate sample_pipeline_state fixture
- `tests/test_cli/test_analyze.py` — 13 real tests replacing stubs (Rich/JSON output + error handling)
- `tests/test_cli/test_config.py` — 4 real tests replacing stubs (display + redaction + JSON)
- `tests/test_cli/test_rules.py` — 5 real tests replacing stubs (table + JSON + empty + errors)
