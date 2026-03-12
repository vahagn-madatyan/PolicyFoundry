# S09: CLI Integration

**Goal:** Wire all upstream modules through a Typer CLI so users can run `policyfoundry analyze` and `policyfoundry rules` from the terminal, with Rich or JSON output, suggest-only safety, token cost display, and actionable error messages.

**Demo:** User runs `policyfoundry analyze --source local --format rich` (with mocked LLM) and sees a Rich report with traffic analysis, rule proposals, color-coded risk tables, and token cost summary. `--format json` emits valid JSON. `policyfoundry rules` displays current SG rules. `policyfoundry config` shows resolved config. ReadOnlyAdapter blocks any write attempt with `SafetyError`. All 300+ pre-existing tests pass after source reconstruction from bytecode.

## Must-Haves

- All 48 src `.py` files reconstructed from `.pyc` bytecode and importable
- All 44 test `.py` files reconstructed from `.pyc` bytecode
- `pyproject.toml` reconstructed with all dependencies (including `typer`) and entry points
- Full pre-existing test suite (300+ tests from S01–S08) passes with zero regressions
- `SafetyError` added to `policyfoundry.exceptions` hierarchy
- `ReadOnlyAdapter` in `policyfoundry.adapters.safety` — delegates reads, raises `SafetyError` on writes
- 6 pre-existing safety tests pass (`tests/test_safety/test_readonly_adapter.py`)
- `policyfoundry analyze` command: `--source`, `--format`, `--sg-ids` options; wires config → LLM → adapter → ReadOnlyAdapter → pipeline → formatter
- `policyfoundry rules` command: fetches and displays current SG rules via adapter
- `policyfoundry config` command: shows resolved configuration
- All commands have useful `--help` text
- CLI catches `PolicyFoundryError` subtypes at the boundary → Rich-formatted actionable messages (not stack traces)
- Rich `Status` spinner during LLM inference stages
- Token usage and estimated cost displayed in output footer
- `--format json` produces valid, parseable JSON with all pipeline stage data
- `__main__.py` entry point matches `policyfoundry.__main__:main` in entry_points
- CLI integration tests exercise analyze/rules/config commands with mocked LLM and adapter

## Proof Level

- This slice proves: integration (real module composition through CLI entrypoint with mocked external services)
- Real runtime required: no (LLM and AWS adapter are mocked; config, ingestion, storage, output are real)
- Human/UAT required: yes (S09 UAT per roadmap — user visually confirms Rich output quality)

## Verification

- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ tests/test_adapters/ tests/test_output/ tests/test_pipeline/ -x` → all pre-existing tests pass (proves reconstruction fidelity)
- `uv run pytest tests/test_safety/ -x` → 6 safety tests pass (proves SAFE-01: ReadOnlyAdapter + SafetyError)
- `uv run pytest tests/test_cli/ -x` → CLI integration tests pass (proves OUT-01, OUT-02, SAFE-02, CLI error handling)
- `uv run policyfoundry --help` → exits 0, shows commands: analyze, rules, config
- `uv run policyfoundry analyze --help` → exits 0, shows --source, --format, --sg-ids options
- Observability check: CLI integration test verifies that `PolicyFoundryError` subtypes produce exit code 1 + actionable message (not a traceback)

## Observability / Diagnostics

- Runtime signals: CLI commands log structured error context via `PolicyFoundryError.error_code` and `PolicyFoundryError.details` dict; Rich `Status` spinner shows current pipeline stage name during inference
- Inspection surfaces: `policyfoundry config` command dumps resolved config; `--debug` flag enables full tracebacks; `--format json` provides machine-parseable pipeline output
- Failure visibility: Every `PolicyFoundryError` subtype carries `error_code` (str) and `details` (dict) that the CLI renders as a Rich panel with the error class name, message, and relevant context (e.g., which config key failed, which pipeline stage errored)
- Redaction constraints: No API keys or credentials in CLI output; token usage shows counts and cost estimates only

## Integration Closure

- Upstream surfaces consumed: `config.loader.load_config()`, `pipeline.llm.create_llm_client()`, `adapters.registry.AdapterRegistry.get_adapter()`, `pipeline.runner.run_pipeline()`, `output.rich_output.format_rich()`, `output.json_output.format_json()`, `output.models.TokenUsage`, `exceptions.PolicyFoundryError` hierarchy, `adapters.base.FirewallAdapter` ABC
- New wiring introduced in this slice: `main.py` Typer app composes all upstream modules through CLI commands; `__main__.py` entry point registered in `pyproject.toml`; `adapters/safety.py` ReadOnlyAdapter wraps any FirewallAdapter; `SafetyError` added to exception hierarchy; `pyproject.toml` restored with full package definition
- What remains before the milestone is truly usable end-to-end: S10 (Terraform infra, Docker packaging, E2E test against real/fixture data)

## Tasks

> **Note on task count:** This slice has 13 tasks due to the unprecedented requirement of reconstructing 92 source files from CPython 3.13 bytecode (D028, D029). Tasks T01–T11 handle reconstruction and verification; T12–T13 deliver the new CLI functionality. The reconstruction is a hard prerequisite (D028) and the slice was elevated to HIGH risk specifically for this reason (D029).

- [x] **T01: Build bytecode inspection toolkit, reconstruct pyproject.toml, create failing CLI test stubs** `est:1h`
  - Why: Establishes reconstruction tooling and verification-first test stubs before any source recovery begins. The decompilation toolkit is used by all subsequent reconstruction tasks. The failing test stubs define the done condition for the entire slice.
  - Files: `tools/inspect_pyc.py`, `pyproject.toml`, `tests/test_cli/__init__.py`, `tests/test_cli/conftest.py`, `tests/test_cli/test_analyze.py`, `tests/test_cli/test_rules.py`, `tests/test_cli/test_config.py`
  - Do: Build a Python script using `dis` + `marshal` + `types` that extracts structure from .pyc files (imports, class defs, function signatures, docstrings, constants). Reconstruct `pyproject.toml` from `.dist-info/METADATA` + `entry_points.txt`, adding `typer>=0.15` to deps. Create CLI integration test stubs with test function signatures and `pytest.skip("not yet implemented")` or direct assertions that will fail until T12–T13.
  - Verify: `uv run python tools/inspect_pyc.py src/policyfoundry/__pycache__/exceptions.cpython-313.pyc` produces structured output; `uv sync` succeeds with reconstructed `pyproject.toml`; `uv run pytest tests/test_cli/ -x` runs but tests fail (expected — no CLI yet)
  - Done when: Toolkit extracts class/function names from any .pyc file, pyproject.toml is valid, CLI test stubs exist and fail

- [x] **T02: Reconstruct src root and config module from bytecode** `est:2h`
  - Why: Root `exceptions.py` defines the entire error hierarchy used by all modules. Config module is the first thing the CLI calls (`load_config()`). Both are prerequisites for everything downstream.
  - Files: `src/policyfoundry/__init__.py`, `src/policyfoundry/exceptions.py`, `src/policyfoundry/config/__init__.py`, `src/policyfoundry/config/defaults.py`, `src/policyfoundry/config/models.py`, `src/policyfoundry/config/validation.py`, `src/policyfoundry/config/loader.py`
  - Do: Use the T01 toolkit + `dis` disassembly via `.venv/bin/python3` to reconstruct each file. For Pydantic models in `config/models.py`, extract field names, types, and defaults from code object constants. For `exceptions.py`, reconstruct the class hierarchy (all leaf exception classes). Verify each module imports cleanly.
  - Verify: `uv run python -c "from policyfoundry.exceptions import PolicyFoundryError, ConfigError, PipelineError; print('OK')"` and `uv run python -c "from policyfoundry.config.loader import load_config; print('OK')"`
  - Done when: All 7 files exist as `.py`, all config and exception classes importable with correct signatures

- [x] **T03: Reconstruct src ingestion module from bytecode** `est:2h`
  - Why: Ingestion module (schema, parser, dedup, local/S3 file readers) is consumed by the pipeline runner via `ingest_local_files()`. Must exist before pipeline integration.
  - Files: `src/policyfoundry/ingestion/__init__.py`, `src/policyfoundry/ingestion/schema.py`, `src/policyfoundry/ingestion/parser.py`, `src/policyfoundry/ingestion/dedup.py`, `src/policyfoundry/ingestion/result.py`, `src/policyfoundry/ingestion/local.py`, `src/policyfoundry/ingestion/s3.py`
  - Do: Reconstruct each file from bytecode. Parser has complex regex for VPC Flow Log v2 format — extract pattern strings from code constants. Local/S3 ingestion are async functions — ensure `async def` signatures.
  - Verify: `uv run python -c "from policyfoundry.ingestion.local import ingest_local_files; from policyfoundry.ingestion.parser import parse_flow_log_line; print('OK')"`
  - Done when: All 7 ingestion files exist as `.py` and import without error

- [x] **T04: Reconstruct src storage and adapters core from bytecode** `est:2h`
  - Why: Storage layer (Parquet writer, DuckDB queries) and adapter framework (ABC, schema, registry) are both consumed by the pipeline. The adapter schema defines `UniversalRule`, `RiskLevel`, and other critical types used throughout.
  - Files: `src/policyfoundry/storage/__init__.py`, `src/policyfoundry/storage/models.py`, `src/policyfoundry/storage/parquet_schema.py`, `src/policyfoundry/storage/writer.py`, `src/policyfoundry/storage/queries.py`, `src/policyfoundry/adapters/__init__.py`, `src/policyfoundry/adapters/base.py`, `src/policyfoundry/adapters/schema.py`, `src/policyfoundry/adapters/registry.py`
  - Do: Reconstruct storage module (writer is async, queries use DuckDB SQL). Reconstruct adapter core: `FirewallAdapter` ABC with abstract methods (`get_rules`, `validate`, `apply_rule`, `apply_rules`, `capabilities`), `AdapterRegistry` with `get_adapter()` static method, and the full schema module with `RiskLevel` StrEnum, `UniversalRule`, `ValidationResult`, `AdapterCapabilities`, `Direction`, `RuleAction`, `PortRange`, `NetworkEndpoint`.
  - Verify: `uv run python -c "from policyfoundry.adapters.schema import RiskLevel, UniversalRule; from policyfoundry.adapters.registry import AdapterRegistry; from policyfoundry.storage.writer import write_records; print('OK')"`
  - Done when: All 9 files exist as `.py` and import correctly

- [x] **T05: Reconstruct src AWS SG adapter and output module from bytecode** `est:2h`
  - Why: AWS SG adapter (translator, client, adapter) implements the concrete `FirewallAdapter` for Security Groups. Output module (Rich formatter, JSON formatter, models) renders pipeline results to the terminal. Both are consumed directly by CLI commands.
  - Files: `src/policyfoundry/adapters/aws_sg/__init__.py`, `src/policyfoundry/adapters/aws_sg/translator.py`, `src/policyfoundry/adapters/aws_sg/client.py`, `src/policyfoundry/adapters/aws_sg/adapter.py`, `src/policyfoundry/output/__init__.py`, `src/policyfoundry/output/models.py`, `src/policyfoundry/output/json_output.py`, `src/policyfoundry/output/rich_output.py`
  - Do: Reconstruct AWS SG adapter: translator has static methods for rule conversion, client wraps boto3, adapter implements `FirewallAdapter` ABC. Reconstruct output: `TokenUsage` dataclass, `PipelineResult` Pydantic model with `from_state` classmethod, `format_rich()` with Rich tables and `RISK_COLORS` dict, `format_json()` via `PipelineResult`.
  - Verify: `uv run python -c "from policyfoundry.adapters.aws_sg.adapter import AwsSecurityGroupAdapter; from policyfoundry.output.rich_output import format_rich; from policyfoundry.output.json_output import format_json; print('OK')"`
  - Done when: All 8 files exist as `.py` and import correctly

- [x] **T06: Reconstruct src pipeline core and prompts from bytecode** `est:2h`
  - Why: Pipeline module is the heart of the system — LLM client, LangGraph graph definition, pipeline runner, and prompt templates. The CLI's `analyze` command calls `run_pipeline()` which orchestrates everything.
  - Files: `src/policyfoundry/pipeline/__init__.py`, `src/policyfoundry/pipeline/state.py`, `src/policyfoundry/pipeline/schema.py`, `src/policyfoundry/pipeline/llm.py`, `src/policyfoundry/pipeline/graph.py`, `src/policyfoundry/pipeline/runner.py`, `src/policyfoundry/pipeline/prompts/__init__.py`, `src/policyfoundry/pipeline/prompts/analyze.py`, `src/policyfoundry/pipeline/prompts/assess.py`, `src/policyfoundry/pipeline/prompts/generate.py`, `src/policyfoundry/pipeline/prompts/decide.py`
  - Do: Reconstruct `PipelineState` TypedDict (total=False, per D003). Reconstruct `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision` Pydantic models. Reconstruct `LLMClient` with Instructor/LiteLLM integration (per D018, D019, D020) and `get_usage() -> TokenUsage`. Reconstruct `build_pipeline()` returning LangGraph `CompiledGraph`. Reconstruct `run_pipeline()` async function. Reconstruct prompt template strings — these are string constants extractable from bytecode.
  - Verify: `uv run python -c "from policyfoundry.pipeline.runner import run_pipeline; from policyfoundry.pipeline.llm import create_llm_client, LLMClient; from policyfoundry.pipeline.graph import build_pipeline; print('OK')"`
  - Done when: All 11 files exist as `.py` and import correctly

- [x] **T07: Reconstruct src pipeline stages from bytecode** `est:1.5h`
  - Why: Five pipeline stage functions (analyze, assess, generate, validate, decide) are the LangGraph nodes that execute the AI pipeline. Each stage reads from `PipelineState`, calls LLM or adapter, and returns state updates.
  - Files: `src/policyfoundry/pipeline/stages/__init__.py`, `src/policyfoundry/pipeline/stages/analyze.py`, `src/policyfoundry/pipeline/stages/assess.py`, `src/policyfoundry/pipeline/stages/generate.py`, `src/policyfoundry/pipeline/stages/validate.py`, `src/policyfoundry/pipeline/stages/decide.py`
  - Do: Each stage follows a common pattern: extract data from state → format prompt → call LLM (or adapter for validate, per D026) → return dict update. Reconstruct using bytecode structure + patterns from D021 (PipelineContext DI), D022 (dict return), D024 (empty proposals handling), D025 (temperature settings). Validate stage is non-LLM (D026).
  - Verify: `uv run python -c "from policyfoundry.pipeline.stages import analyze_stage, assess_stage, generate_stage, validate_stage, decide_stage; print('OK')"`
  - Done when: All 6 stage files exist as `.py`, all stage functions importable

- [x] **T08: Reconstruct test files — root, models, config, exceptions** `est:2h`
  - Why: These tests verify the foundational layers (domain models, config system, exception hierarchy) reconstructed in T02. Running them is the primary fidelity check for reconstruction quality.
  - Files: `tests/__init__.py`, `tests/conftest.py`, `tests/test_models/__init__.py`, `tests/test_models/test_flow_log.py`, `tests/test_models/test_universal_rule.py`, `tests/test_models/test_pipeline_state.py`, `tests/test_models/test_pipeline_schema.py`, `tests/test_config/__init__.py`, `tests/test_config/conftest.py`, `tests/test_config/test_loader.py`, `tests/test_config/test_models.py`, `tests/test_config/test_validation.py`, `tests/test_exceptions/__init__.py`, `tests/test_exceptions/test_exceptions.py`
  - Do: Reconstruct all test files from bytecode using `.venv/bin/python3` for `dis`. Extract test function names, fixture references, assertion patterns from code objects. `__init__.py` files are empty. `conftest.py` files contain shared fixtures. Run reconstructed tests against reconstructed src.
  - Verify: `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ -x -v 2>&1 | tail -5` → all tests pass
  - Done when: All tests in these 3 test modules + root pass

- [x] **T09: Reconstruct test files — ingestion, storage** `est:2h`
  - Why: Ingestion and storage tests verify the data pipeline (parsing, dedup, Parquet writing, DuckDB queries). These are medium-to-large test files with complex fixtures.
  - Files: `tests/test_ingestion/__init__.py`, `tests/test_ingestion/conftest.py`, `tests/test_ingestion/test_local.py`, `tests/test_ingestion/test_dedup.py`, `tests/test_ingestion/test_parser.py`, `tests/test_ingestion/test_s3.py`, `tests/test_storage/__init__.py`, `tests/test_storage/conftest.py`, `tests/test_storage/test_queries.py`, `tests/test_storage/test_writer.py`
  - Do: Reconstruct test files from bytecode. Ingestion tests use sample flow log lines as fixtures. Storage tests use tmp_path for Parquet files and DuckDB. S3 tests use moto mocks (per D012).
  - Verify: `uv run pytest tests/test_ingestion/ tests/test_storage/ -x -v 2>&1 | tail -5` → all tests pass
  - Done when: All ingestion and storage tests pass

- [x] **T10: Reconstruct test files — adapters, output** `est:2h`
  - Why: Adapter tests verify SG translation, validation, and registry. Output tests verify Rich formatting and JSON serialization. Both are needed before CLI integration tests.
  - Files: `tests/test_adapters/__init__.py`, `tests/test_adapters/conftest.py`, `tests/test_adapters/test_registry.py`, `tests/test_adapters/test_schema.py`, `tests/test_adapters/test_validation.py`, `tests/test_adapters/test_aws_sg_translator.py`, `tests/test_adapters/test_aws_sg_adapter.py`, `tests/test_output/__init__.py`, `tests/test_output/conftest.py`, `tests/test_output/test_json_output.py`, `tests/test_output/test_rich_output.py`, `tests/test_output/test_models.py`
  - Do: Reconstruct from bytecode. Adapter tests use moto for AWS mocking and test the full translate → validate → capabilities flow. Output tests use `sample_pipeline_state` fixture from `test_output/conftest.py` (reusable for CLI tests). Output conftest is critical — it defines the pipeline state fixture used by T13.
  - Verify: `uv run pytest tests/test_adapters/ tests/test_output/ -x -v 2>&1 | tail -5` → all tests pass
  - Done when: All adapter and output tests pass

- [x] **T11: Reconstruct test files — pipeline, safety — and verify full test suite** `est:2h`
  - Why: Pipeline tests are the largest test module (62 tests per roadmap) verifying the 5-stage LangGraph pipeline. Safety tests define the exact interface for `ReadOnlyAdapter` and `SafetyError` that T12 must implement. Running the full suite proves reconstruction fidelity across all 300+ tests.
  - Files: `tests/test_pipeline/__init__.py`, `tests/test_pipeline/conftest.py`, `tests/test_pipeline/test_stages.py`, `tests/test_pipeline/test_llm.py`, `tests/test_pipeline/test_prompts.py`, `tests/test_pipeline/test_graph.py`, `tests/test_safety/__init__.py`, `tests/test_safety/test_readonly_adapter.py`
  - Do: Reconstruct pipeline test files (large — test_stages and test_llm are the biggest test files in the project). Reconstruct safety tests (6 tests importing `ReadOnlyAdapter` from `policyfoundry.adapters.safety` and `SafetyError` from `policyfoundry.exceptions`). Run pipeline tests (safety tests expected to fail — no implementation yet). Then run full suite across all reconstructed tests; fix any reconstruction issues.
  - Verify: `uv run pytest tests/test_pipeline/ -x -v 2>&1 | tail -5` → pipeline tests pass; `uv run pytest tests/ --ignore=tests/test_safety --ignore=tests/test_cli -x -q 2>&1 | tail -3` → all non-safety, non-CLI tests pass
  - Done when: Full test suite passes (excluding test_safety and test_cli); safety test files exist and importable

- [ ] **T12: Implement SafetyError, ReadOnlyAdapter, and build Typer CLI** `est:2h`
  - Why: This is the core deliverable of S09 — the actual CLI that users run. SafetyError + ReadOnlyAdapter implement SAFE-01 (suggest-only mode). The Typer app with analyze/rules/config commands implements OUT-01, OUT-02, and SAFE-02 through the CLI surface.
  - Files: `src/policyfoundry/exceptions.py` (modify), `src/policyfoundry/adapters/safety.py` (new), `src/policyfoundry/main.py` (new), `src/policyfoundry/__main__.py` (new)
  - Do: (1) Add `SafetyError(PolicyFoundryError)` to exceptions.py with error_code="SAFETY_VIOLATION". (2) Create `ReadOnlyAdapter(FirewallAdapter)` in `adapters/safety.py` — delegates `get_rules`, `validate`, `capabilities`; raises `SafetyError` on `apply_rule`/`apply_rules`. (3) Create `main.py` with Typer app: `analyze` command (sync wrapper → asyncio.run → load_config → create_llm_client → get_adapter → ReadOnlyAdapter → run_pipeline → format_rich/format_json + token usage), `rules` command (fetch + display SG rules), `config` command (show resolved config). (4) Create `__main__.py` calling `main()`. (5) Wire CLI error handler: catch PolicyFoundryError → Rich console error panel; `--debug` flag for full tracebacks. (6) Add Rich Status spinner for pipeline stages.
  - Verify: `uv run pytest tests/test_safety/ -x -v` → 6 safety tests pass; `uv run policyfoundry --help` → exits 0, shows commands; `uv run policyfoundry analyze --help` → shows options
  - Done when: Safety tests pass, CLI commands show help, entry point works

- [ ] **T13: Complete CLI integration tests and final slice verification** `est:1.5h`
  - Why: Integration tests prove the full stack composes through the real CLI entrypoint. This is the final proof for OUT-01, OUT-02, SAFE-01, SAFE-02. Without these tests, we only have unit coverage — the real composition hasn't been exercised.
  - Files: `tests/test_cli/conftest.py` (complete), `tests/test_cli/test_analyze.py` (complete), `tests/test_cli/test_rules.py` (complete), `tests/test_cli/test_config.py` (complete)
  - Do: Complete CLI integration test stubs from T01 with real assertions. Use `typer.testing.CliRunner` to invoke commands. Mock `LLMClient` and `AwsSecurityGroupAdapter` at the boundary (monkeypatch). Use `sample_pipeline_state` fixture pattern from `test_output/conftest.py`. Test: (1) analyze with --format rich → exit 0, output contains risk table headers and token usage. (2) analyze with --format json → exit 0, output is valid JSON with pipeline stages. (3) rules → exit 0, output contains rule data. (4) config → exit 0, output contains config keys. (5) error handling: invalid config → exit 1, actionable message, no traceback. Run full test suite including CLI tests.
  - Verify: `uv run pytest tests/test_cli/ -x -v` → all CLI tests pass; `uv run pytest tests/ -x -q` → entire suite (300+ tests) passes
  - Done when: All CLI integration tests pass, full suite green, all requirements verified

## Files Likely Touched

- `pyproject.toml` (reconstructed)
- `tools/inspect_pyc.py` (new — decompilation toolkit)
- `src/policyfoundry/**/*.py` (48 files reconstructed from bytecode)
- `src/policyfoundry/adapters/safety.py` (new)
- `src/policyfoundry/main.py` (new)
- `src/policyfoundry/__main__.py` (new)
- `tests/**/*.py` (44 files reconstructed from bytecode)
- `tests/test_cli/*.py` (4 new files)
