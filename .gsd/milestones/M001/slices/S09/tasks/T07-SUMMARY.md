---
id: T07
parent: S09
milestone: M001
provides:
  - All 5 pipeline stage functions verified against bytecode: analyze, assess, generate, validate, decide
  - Full 48-file source tree reconstruction complete (all src .py files on disk)
key_files:
  - src/policyfoundry/pipeline/stages/__init__.py
  - src/policyfoundry/pipeline/stages/analyze.py
  - src/policyfoundry/pipeline/stages/assess.py
  - src/policyfoundry/pipeline/stages/generate.py
  - src/policyfoundry/pipeline/stages/validate.py
  - src/policyfoundry/pipeline/stages/decide.py
key_decisions:
  - D022 confirmed: all 5 stages return dict[str, Any] with current_stage key
  - D023 confirmed: PolicyProposalList wrapper in generate.py, RuleDecisionList wrapper in decide.py
  - D024 confirmed: decide_stage short-circuits with empty decisions list when proposals is empty
  - D025 confirmed: analyze=0.1, assess=0.1, generate=0.3, decide=0.1 temperatures
  - D026 confirmed: validate_proposals uses adapter.validate() with no LLM call
patterns_established:
  - Stage function signature: async def stage_name(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]
  - LLM stages: extract from state → format prompt → build messages list → ctx.llm_client.complete() → model_dump() into return dict
  - Non-LLM stage (validate): iterate proposals → PolicyProposal.model_validate() → adapter.validate(rule, current_rule_count=N) → filter by result.valid
  - Wrapper models for list outputs: Pydantic BaseModel with single list field, used as LLM structured output type
observability_surfaces:
  - none (reconstruction only — stages are pure pipeline functions)
duration: 15m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T07: Reconstruct src pipeline stages from bytecode

**Verified all 5 pipeline stage files against CPython 3.13 bytecode — all 48 src .py files now confirmed on disk, completing the full source tree reconstruction.**

## What Happened

The 6 stage files (5 stages + `__init__.py`) already existed from T06's reconstruction work. This task performed byte-level verification of each file against the original `.cpython-313.pyc` bytecode using `dis.dis()` and `marshal` introspection to confirm:

1. **`__init__.py`** — Re-exports all 5 functions with `__all__` list. Bytecode CO_NAMES confirms `__all__` assignment.
2. **`analyze.py`** — Queries 4 DuckDB analytics (traffic_summary, top_talkers(20), denied_flows, traffic_by_protocol), formats with analyze prompt, calls LLM at temperature 0.1, returns `{analysis: ..., current_stage: "analyze"}`.
3. **`assess.py`** — Reads analysis from state, fetches current rules via adapter, formats with assess prompt, calls LLM at temperature 0.1, returns `{assessment: ..., current_stage: "assess"}`.
4. **`generate.py`** — Reads assessment + analysis, gets adapter capabilities, formats with generate prompt, calls LLM with PolicyProposalList wrapper at temperature 0.3, truncates to `_MAX_PROPOSALS=20`, returns `{proposals: [...], current_stage: "generate"}`.
5. **`validate.py`** — Non-LLM stage. Iterates proposals, reconstructs each via `PolicyProposal.model_validate()`, calls `adapter.validate(rule, current_rule_count=len(rules))`, filters invalid, returns `{proposals: valid_list, current_stage: "validate"}`.
6. **`decide.py`** — Short-circuits on empty proposals (D024). Otherwise formats with decide prompt, calls LLM with RuleDecisionList wrapper at temperature 0.1, returns `{decisions: [...], current_stage: "decide"}`.

Every variable name, constant value, import path, and control flow path in the source matches the bytecode disassembly.

## Verification

- `uv run python -c "from policyfoundry.pipeline.stages import analyze_stage, assess_stage, generate_stage, validate_proposals, decide_stage; print('OK')"` → OK
- `uv run python -c "import inspect; ..."` → all 5 functions: params=['state', 'runtime'], async=True, return type dict[str, Any]
- D022: All 5 stages accept (state, runtime) and return dict[str, Any] ✅
- D023: PolicyProposalList in generate.py, RuleDecisionList in decide.py ✅
- D024: `if not proposals:` short-circuit in decide_stage ✅
- D025: analyze=0.1, assess=0.1, generate=0.3, decide=0.1 ✅
- D026: validate has no llm_client reference, uses adapter.validate() ✅
- All 6 files import without error ✅
- 48 total src .py files confirmed on disk via `find src/policyfoundry -name '*.py'`

### Slice Verification (intermediate — T07 of T13)

| Check | Status | Notes |
|---|---|---|
| Pre-existing tests pass | N/A | Test .py files not yet reconstructed (T08–T11) — dirs exist but are empty |
| Safety tests pass | N/A | Safety module not yet built (T12) |
| CLI tests pass | Expected fail | T01 stubs fail with "Not yet implemented — waiting for CLI module reconstruction (T10)" |
| `policyfoundry --help` | N/A | CLI not yet built (T12) |

## Diagnostics

- Import any stage: `uv run python -c "from policyfoundry.pipeline.stages.analyze import analyze_stage; print(analyze_stage)"`
- Inspect signatures: `uv run python -c "import inspect; from policyfoundry.pipeline.stages import analyze_stage; print(inspect.signature(analyze_stage))"`
- Bytecode verification: `uv run python tools/inspect_pyc.py src/policyfoundry/pipeline/stages/__pycache__/analyze.cpython-313.pyc`

## Deviations

None. The stage files already existed from T06, so T07 was a verification-only task confirming bytecode fidelity.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/stages/__init__.py` — verified: re-exports 5 stage functions with __all__
- `src/policyfoundry/pipeline/stages/analyze.py` — verified: Stage 1, DuckDB queries → LLM, temp 0.1
- `src/policyfoundry/pipeline/stages/assess.py` — verified: Stage 2, analysis + rules → LLM, temp 0.1
- `src/policyfoundry/pipeline/stages/generate.py` — verified: Stage 3, PolicyProposalList wrapper, temp 0.3
- `src/policyfoundry/pipeline/stages/validate.py` — verified: Non-LLM stage, adapter.validate()
- `src/policyfoundry/pipeline/stages/decide.py` — verified: Stage 4, RuleDecisionList wrapper, D024 skip, temp 0.1
