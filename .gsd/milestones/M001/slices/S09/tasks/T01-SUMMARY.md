---
id: T01
parent: S09
milestone: M001
provides:
  - bytecode inspection toolkit for .pyc → structured info extraction
  - pyproject.toml with all runtime deps, entry points, dev deps
  - 22 failing CLI integration test stubs across analyze/rules/config commands
key_files:
  - tools/inspect_pyc.py
  - pyproject.toml
  - tests/test_cli/conftest.py
  - tests/test_cli/test_analyze.py
  - tests/test_cli/test_rules.py
  - tests/test_cli/test_config.py
key_decisions:
  - hatchling build-backend with license = {text = "BSL-1.1"} (hatchling rejects SPDX "BSL-1.1" as unknown)
  - Typer CliRunner() without mix_stderr (Typer's CliRunner doesn't support that kwarg)
patterns_established:
  - CLI test stubs use pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")
  - conftest provides cli_runner, mock_llm_client_factory, mock_adapter_factory fixtures
  - tools/inspect_pyc.py is invoked via `uv run python tools/inspect_pyc.py <path>`
observability_surfaces:
  - tools/inspect_pyc.py prints clear errors on .pyc format issues or Python version mismatch
duration: 1 step
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T01: Built bytecode inspection toolkit, reconstructed pyproject.toml, created 22 failing CLI test stubs

**Shipped bytecode inspection toolkit that extracts classes/functions/imports/docstrings from any .pyc, a complete pyproject.toml enabling `uv sync`/`uv run`, and 22 failing CLI test stubs defining the slice done condition.**

## What Happened

Built three foundations for S09:

1. **`tools/inspect_pyc.py`** — Reads .pyc files using Python 3.13 marshal/dis/types. Extracts module docstrings, import statements (IMPORT_NAME/IMPORT_FROM opcodes), class definitions with base classes, function/method signatures with argument names, and string constants. Supports `--recursive` mode for directory trees, `--summary` for compact output, and `--verbose` for string constants.

2. **`pyproject.toml`** — Reconstructed from `.dist-info/METADATA` (10 runtime deps), `entry_points.txt` (console_scripts + adapter plugin), and `WHEEL` (build metadata). Added `typer>=0.24.1` as 11th runtime dep. Dev deps: pytest, moto[s3], pytest-asyncio. Build system: hatchling. Wheel packages: `["src/policyfoundry"]`.

3. **CLI test stubs** — 22 test functions across 3 test files (test_analyze.py, test_rules.py, test_config.py) plus conftest.py with shared fixtures. All tests use `pytest.fail()` to produce clean FAILED results. Tests cover: Rich output, JSON output, error handling, token cost display, rule display, config display, and sensitive value redaction.

## Verification

All four must-haves verified:

- `uv run python tools/inspect_pyc.py src/policyfoundry/__pycache__/exceptions.cpython-313.pyc` → outputs 14 class names including PolicyFoundryError, ConfigError, IngestionError, etc. ✅
- `uv sync 2>&1 | tail -3` → "Resolved 98 packages … Audited 97 packages" (success) ✅
- `uv run pytest tests/test_cli/ --collect-only -q` → 22 tests collected ✅
- `uv run pytest tests/test_cli/ -x 2>&1 | tail -3` → "1 failed" (expected — stubs use pytest.fail) ✅

### Slice-level verification status (T01 is intermediate — partial passes expected):

| Check | Status | Notes |
|-------|--------|-------|
| Pre-existing tests pass | ⏳ | Source not yet reconstructed (T02–T09) |
| Safety tests pass | ⏳ | SafetyError/ReadOnlyAdapter not yet built (T12) |
| CLI integration tests pass | ⏳ | CLI module not yet built (T10); stubs correctly fail |
| `policyfoundry --help` exits 0 | ⏳ | __main__.py not yet reconstructed |
| `policyfoundry analyze --help` exits 0 | ⏳ | CLI app not yet wired |

## Diagnostics

- Run `uv run python tools/inspect_pyc.py <any.pyc>` to extract structure from any bytecode file
- Run `uv run python tools/inspect_pyc.py --recursive src/` to scan all source .pyc files
- Toolkit prints "Error: ..." to stderr with clear messages on .pyc read failures

## Deviations

- `license = {text = "BSL-1.1"}` instead of plain string — hatchling rejects SPDX `BSL-1.1` as unknown, requires table form
- `CliRunner()` without `mix_stderr=False` — Typer's CliRunner doesn't support that parameter (unlike Click's)

## Known Issues

None.

## Files Created/Modified

- `tools/inspect_pyc.py` — bytecode inspection toolkit (reads .pyc → structured output)
- `pyproject.toml` — complete package definition (11 runtime deps, entry points, dev deps, hatchling build)
- `tests/test_cli/__init__.py` — empty package marker
- `tests/test_cli/conftest.py` — shared fixtures (CliRunner, mock LLM client factory, mock adapter factory)
- `tests/test_cli/test_analyze.py` — 13 failing test stubs for analyze command (Rich, JSON, error handling)
- `tests/test_cli/test_rules.py` — 5 failing test stubs for rules command
- `tests/test_cli/test_config.py` — 4 failing test stubs for config command
