---
estimated_steps: 5
estimated_files: 4
---

# T12: Implement SafetyError, ReadOnlyAdapter, and build Typer CLI

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

This is the core deliverable of S09 — the new code that makes PolicyFoundry a usable CLI tool. Three pieces of work:

1. **SafetyError + ReadOnlyAdapter** (SAFE-01): Add `SafetyError` to the exception hierarchy and create `ReadOnlyAdapter` that wraps any `FirewallAdapter`, delegating read operations and raising `SafetyError` on write attempts. Six pre-existing tests in `test_safety/` define the exact interface.

2. **Typer CLI** (OUT-01, OUT-02, SAFE-02): Create `main.py` with the Typer app containing `analyze`, `rules`, and `config` commands. The `analyze` command is the full pipeline: `load_config() → create_llm_client() → get_adapter() → ReadOnlyAdapter() → run_pipeline() → format_rich()/format_json()`. Commands are sync with internal `asyncio.run()` (D027). Error handling catches `PolicyFoundryError` at the boundary (D030).

3. **Entry point**: Create `__main__.py` matching the registered `policyfoundry.__main__:main` entry point.

## Steps

1. **Add `SafetyError` to `exceptions.py`** — `class SafetyError(PolicyFoundryError)` with `error_code="SAFETY_VIOLATION"`. Must be importable as `from policyfoundry.exceptions import SafetyError`.

2. **Create `adapters/safety.py`** — `ReadOnlyAdapter(FirewallAdapter)` that wraps another `FirewallAdapter`. Delegates: `get_rules()`, `validate()`, `capabilities()`. Raises `SafetyError` on: `apply_rule()`, `apply_rules()`. Constructor takes `wrapped: FirewallAdapter`. Run `uv run pytest tests/test_safety/ -x -v` → 6 tests pass.

3. **Create `main.py` with Typer app** — Three commands:
   - `analyze`: Options `--source` (default "local"), `--format` (rich/json, default rich), `--sg-ids` (list), `--config` (YAML path), `--debug` (flag). Sync wrapper calls `asyncio.run()` for the async pipeline. Wraps adapter in `ReadOnlyAdapter`. Shows Rich `Status` spinner during pipeline execution. Calls `format_rich(state)` or `format_json(state)` based on `--format`. Displays token usage from `llm_client.get_usage()`.
   - `rules`: Options `--adapter` (default "aws_sg"), `--sg-id` (required). Fetches rules via adapter and displays in Rich table.
   - `config`: Shows resolved `PolicyFoundryConfig` in Rich panel.
   - Global callback with `--debug` and `--verbose` options.
   - Error handler: `try/except PolicyFoundryError` at each command boundary → `console.print()` Rich error panel with error class, message, error_code, and details. With `--debug`, show full traceback.

4. **Create `__main__.py`** — Simple entry point: `from policyfoundry.main import app` then `def main(): app()`. Must match `policyfoundry.__main__:main`.

5. **Verify** — Safety tests pass, CLI `--help` works, entry point resolves.

## Must-Haves

- [ ] `SafetyError` is importable from `policyfoundry.exceptions` with `error_code="SAFETY_VIOLATION"`
- [ ] `ReadOnlyAdapter` delegates reads, raises `SafetyError` on writes — 6 safety tests pass
- [ ] `policyfoundry --help` shows `analyze`, `rules`, `config` commands
- [ ] `policyfoundry analyze --help` shows `--source`, `--format`, `--sg-ids`, `--debug` options
- [ ] Commands are sync with internal `asyncio.run()` (D027)
- [ ] `PolicyFoundryError` caught at command boundary → Rich error panel, not stack trace (D030)
- [ ] Rich `Status` spinner during pipeline stages
- [ ] `__main__.py` entry point works (`uv run policyfoundry --help`)

## Verification

- `uv run pytest tests/test_safety/ -x -v` → 6 tests pass (SAFE-01 proven)
- `uv run policyfoundry --help` → exit 0, shows analyze/rules/config
- `uv run policyfoundry analyze --help` → exit 0, shows --source/--format/--sg-ids
- `uv run python -c "from policyfoundry.exceptions import SafetyError; print(SafetyError.__bases__)"` → shows PolicyFoundryError

## Observability Impact

- Signals added/changed: CLI commands produce structured error output via PolicyFoundryError.error_code + details; Rich Status spinner shows pipeline stage names; token usage + cost displayed in output footer
- How a future agent inspects this: `policyfoundry config` shows resolved config; `policyfoundry analyze --debug` shows full tracebacks on error; `--format json` provides machine-parseable output
- Failure state exposed: Every PolicyFoundryError renders as a Rich panel showing error_code, message, and details dict — no raw tracebacks without --debug

## Inputs

- `src/policyfoundry/exceptions.py` from T02 (modify: add SafetyError)
- `src/policyfoundry/adapters/base.py` from T04 (FirewallAdapter ABC)
- `src/policyfoundry/config/loader.py` from T02 (load_config)
- `src/policyfoundry/pipeline/llm.py` from T06 (create_llm_client)
- `src/policyfoundry/pipeline/runner.py` from T06 (run_pipeline)
- `src/policyfoundry/adapters/registry.py` from T04 (AdapterRegistry)
- `src/policyfoundry/output/rich_output.py` from T05 (format_rich)
- `src/policyfoundry/output/json_output.py` from T05 (format_json)
- `tests/test_safety/test_readonly_adapter.py` from T11 (defines exact interface)
- Decisions D027, D030

## Expected Output

- `src/policyfoundry/exceptions.py` — modified with `SafetyError` added
- `src/policyfoundry/adapters/safety.py` — new `ReadOnlyAdapter` class
- `src/policyfoundry/main.py` — new Typer app with analyze/rules/config commands
- `src/policyfoundry/__main__.py` — new entry point
