---
estimated_steps: 3
estimated_files: 6
---

# T07: Reconstruct src pipeline stages from bytecode

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the five pipeline stage functions that are the LangGraph nodes: analyze, assess, generate, validate, and decide. Each stage follows a common pattern: extract data from `PipelineState` → format prompt → call LLM (or adapter) → return `dict[str, Any]` state update (D022). The validate stage is unique — it uses `adapter.validate()` instead of an LLM call (D026).

All stages access dependencies via `PipelineContext` from the LangGraph `context_schema` (D021). Temperature settings vary by stage (D025). Empty proposals trigger a short-circuit skip (D024).

## Steps

1. **Reconstruct `stages/__init__.py`** — re-exports all five stage functions (e.g., `analyze_stage`, `assess_stage`, etc.).

2. **Reconstruct the five stage files** — Each follows this pattern:
   - `stages/analyze.py` — Reads flow log data + SG rules from state, formats with analyze prompt, calls LLM → returns `{"analysis": TrafficAnalysis}`. Temperature 0.1 (D025).
   - `stages/assess.py` — Reads analysis + current rules, formats with assess prompt, calls LLM → returns `{"assessment": SecurityAssessment}`. Temperature 0.1 (D025).
   - `stages/generate.py` — Reads assessment, formats with generate prompt, calls LLM → returns `{"proposals": list[PolicyProposal]}` via `PolicyProposalList` wrapper (D023). Temperature 0.3 (D025).
   - `stages/validate.py` — Non-LLM stage (D026). Reads proposals, calls `adapter.validate()` for each, filters invalid proposals → returns `{"proposals": list[PolicyProposal]}` (filtered).
   - `stages/decide.py` — Reads validated proposals, formats with decide prompt, calls LLM → returns `{"decisions": list[RuleDecision]}` via `RuleDecisionList` wrapper (D023). Skips if no proposals (D024). Temperature 0.1 (D025).

3. **Verify all stages import and have correct signatures** — Each stage function should accept `(state: PipelineState, context: PipelineContext)` and return `dict[str, Any]`.

## Must-Haves

- [ ] All five stage functions follow the `(state, context) -> dict[str, Any]` pattern (D022)
- [ ] Validate stage uses `adapter.validate()`, not LLM (D026)
- [ ] Generate stage uses temperature 0.3; analyze, assess, decide use 0.1 (D025)
- [ ] Decide stage skips LLM call when proposals list is empty (D024)
- [ ] `PolicyProposalList` and `RuleDecisionList` wrappers used for list outputs (D023)
- [ ] All 6 files import without error

## Verification

- `uv run python -c "from policyfoundry.pipeline.stages import analyze_stage, assess_stage, generate_stage, validate_stage, decide_stage; print('OK')"`
- `uv run python -c "import inspect; from policyfoundry.pipeline.stages.analyze import analyze_stage; sig = inspect.signature(analyze_stage); print(list(sig.parameters.keys())); print('OK')"`

## Observability Impact

- Signals added/changed: None (reconstruction only)
- How a future agent inspects this: Import stage functions and inspect signatures; check for `PipelineContext` parameter usage
- Failure state exposed: None

## Inputs

- `src/policyfoundry/pipeline/stages/__pycache__/*.cpython-313.pyc` (6 files, 677–2864 bytes)
- `tools/inspect_pyc.py` from T01
- `src/policyfoundry/pipeline/state.py`, `schema.py`, `graph.py` from T06 (PipelineState, PipelineContext, Pydantic models)
- `src/policyfoundry/pipeline/prompts/` from T06 (prompt templates)
- Decisions D021, D022, D023, D024, D025, D026

## Expected Output

- `src/policyfoundry/pipeline/stages/__init__.py` — re-exports
- `src/policyfoundry/pipeline/stages/analyze.py` — analyze stage
- `src/policyfoundry/pipeline/stages/assess.py` — assess stage
- `src/policyfoundry/pipeline/stages/generate.py` — generate stage
- `src/policyfoundry/pipeline/stages/validate.py` — validate stage (non-LLM)
- `src/policyfoundry/pipeline/stages/decide.py` — decide stage

After T07, all 48 src `.py` files exist on disk. The full source tree is reconstructed.
