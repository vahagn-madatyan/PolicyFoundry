---
estimated_steps: 4
estimated_files: 7
---

# T01: Build bytecode inspection toolkit, reconstruct pyproject.toml, create failing CLI test stubs

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Establishes the three foundations for S09: (1) a bytecode inspection toolkit that all subsequent reconstruction tasks depend on, (2) the missing `pyproject.toml` so `uv sync` and `uv run` work, and (3) failing CLI integration test stubs that define the slice's done condition before any implementation begins.

The toolkit reads `.pyc` files using Python 3.13's `marshal` + `dis` + `types` modules and extracts structured information: module docstrings, import statements, class definitions with base classes, function/method signatures with argument names, default values, and string constants. This accelerates reconstruction in T02–T11.

The CLI test stubs contain the test function signatures and mock boundaries that T13 will flesh out. They should be runnable but failing (assertions fail or skip markers present), proving the test infrastructure works.

## Steps

1. **Build `tools/inspect_pyc.py`** — A Python script that takes a `.pyc` file path, reads the code object, and prints structured output: module docstring, imports (from IMPORT_NAME/IMPORT_FROM opcodes), class hierarchy (from LOAD_BUILD_CLASS), function signatures (from inner code objects with `co_varnames[:co_argcount]`), and string constants. Must use `.venv/bin/python3` (Python 3.13) for `dis` compatibility. Include a `--recursive` mode that processes all `.pyc` files in a directory tree.

2. **Reconstruct `pyproject.toml`** from `.dist-info/METADATA` (deps, Python version, license) and `entry_points.txt` (console_scripts, adapter plugin). Add `typer` to dependencies (missing from original METADATA — see research constraints). Pin to the version installed in the venv (0.24.1 per research). Add dev dependencies: `pytest>=9.0`, `moto[s3]>=5.0`, `pytest-asyncio>=0.25`. Use `[build-system]` with `hatchling`. Set `[tool.hatch.build.targets.wheel]` packages to `["src/policyfoundry"]`. Run `uv sync` to verify.

3. **Create CLI integration test stubs** in `tests/test_cli/`: `__init__.py` (empty), `conftest.py` (shared fixtures — CliRunner instance, mock LLM client factory, mock adapter factory), `test_analyze.py` (test functions for rich output, json output, error handling), `test_rules.py` (test function for rules display), `test_config.py` (test function for config display). Each test should have a descriptive name and a body that either asserts `False` with a "not yet implemented" message or uses `pytest.fail()`.

4. **Verify** the toolkit works on a sample `.pyc`, `uv sync` succeeds, and CLI tests are discoverable by pytest (but fail as expected).

## Must-Haves

- [ ] `tools/inspect_pyc.py` successfully extracts class names, function signatures, and docstrings from any `.pyc` file in the project
- [ ] `pyproject.toml` includes all 10 runtime deps from METADATA plus `typer`, correct entry points, Python >=3.12
- [ ] `uv sync` completes without error
- [ ] CLI test stubs exist and pytest discovers them (but they fail)

## Verification

- `uv run python tools/inspect_pyc.py src/policyfoundry/__pycache__/exceptions.cpython-313.pyc` → outputs class names including `PolicyFoundryError`, `ConfigError`, etc.
- `uv sync 2>&1 | tail -3` → success
- `uv run pytest tests/test_cli/ --collect-only -q` → shows test items
- `uv run pytest tests/test_cli/ -x 2>&1 | tail -3` → FAILED (expected)

## Observability Impact

- Signals added/changed: None (toolkit is a dev-time tool, not runtime)
- How a future agent inspects this: Run `uv run python tools/inspect_pyc.py <any.pyc>` to extract structure from bytecode
- Failure state exposed: Toolkit prints clear error if .pyc format is unreadable or Python version mismatch

## Inputs

- `.venv/lib/python3.13/site-packages/policyfoundry-0.1.0.dist-info/METADATA` — dependency list
- `.venv/lib/python3.13/site-packages/policyfoundry-0.1.0.dist-info/entry_points.txt` — console_scripts and adapter plugin
- `.venv/lib/python3.13/site-packages/policyfoundry-0.1.0.dist-info/WHEEL` — build metadata
- S09 research: constraint that `typer` is not in original deps and must be added
- S09 research: CLI test boundaries (mock LLMClient + adapter, keep real config/ingestion/storage/output)

## Expected Output

- `tools/inspect_pyc.py` — bytecode inspection toolkit usable by all reconstruction tasks
- `pyproject.toml` — complete package definition enabling `uv sync` and `uv run`
- `tests/test_cli/__init__.py` — empty
- `tests/test_cli/conftest.py` — shared CLI test fixtures (CliRunner, mock factories)
- `tests/test_cli/test_analyze.py` — failing test stubs for analyze command
- `tests/test_cli/test_rules.py` — failing test stubs for rules command
- `tests/test_cli/test_config.py` — failing test stubs for config command
