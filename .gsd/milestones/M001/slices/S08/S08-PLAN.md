# S08: Output And Safety

**Goal:** Pipeline results render as Rich terminal tables with color-coded risk levels or export as structured JSON. LLMClient tracks token usage and cost per stage. ReadOnlyAdapter wrapper enforces suggest-only mode. All verified against realistic pipeline output fixtures.
**Demo:** Running `pytest tests/test_output/ tests/test_safety/` passes all tests proving: (1) Rich formatter produces risk-colored tables with traffic analysis, proposals, decisions, and cost footer; (2) JSON formatter serializes full pipeline state to valid JSON; (3) LLMClient accumulates token usage across `complete()` calls and surfaces it via `get_usage()`; (4) ReadOnlyAdapter delegates reads and raises SafetyError on any write attempt.

## Must-Haves

- Rich formatter renders TrafficAnalysis summary panel, SecurityAssessment risk display, PolicyProposal details, RuleDecision color-coded table, and TokenUsage cost footer from PipelineState
- JSON formatter serializes PipelineState (with reconstructed Pydantic models) to valid, parseable JSON with all stage data
- LLMClient.complete() captures token usage (prompt_tokens, completion_tokens, total_tokens, cost) from Instructor's create_with_completion() response
- LLMClient accumulates usage across multiple calls and exposes get_usage() → TokenUsage
- PipelineState extended with token_usage dict field (TypedDict total=False)
- SafetyError exception added to hierarchy (inherits PolicyFoundryError)
- ReadOnlyAdapter wraps any FirewallAdapter, delegates get_rules/validate/capabilities, raises SafetyError on any write-like method
- PipelineResult Pydantic model wraps PipelineState with typed stage outputs for clean serialization
- Rich added as direct dependency (not just transitive via instructor)
- RiskLevel → color mapping centralized in a single dict (LOW→green, MEDIUM→yellow, HIGH→red, CRITICAL→bold red)

## Proof Level

- This slice proves: contract
- Real runtime required: no (all tests use mocks and fixtures)
- Human/UAT required: no (visual Rich output quality verified in S09 UAT)

## Verification

- `pytest tests/test_output/ -v` — all output formatter tests pass (Rich rendering produces expected table/panel content, JSON is valid and contains all stage data)
- `pytest tests/test_safety/ -v` — ReadOnlyAdapter delegates reads, raises SafetyError on writes; SafetyError has correct error_code
- `pytest tests/test_pipeline/test_llm.py -v` — existing tests still pass plus new token tracking tests (usage accumulation, cost from response, graceful None handling)
- `cd src && python -m pyright` — strict mode passes on all new src/ files
- `ruff check src/ tests/` — no lint violations
- At least one test verifies token_usage absent in PipelineState is handled gracefully by formatters (backward compat)

## Observability / Diagnostics

- Runtime signals: TokenUsage dataclass captures per-call and cumulative token counts; cost field set to 0.0 for local Ollama models with logged info message
- Inspection surfaces: `LLMClient.get_usage()` returns current accumulated TokenUsage; `PipelineResult.token_usage` field in JSON output
- Failure visibility: SafetyError carries `error_code="SAFETY_WRITE_BLOCKED"` with details dict naming the attempted method; OutputError carries `error_code="OUTPUT_RENDER_FAILED"` or `"OUTPUT_SERIALIZE_FAILED"`
- Redaction constraints: none (no secrets in output layer)

## Integration Closure

- Upstream surfaces consumed: `PipelineState` (pipeline/state.py), `run_pipeline()` (pipeline/runner.py), `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision` (pipeline/schema.py), `RiskLevel` (adapters/schema.py), `FirewallAdapter` ABC (adapters/base.py), `LLMClient` (pipeline/llm.py), exception hierarchy (exceptions.py)
- New wiring introduced in this slice: `output/` package (formatters consume PipelineState), modified LLMClient return path (create_with_completion), `adapters/safety.py` (ReadOnlyAdapter wraps FirewallAdapter), `output/models.py` (PipelineResult bridges state→serialization)
- What remains before the milestone is truly usable end-to-end: S09 CLI wires config→ingestion→storage→adapter→pipeline→output through `policyfoundry analyze` command; S10 packages in Docker with Terraform infra

## Tasks

- [x] **T01: Create test skeletons and shared fixtures for output, safety, and token tracking** `est:45m`
  - Why: Define the verification targets upfront — all test files with real assertions that initially fail, plus shared fixtures (realistic PipelineState, TokenUsage mocks) reused across tasks
  - Files: `tests/test_output/__init__.py`, `tests/test_output/conftest.py`, `tests/test_output/test_rich_output.py`, `tests/test_output/test_json_output.py`, `tests/test_output/test_models.py`, `tests/test_safety/__init__.py`, `tests/test_safety/test_read_only_adapter.py`, `tests/test_safety/test_safety_error.py`
  - Do: Create test directories and files. Build conftest.py with realistic PipelineState fixture (all stages populated), sample TokenUsage fixture, and mock Console. Write failing tests: Rich output tests assert on table content/colors, JSON tests assert on valid JSON with all keys, safety tests assert on SafetyError raise and delegation, model tests assert PipelineResult round-trip. Import from not-yet-existing modules so tests fail with ImportError.
  - Verify: `pytest tests/test_output/ tests/test_safety/ --collect-only` collects all tests; `pytest tests/test_output/ tests/test_safety/` fails (ImportError — modules don't exist yet)
  - Done when: All test files exist, pytest collects them, and they fail for the right reason (missing modules, not syntax errors)

- [x] **T02: Add SafetyError, TokenUsage model, extend PipelineState, and implement ReadOnlyAdapter** `est:40m`
  - Why: Delivers SAFE-01 (suggest-only enforcement) and SAFE-02 foundation (TokenUsage data model). These are leaf modules with no dependencies on the output layer, so they can be built and verified first.
  - Files: `src/policyfoundry/exceptions.py`, `src/policyfoundry/output/__init__.py`, `src/policyfoundry/output/models.py`, `src/policyfoundry/adapters/safety.py`, `src/policyfoundry/pipeline/state.py`
  - Do: Add SafetyError to exceptions.py (error_code="SAFETY_WRITE_BLOCKED"). Create output/models.py with TokenUsage dataclass (prompt_tokens, completion_tokens, total_tokens, cost, per_stage list) and PipelineResult Pydantic model that reconstructs typed stage outputs from PipelineState dicts. Add token_usage field to PipelineState TypedDict. Create adapters/safety.py with ReadOnlyAdapter that wraps FirewallAdapter, delegates get_rules/validate/capabilities, raises SafetyError on __getattr__ for any write-like method name. Scaffold output/__init__.py.
  - Verify: `pytest tests/test_safety/ -v` passes; `pytest tests/test_output/test_models.py -v` passes; `pyright src/policyfoundry/exceptions.py src/policyfoundry/output/models.py src/policyfoundry/adapters/safety.py src/policyfoundry/pipeline/state.py` clean
  - Done when: SafetyError tests pass, ReadOnlyAdapter delegation + write-block tests pass, PipelineResult round-trip tests pass, pyright strict clean on new files

- [x] **T03: Modify LLMClient to track token usage via create_with_completion** `est:45m`
  - Why: Delivers SAFE-02 (token usage and cost tracking). The LLMClient must switch from create() to create_with_completion() to capture the raw response with usage metadata, accumulate across calls, and expose via get_usage().
  - Files: `src/policyfoundry/pipeline/llm.py`, `tests/test_pipeline/test_llm.py`
  - Do: Import TokenUsage from output.models. Add _usage accumulator to LLMClient.__init__. Change _call_with_retry to use create_with_completion() returning tuple[T, Any]. Extract usage from raw response via getattr(response, 'usage', None). Extract cost via response._hidden_params.get("response_cost", 0.0) with fallback. Accumulate into _usage. Add get_usage() → TokenUsage and reset_usage() methods. Update complete() to unpack tuple. Add new tests: usage accumulation across multiple calls, graceful handling when usage is None, cost extraction, get_usage/reset_usage. Ensure all existing LLM tests still pass (mock return values now need to be tuples).
  - Verify: `pytest tests/test_pipeline/test_llm.py -v` — all existing + new tests pass; `pyright src/policyfoundry/pipeline/llm.py` clean
  - Done when: LLMClient.get_usage() returns accumulated TokenUsage after multiple complete() calls; existing retry/error tests unbroken; pyright strict passes

- [x] **T04: Implement Rich and JSON formatters with risk-colored output** `est:50m`
  - Why: Delivers OUT-01 (Rich terminal display) and OUT-02 (JSON export). These consume PipelineState and TokenUsage to produce the user-facing output that S09 CLI will invoke.
  - Files: `src/policyfoundry/output/rich_output.py`, `src/policyfoundry/output/json_output.py`, `src/policyfoundry/output/__init__.py`, `pyproject.toml`
  - Do: Add `rich>=14.0` as direct dependency in pyproject.toml. Create output/rich_output.py with format_rich(state, console) that renders: (1) summary panel with run_id/timestamp, (2) TrafficAnalysis table, (3) SecurityAssessment risk display, (4) PolicyProposal details with justification, (5) RuleDecision table with risk-colored rows using RISK_COLORS dict, (6) TokenUsage cost footer. Handle missing token_usage gracefully. Create output/json_output.py with format_json(state) → str that builds PipelineResult from state and calls model_dump_json(indent=2). Update output/__init__.py exports. Use Console(force_terminal=False) for auto-detection. Use overflow="fold" on text-heavy columns.
  - Verify: `pytest tests/test_output/ -v` — all tests pass; `pyright src/policyfoundry/output/` clean; `ruff check src/policyfoundry/output/`
  - Done when: Rich formatter test confirms table content contains expected risk levels with color markup; JSON formatter test confirms valid JSON with all pipeline stage keys; backward compat test confirms formatters handle missing token_usage; all lint/type checks pass

## Files Likely Touched

- `src/policyfoundry/exceptions.py`
- `src/policyfoundry/pipeline/llm.py`
- `src/policyfoundry/pipeline/state.py`
- `src/policyfoundry/output/__init__.py`
- `src/policyfoundry/output/models.py`
- `src/policyfoundry/output/rich_output.py`
- `src/policyfoundry/output/json_output.py`
- `src/policyfoundry/adapters/safety.py`
- `pyproject.toml`
- `tests/test_output/__init__.py`
- `tests/test_output/conftest.py`
- `tests/test_output/test_rich_output.py`
- `tests/test_output/test_json_output.py`
- `tests/test_output/test_models.py`
- `tests/test_safety/__init__.py`
- `tests/test_safety/test_read_only_adapter.py`
- `tests/test_safety/test_safety_error.py`
- `tests/test_pipeline/test_llm.py`
