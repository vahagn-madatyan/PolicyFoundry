---
estimated_steps: 5
estimated_files: 11
---

# T06: Reconstruct src pipeline core and prompts from bytecode

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the pipeline module's core files (state, schema, LLM client, graph definition, runner) and the prompt template subpackage. The pipeline is the heart of PolicyFoundry — `run_pipeline()` orchestrates the 5-stage LangGraph pipeline that the CLI's `analyze` command invokes.

The LLM client (`llm.py`, 12.6KB pyc — the largest src file) integrates Instructor with LiteLLM for structured output. The graph definition (`graph.py`) builds the LangGraph `CompiledGraph`. The runner (`runner.py`) is the async entry point. Prompt files are string template constants — relatively simple to extract from bytecode.

**Note:** 11 files is at the upper end but 5 are prompt templates (extractable string constants) and `__init__.py` files are small re-exports.

## Steps

1. **Reconstruct pipeline state + schema** (3 files):
   - `pipeline/__init__.py` — re-exports
   - `pipeline/state.py` — `PipelineState` TypedDict with `total=False` (D003). Fields: `run_id`, `started_at`, `current_stage`, `flow_log_path`, `sg_ids`, `analysis`, `assessment`, `proposals`, `decisions`, `token_usage`
   - `pipeline/schema.py` — `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `PolicyProposalList`, `RuleDecision`, `RuleDecisionList` Pydantic models. Lists use wrapper models for Instructor (D023).

2. **Reconstruct `pipeline/llm.py`** — `create_llm_client(config: LLMConfig) -> LLMClient` factory with Ollama health check (D020). `LLMClient` class using `instructor.from_litellm(acompletion, mode=JSON)` (D018) with `ollama_chat/` prefix (D019). `get_usage() -> TokenUsage` method. This is the most complex file — extract class structure, method signatures, and string constants from bytecode carefully.

3. **Reconstruct `pipeline/graph.py` + `pipeline/runner.py`** — `PipelineContext` dataclass (D021) with `llm_client`, `adapter`, `data_dir` fields. `build_pipeline()` returns `CompiledGraph` wiring 5 stages. `async run_pipeline(llm_client, adapter, data_dir, sg_ids) -> PipelineState`.

4. **Reconstruct prompt templates** (5 files):
   - `pipeline/prompts/__init__.py` — re-exports
   - `pipeline/prompts/analyze.py`, `assess.py`, `generate.py`, `decide.py` — Each contains prompt template strings as module-level constants. Extract directly from code object `co_consts`.

5. **Verify all imports** and check that `run_pipeline` is async, `build_pipeline` returns a graph, and `LLMClient` has `get_usage`.

## Must-Haves

- [ ] `PipelineState` is TypedDict with `total=False` (D003)
- [ ] `LLMClient` uses `instructor.from_litellm(acompletion, mode=JSON)` (D018)
- [ ] Ollama health check only runs for Ollama provider (D020)
- [ ] `PipelineContext` is a dataclass with `llm_client`, `adapter`, `data_dir` (D021)
- [ ] `PolicyProposalList` and `RuleDecisionList` wrapper models exist (D023)
- [ ] `run_pipeline` is `async def`
- [ ] All 11 files import without error

## Verification

- `uv run python -c "from policyfoundry.pipeline.state import PipelineState; from policyfoundry.pipeline.schema import TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision; print('OK')"`
- `uv run python -c "from policyfoundry.pipeline.llm import create_llm_client, LLMClient; from policyfoundry.pipeline.graph import build_pipeline, PipelineContext; print('OK')"`
- `uv run python -c "from policyfoundry.pipeline.runner import run_pipeline; import asyncio; assert asyncio.iscoroutinefunction(run_pipeline); print('OK')"`
- `uv run python -c "from policyfoundry.pipeline.prompts import analyze, assess, generate, decide; print('OK')"`

## Observability Impact

- Signals added/changed: None (reconstruction only)
- How a future agent inspects this: Import `LLMClient` and inspect `get_usage()` return type; check `PipelineContext` fields
- Failure state exposed: None

## Inputs

- `src/policyfoundry/pipeline/__pycache__/*.cpython-313.pyc` (6 files, 561–12645 bytes)
- `src/policyfoundry/pipeline/prompts/__pycache__/*.cpython-313.pyc` (5 files, 822–3951 bytes)
- `tools/inspect_pyc.py` from T01
- Decisions D003, D018, D019, D020, D021, D023
- `src/policyfoundry/config/models.py` from T02 (LLMConfig)
- `src/policyfoundry/adapters/base.py` from T04 (FirewallAdapter)
- `src/policyfoundry/output/models.py` from T05 (TokenUsage)

## Expected Output

- `src/policyfoundry/pipeline/__init__.py`, `state.py`, `schema.py`, `llm.py`, `graph.py`, `runner.py`
- `src/policyfoundry/pipeline/prompts/__init__.py`, `analyze.py`, `assess.py`, `generate.py`, `decide.py`
