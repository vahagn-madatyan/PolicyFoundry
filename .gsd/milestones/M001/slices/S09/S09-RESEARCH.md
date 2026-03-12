# S09 ("CLI Integration") — Research

**Date:** 2026-03-11

## Summary

S09 wires all upstream modules (config, ingestion, storage, adapters, pipeline, output) through a Typer CLI that a user can actually invoke. The core deliverables are: `main.py` (Typer app with `analyze`, `rules`, `config` commands), `__main__.py` (entry point), `adapters/safety.py` + `SafetyError` (carry-over from S08), and integration tests proving the full stack composes without error. This slice also owns the CLI's error-handling middleware, progress display during LLM inference, and `--help` text quality.

The biggest risk is **source code reconstruction** — all `.py` source files have been deleted from `src/` and `tests/`. Only `.pyc` bytecode remains in `__pycache__/` directories. The package is editable-installed so imports worked from bytecode, but no source exists for editing or extending. Before any S09 work can proceed, every module must be recovered from bytecode. This is a blocking prerequisite that changes the shape of the slice significantly.

Beyond reconstruction, the integration itself is straightforward: the upstream APIs are clean and well-factored. `load_config()` returns a typed `PolicyFoundryConfig`, `create_llm_client()` takes `LLMConfig`, `AdapterRegistry.get_adapter()` loads by name, `run_pipeline()` is async, and `format_rich()`/`format_json()` consume `PipelineState`. The CLI command functions are sync wrappers that call `asyncio.run()` for the async pipeline. Typer 0.24.1 is already installed and does **not** natively await async commands in CliRunner (verified: coroutine never awaited warning), so commands must be synchronous with internal `asyncio.run()`.

## Recommendation

**Approach: Reconstruct source → implement safety carry-over → build CLI → write integration tests.**

1. **Reconstruct all source files** from bytecode. The `.pyc` files contain complete code objects — use `decompyle3` or `pycdc` to recover Python source. This must happen first since S09 needs to edit `exceptions.py` (add `SafetyError`) and create new files (`main.py`, `__main__.py`, `adapters/safety.py`). Also reconstruct test files so the existing 300+ tests can verify nothing broke.

2. **Implement S08 carry-over** (`SafetyError` in `exceptions.py`, `ReadOnlyAdapter` in `adapters/safety.py`). Six tests already exist in bytecode at `tests/test_safety/test_readonly_adapter.py` — they import these exact symbols.

3. **Build the Typer CLI** (`main.py` with `analyze`, `rules`, `config` commands). The wiring follows a clear pattern: `load_config() → create_llm_client() → get_adapter() → ReadOnlyAdapter() → run_pipeline() → format_rich()/format_json()`. Add error handling middleware, Rich progress spinners, and `--help` text.

4. **Write integration tests** using `typer.testing.CliRunner`. Mock `LLMClient` and adapter at the boundary, exercise the real CLI entrypoint against fixture data, assert on exit codes and output content.

5. **Recreate `pyproject.toml`** — the file is missing. Package metadata exists in `.dist-info/` (deps, entry points) so reconstruction is deterministic.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI framework | Typer 0.24.1 (already installed) | Click-based, type-hint-driven, auto-generates `--help`, Rich bundled |
| CLI testing | `typer.testing.CliRunner` | In-process invocation, captures exit_code + output, no subprocess needed |
| Progress display | `rich.status.Status` context manager | Shows spinner with stage name during LLM calls; already a dep |
| Error formatting | `rich.console.Console.print_exception()` | Renders actionable errors without raw tracebacks |
| Bytecode recovery | `decompyle3` / `pycdc` | Recover `.py` from `.pyc` — don't rewrite 48 source + 44 test files by hand |
| Async-in-sync | `asyncio.run()` | Typer commands are sync; `run_pipeline()` is async. Wrap at command level |

## Existing Code and Patterns

- `src/policyfoundry/config/loader.py` (.pyc) — `load_config(**overrides) -> PolicyFoundryConfig`. Clean entry point for config; accepts override kwargs. CLI passes `--format`, `--source`, etc. as overrides.
- `src/policyfoundry/pipeline/runner.py` (.pyc) — `async run_pipeline(llm_client, adapter, data_dir, sg_ids) -> PipelineState`. The async function the CLI must call via `asyncio.run()`. Wraps errors in `PipelineError`.
- `src/policyfoundry/pipeline/llm.py` (.pyc) — `create_llm_client(config: LLMConfig) -> LLMClient`. Factory with Ollama health check. `LLMClient.get_usage() -> TokenUsage` for post-pipeline cost display.
- `src/policyfoundry/adapters/registry.py` (.pyc) — `AdapterRegistry.get_adapter(name, **kwargs) -> FirewallAdapter`. Static method; tries entry_points first, falls back to built-in `aws_sg`. Instantiates with `**kwargs`.
- `src/policyfoundry/adapters/aws_sg/adapter.py` (.pyc) — `AwsSecurityGroupAdapter(security_group_id, *, region=None)`. Constructor takes SG ID and optional region.
- `src/policyfoundry/output/rich_output.py` (.pyc) — `format_rich(state: PipelineState, *, console=None) -> None`. Renders summary, traffic analysis, assessment, proposals, decisions, token usage tables. Internal `_risk_text()` applies `RISK_COLORS` dict.
- `src/policyfoundry/output/json_output.py` (.pyc) — `format_json(state: PipelineState) -> str`. Uses `PipelineResult.from_state(state)` for typed serialization.
- `src/policyfoundry/output/models.py` (.pyc) — `TokenUsage` (dataclass with `add_call`, `to_dict`, `__add__`), `PipelineResult` (Pydantic with `from_state` classmethod).
- `src/policyfoundry/exceptions.py` (.pyc) — Full hierarchy: `PolicyFoundryError` (base with `error_code`, `details`), `ConfigError`, `IngestionError`, `AdapterError`, `PipelineError`, `OutputError`. **Missing: `SafetyError`** — must be added.
- `tests/test_safety/test_readonly_adapter.py` (.pyc) — 6 tests: delegates `get_rules`, `validate`, `capabilities`; blocks `apply_rule`, `apply_rules`; verifies `SafetyError` structured details. Imports `ReadOnlyAdapter` from `policyfoundry.adapters.safety` and `SafetyError` from `policyfoundry.exceptions`.
- `tests/test_output/conftest.py` (.pyc) — Fixtures: `sample_pipeline_state` (full 4-stage), `sample_pipeline_state_no_tokens`, `sample_pipeline_state_empty`. **Reusable for CLI integration tests.**
- `.venv/bin/policyfoundry` — Entry point script calling `policyfoundry.__main__:main`. Already registered but `__main__.py` doesn't exist.
- `.venv/lib/.../entry_points.txt` — Declares `policyfoundry = policyfoundry.__main__:main` and adapter entry point `aws_sg = policyfoundry.adapters.aws_sg:AwsSecurityGroupAdapter`.

## Constraints

- **All `.py` source files are deleted.** Only `.pyc` bytecode exists (48 src files, 44 test files). Source must be reconstructed before any S09 implementation can begin. This is a hard prerequisite.
- **`pyproject.toml` is missing.** Package metadata (deps, entry points, Python version) exists in `.dist-info/METADATA` and `entry_points.txt`. Must be reconstructed.
- **Typer does not natively await async commands.** Verified: `@app.command() async def ...` registers but `CliRunner.invoke()` produces "coroutine never awaited" warning. Commands must be sync functions using `asyncio.run()` internally.
- **`run_pipeline()` is async** — requires `asyncio.run()` wrapper at the CLI command level.
- **`AwsSecurityGroupAdapter.__init__` takes `security_group_id` + optional `region`** — not a list of SG IDs. The CLI `analyze` command must handle multiple SG IDs by running per-SG or iterating.
- **`AdapterRegistry.get_adapter(name, **kwargs)` returns an instantiated adapter** — kwargs flow through to the adapter constructor.
- **`load_config()` accepts no required args** — reads YAML + env vars automatically. CLI overrides go via `**overrides` kwargs.
- **`format_rich()` signature is `format_rich(state, *, console=None)`** — `console` is keyword-only, defaults to creating a new `Console()`.
- **Python 3.13** runtime (per `.venv/pyvenv.cfg`) — pyproject.toml says `>=3.12` but runtime is 3.13.
- **No `typer` in package dependencies** — it's installed in the venv but not listed in `Requires-Dist`. Must be added to `pyproject.toml` when reconstructed.
- **`instructor[litellm]>=1.14.5`** is the LLM dependency, not `langchain-litellm`. The project uses Instructor's `from_litellm()` pattern, not LangChain's `ChatLiteLLM`.

## Common Pitfalls

- **Async in Typer commands** — Declaring `async def` Typer commands silently fails; the coroutine is never awaited. Use sync commands with `asyncio.run()` for the pipeline call. Verified empirically with Typer 0.24.1.
- **Missing `__main__.py` crashes the `policyfoundry` CLI command** — The entry point at `.venv/bin/policyfoundry` imports `policyfoundry.__main__:main`. If this module doesn't exist, the CLI fails immediately with `ModuleNotFoundError`.
- **Config overrides vs. env vars** — `load_config()` already handles YAML + env var merge. CLI options (e.g., `--format json`) should be passed as overrides, not set as env vars, to preserve the priority chain: CLI flags > env vars > YAML.
- **AdapterRegistry returns a class instance, not a class** — `get_adapter(name, **kwargs)` instantiates. Don't try to call the result as a constructor again.
- **ReadOnlyAdapter tests expect specific import paths** — Tests import `from policyfoundry.adapters.safety import ReadOnlyAdapter` and `from policyfoundry.exceptions import SafetyError`. The implementation must match these exact module paths.
- **Stack traces in user-facing output** — All `PolicyFoundryError` subtypes must be caught at the CLI boundary and rendered as actionable Rich-formatted messages. Raw tracebacks should only appear with `--debug` flag.
- **Multiple SG IDs with single-SG adapter** — `AwsSecurityGroupAdapter` takes one `security_group_id`. The `analyze` command (which accepts `targets.security_group_ids` as a list) needs to either iterate or use the first ID. The pipeline runner takes `sg_ids: list[str]`, but the adapter is per-SG. Resolution: the pipeline may handle this internally, or the CLI iterates.
- **Bytecode reconstruction fidelity** — Decompiled code may have formatting differences, lost comments, and slightly different variable names. Tests are the ground truth: all 300+ must pass after reconstruction.

## Open Risks

- **Source reconstruction completeness** — Bytecode decompilation can fail on complex constructs (match statements, walrus operators, complex comprehensions in Python 3.13). Some files may need manual correction after decompilation. Risk: MEDIUM. Mitigation: run all existing tests after reconstruction to verify fidelity.
- **Decompiler availability for Python 3.13** — `decompyle3` may not fully support CPython 3.13 bytecode. `pycdc` (C++ based) has broader version support but sometimes produces invalid Python. May need to use Python's `dis` module as fallback and reconstruct manually for problematic files.
- **Integration test mock boundaries** — The CLI integration tests need to mock `LLMClient` and `AwsSecurityGroupAdapter` (external services) while keeping the real config, ingestion, storage, and output modules. Getting the mock injection right without modifying production code (dependency injection vs. monkeypatching) requires careful design.
- **CliRunner async interaction** — While sync commands with `asyncio.run()` work, CliRunner may have edge cases with Rich console output capture. Rich's `Console(file=...)` redirect may conflict with CliRunner's output capture. Need to verify Rich output appears in `result.output`.
- **Token usage display** — `LLMClient.get_usage()` returns `TokenUsage` which is separate from `PipelineState`. The CLI must call `get_usage()` after the pipeline run and either inject it into the state's `token_usage` field or pass it separately to the formatter.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | `narumiruna/agent-skills@python-cli-typer` (13 installs) | available — Typer-specific patterns |
| Typer CLI | `0xdarkmatter/claude-mods@python-cli-patterns` (29 installs) | available — general CLI patterns |
| Python CLI | `wdm0006/python-skills@building-python-clis` (18 installs) | available — broader CLI building |
| pytest | `manutej/luxor-claude-marketplace@pytest-patterns` (117 installs) | available — high install count, general pytest |

None of these are critical for the work — Typer and pytest are well-documented and the existing codebase patterns are clear. The pytest-patterns skill has high installs and could be useful for integration test design.

## Sources

- Typer 0.24.1 async behavior verified empirically — `CliRunner.invoke()` on async commands produces "coroutine never awaited" warning; sync wrappers with `asyncio.run()` required (source: local verification)
- Typer testing uses `CliRunner.invoke(app, args)` returning `Result` with `.exit_code`, `.output`, `.stdout` (source: [Typer Testing Docs](https://typer.tiangolo.com/tutorial/testing/))
- Typer supports `str Enum` for `--format` option with auto-generated help (source: [Typer CLI Option Tutorial](https://typer.tiangolo.com/tutorial/parameter-types/enum/))
- `@app.callback()` enables global options (e.g., `--debug`, `--verbose`) shared across commands (source: [Typer Callback Docs](https://typer.tiangolo.com/tutorial/commands/callback/))
- Rich `Status` context manager provides spinners for unknown-duration operations (source: [Typer Progress Bar Docs](https://typer.tiangolo.com/tutorial/progressbar/))
- Package metadata reconstructed from `.dist-info/METADATA` — dependencies include `aiofiles`, `boto3`, `duckdb`, `instructor[litellm]`, `langgraph`, `pyarrow`, `pydantic`, `pydantic-settings[yaml]`, `pytz`, `rich`. Missing: `typer` (source: local `.dist-info/METADATA`)
- Entry point is `policyfoundry = policyfoundry.__main__:main` (source: local `.dist-info/entry_points.txt`)
- All 48 src and 44 test `.py` files deleted — only `.pyc` bytecode remains (source: filesystem inspection)
- S08 carry-over: 6 `ReadOnlyAdapter` tests import `SafetyError` from `policyfoundry.exceptions` and `ReadOnlyAdapter` from `policyfoundry.adapters.safety` — neither exists in current bytecode (source: bytecode analysis of `test_readonly_adapter.cpython-313-pytest-9.0.2.pyc`)
