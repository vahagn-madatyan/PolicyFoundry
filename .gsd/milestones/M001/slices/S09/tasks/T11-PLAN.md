---
estimated_steps: 4
estimated_files: 6
---

# T11: Reconstruct test files — pipeline, safety — and verify full test suite

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the pipeline test module (the largest test module — 4 test files totaling 182KB of pyc) and the safety test module (6 tests defining the ReadOnlyAdapter/SafetyError interface). Then runs the complete test suite across all reconstructed files to prove reconstruction fidelity.

The pipeline tests include test_stages (53KB — tests all 5 stages), test_llm (64KB — largest single test file, tests LLMClient with mocked Instructor), test_prompts (41KB — tests prompt formatting), and test_graph (24KB — tests LangGraph pipeline construction). The safety tests import `ReadOnlyAdapter` from `policyfoundry.adapters.safety` and `SafetyError` from `policyfoundry.exceptions` — neither exists yet, so safety tests are expected to fail (fixed in T12).

## Steps

1. **Reconstruct pipeline test fixtures + tests** — `test_pipeline/conftest.py` (11KB — pipeline test fixtures with mock LLM client, mock adapter, sample states), `test_stages.py` (53KB — tests all 5 stage functions with mocked dependencies), `test_llm.py` (64KB — tests LLMClient creation, structured output, health checking, token usage, retry logic), `test_prompts.py` (41KB — tests prompt template formatting), `test_graph.py` (24KB — tests graph construction and execution flow).

2. **Reconstruct safety tests** — `test_safety/test_readonly_adapter.py` (15KB — 6 tests: delegates get_rules/validate/capabilities, blocks apply_rule/apply_rules, verifies SafetyError structured details). These tests define the exact interface T12 must implement.

3. **Run pipeline tests** — `uv run pytest tests/test_pipeline/ -x -v`. Fix reconstruction issues. Then run full suite excluding safety and CLI: `uv run pytest tests/ --ignore=tests/test_safety --ignore=tests/test_cli -x -q`.

4. **Verify full suite** — Run all tests except safety (not yet implemented) and CLI (not yet implemented). Count should be 300+ tests all passing. Report the exact count.

## Must-Haves

- [ ] Pipeline conftest has mock LLM client and mock adapter fixtures
- [ ] Stage tests cover all 5 stages with mocked LLM (temperature per D025, validate non-LLM per D026)
- [ ] LLM tests cover Instructor integration (D018), Ollama prefix (D019), health check (D020)
- [ ] Graph tests verify 5-stage LangGraph pipeline construction (D021)
- [ ] Safety tests import from exact paths: `policyfoundry.adapters.safety.ReadOnlyAdapter`, `policyfoundry.exceptions.SafetyError`
- [ ] All pipeline tests pass; full suite (minus safety/CLI) passes with 300+ tests

## Verification

- `uv run pytest tests/test_pipeline/ -x -v 2>&1 | tail -5` → all pass
- `uv run pytest tests/ --ignore=tests/test_safety --ignore=tests/test_cli -x -q 2>&1 | tail -3` → 300+ tests passed
- `uv run pytest tests/test_safety/ --collect-only -q 2>&1` → shows 6 test items (collection succeeds but tests would fail on import)

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: Full test suite run with `-v` shows every test; `--tb=short` gives concise failure info
- Failure state exposed: Pytest summary line shows exact pass/fail/error counts

## Inputs

- `tests/test_pipeline/__pycache__/*.pyc` (conftest + 4 tests, 11–64KB)
- `tests/test_safety/__pycache__/*.pyc` (1 test, 15KB)
- All reconstructed src files from T02–T07
- All reconstructed test files from T08–T10
- `tools/inspect_pyc.py` from T01

## Expected Output

- `tests/test_pipeline/conftest.py`, `test_stages.py`, `test_llm.py`, `test_prompts.py`, `test_graph.py`
- `tests/test_safety/test_readonly_adapter.py`
- Full test suite result: 300+ tests passing (excluding safety and CLI)
- Safety tests: importable, 6 tests discoverable (will fail until T12)
