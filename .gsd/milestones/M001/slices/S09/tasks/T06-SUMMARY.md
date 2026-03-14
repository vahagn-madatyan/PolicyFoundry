---
id: T06
parent: S09
milestone: M001
provides:
  - policyfoundry.pipeline core: state, schema, llm, graph, runner modules
  - policyfoundry.pipeline.prompts subpackage: 4 system prompts + 4 user message formatters
  - policyfoundry.pipeline.stages: 5 stage functions + 2 wrapper models (D023)
  - PipelineContext dataclass (D021) for LangGraph dependency injection
  - LLMClient with Instructor+LiteLLM structured output (D018), Ollama health check (D020)
  - async run_pipeline() entry point with PipelineError wrapping
key_files:
  - src/policyfoundry/pipeline/__init__.py
  - src/policyfoundry/pipeline/state.py
  - src/policyfoundry/pipeline/schema.py
  - src/policyfoundry/pipeline/llm.py
  - src/policyfoundry/pipeline/graph.py
  - src/policyfoundry/pipeline/runner.py
  - src/policyfoundry/pipeline/prompts/__init__.py
  - src/policyfoundry/pipeline/prompts/analyze.py
  - src/policyfoundry/pipeline/prompts/assess.py
  - src/policyfoundry/pipeline/prompts/generate.py
  - src/policyfoundry/pipeline/prompts/decide.py
  - src/policyfoundry/pipeline/stages/__init__.py
  - src/policyfoundry/pipeline/stages/analyze.py
  - src/policyfoundry/pipeline/stages/assess.py
  - src/policyfoundry/pipeline/stages/generate.py
  - src/policyfoundry/pipeline/stages/decide.py
  - src/policyfoundry/pipeline/stages/validate.py
key_decisions:
  - D023 wrapper models (PolicyProposalList, RuleDecisionList) confirmed in stages/ not schema.py — bytecode shows them in generate.py and decide.py
patterns_established:
  - LLM stage functions: async def stage(state, runtime) -> dict[str, Any] using runtime.context for PipelineContext
  - Prompt pattern: module-level SYSTEM_PROMPT constant + format_*_user_message() function that serializes to JSON
  - Retry layers: inner Instructor validation retries (3) + outer tenacity transient retries (3) with exponential backoff
  - Temperature settings: 0.1 for analyze/assess/decide, 0.3 for generate (D025)
  - Empty proposals short-circuit in decide_stage (D024)
observability_surfaces:
  - LLMClient.get_usage() returns deep-copied TokenUsage with per-call breakdown
  - PipelineError with error_code and details dict for LLM failures (LLM_PARSE_FAILED, LLM_CALL_FAILED, LLM_MODEL_NOT_FOUND, LLM_UNREACHABLE, PIPELINE_STAGE_FAILED)
  - logger.warning when LLM response missing usage metadata
duration: 35m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T06: Reconstruct src pipeline core and prompts from bytecode

**Reconstructed 17 source files from CPython 3.13 bytecode: pipeline core (state, schema, LLM client, graph, runner), 4 prompt templates, and 5 pipeline stages with wrapper models.**

## What Happened

Used dis module disassembly to reconstruct all pipeline-related source files from .pyc bytecode. The 11 planned files plus 6 required stage files were extracted:

1. **Pipeline state + schema** (existing from T05 stubs, verified correct): `PipelineState` TypedDict with `total=False` (D003), 4 Pydantic schema models.

2. **Pipeline llm.py** (12.6KB pyc → 10.6KB py, most complex file): Reconstructed `LLMClient` class with dual retry layers (inner Instructor validation + outer tenacity transient), `create_llm_client` factory with Ollama health check, `_compose_model_name` for provider-specific LiteLLM identifiers, `_extract_cost` for hidden params, and `_check_ollama_health` async validation. Uses `instructor.from_litellm(acompletion, mode=instructor.Mode.JSON)` (D018) with `ollama_chat/` prefix (D019).

3. **Pipeline graph.py + runner.py**: `PipelineContext` dataclass (D021) with `llm_client`, `adapter`, `data_dir`. `build_pipeline()` wires 5-node linear StateGraph (START→analyze→assess→generate→validate→decide→END) via `context_schema=PipelineContext`. `run_pipeline()` is async, wraps non-PipelineError exceptions with stage context.

4. **Prompt templates** (4 files): All 4 system prompts extracted from bytecode `co_consts` and verified character-for-character match. Each module has a SYSTEM_PROMPT constant and a `format_*_user_message()` function that serializes inputs to JSON.

5. **Pipeline stages** (6 files, deviation from plan): Required because graph.py's top-level imports need importable stage modules. Python's standard importer cannot find `.pyc` files in `__pycache__/` without corresponding `.py` files. All 5 stage functions + wrapper models (`PolicyProposalList`, `RuleDecisionList` per D023) + `_MAX_PROPOSALS=20` constant were faithfully reconstructed.

## Verification

All 4 task-plan verification commands pass:
- `from policyfoundry.pipeline.state import PipelineState; from policyfoundry.pipeline.schema import TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision` → OK
- `from policyfoundry.pipeline.llm import create_llm_client, LLMClient; from policyfoundry.pipeline.graph import build_pipeline, PipelineContext` → OK
- `from policyfoundry.pipeline.runner import run_pipeline; assert asyncio.iscoroutinefunction(run_pipeline)` → OK
- `from policyfoundry.pipeline.prompts import analyze, assess, generate, decide` → OK

Must-haves verified:
- [x] PipelineState is TypedDict with total=False (D003)
- [x] LLMClient uses instructor.from_litellm(acompletion, mode=JSON) (D018)
- [x] Ollama health check only runs for Ollama provider (D020)
- [x] PipelineContext is dataclass with llm_client, adapter, data_dir (D021)
- [x] PolicyProposalList and RuleDecisionList wrapper models exist (D023)
- [x] run_pipeline is async def
- [x] All 11 core files + 6 stage files import without error

Prompt content verification: all 4 system prompts match bytecode character-for-character (1070, 1212, 1462, 1533 chars respectively).

Slice-level verification (intermediate — T06 of 13):
- Pre-existing tests: 0 collected (test .py files not yet reconstructed — later task)
- Safety tests: 0 collected (not yet created — later task)
- CLI tests: fail as expected (CLI module not yet created)
- `policyfoundry --help`: fails (CLI __main__.py not yet created)

## Diagnostics

- Import any pipeline module: `uv run python -c "from policyfoundry.pipeline.llm import LLMClient; print(LLMClient.__doc__[:50])"`
- Inspect LLMClient: `uv run python -c "from policyfoundry.pipeline.llm import LLMClient; print([m for m in dir(LLMClient) if not m.startswith('__')])"`
- Check PipelineContext fields: `uv run python -c "import dataclasses; from policyfoundry.pipeline.graph import PipelineContext; print([f.name for f in dataclasses.fields(PipelineContext)])"`
- Verify prompt lengths match: `uv run python -c "from policyfoundry.pipeline.prompts import *; print(len(ANALYZE_SYSTEM_PROMPT), len(ASSESS_SYSTEM_PROMPT), len(GENERATE_SYSTEM_PROMPT), len(DECIDE_SYSTEM_PROMPT))"`

## Deviations

- **Added 6 stage files** not in T06 expected output: `stages/__init__.py`, `stages/analyze.py`, `stages/assess.py`, `stages/generate.py`, `stages/decide.py`, `stages/validate.py`. Required because `graph.py` has top-level imports of all 5 stage functions, and Python's standard import system cannot find .pyc files in `__pycache__/` without corresponding .py source files. Full reconstruction from bytecode was done (not stubs) to avoid rework in later tasks.

- **Wrapper models (D023) are in stages/ not schema.py**: The task plan suggested `PolicyProposalList` and `RuleDecisionList` belong in `schema.py`, but bytecode shows they're defined in `stages/generate.py` and `stages/decide.py` respectively. This makes sense — they're response_model wrappers used only by their respective stage functions.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/__init__.py` — Package docstring (unchanged from T05 stub)
- `src/policyfoundry/pipeline/state.py` — PipelineState TypedDict (unchanged from T05 stub)
- `src/policyfoundry/pipeline/schema.py` — 4 Pydantic models (unchanged from T05 stub)
- `src/policyfoundry/pipeline/llm.py` — LLMClient class, create_llm_client factory, Ollama health check, retry layers
- `src/policyfoundry/pipeline/graph.py` — PipelineContext dataclass, build_pipeline() with 5-node StateGraph
- `src/policyfoundry/pipeline/runner.py` — async run_pipeline() entry point with error wrapping
- `src/policyfoundry/pipeline/prompts/__init__.py` — Re-exports all 4 system prompts
- `src/policyfoundry/pipeline/prompts/analyze.py` — ANALYZE_SYSTEM_PROMPT + format_analyze_user_message()
- `src/policyfoundry/pipeline/prompts/assess.py` — ASSESS_SYSTEM_PROMPT + format_assess_user_message()
- `src/policyfoundry/pipeline/prompts/generate.py` — GENERATE_SYSTEM_PROMPT + format_generate_user_message()
- `src/policyfoundry/pipeline/prompts/decide.py` — DECIDE_SYSTEM_PROMPT + format_decide_user_message()
- `src/policyfoundry/pipeline/stages/__init__.py` — Re-exports all 5 stage functions
- `src/policyfoundry/pipeline/stages/analyze.py` — Stage 1: DuckDB queries → LLM TrafficAnalysis
- `src/policyfoundry/pipeline/stages/assess.py` — Stage 2: analysis + rules → LLM SecurityAssessment
- `src/policyfoundry/pipeline/stages/generate.py` — Stage 3: assessment → LLM PolicyProposalList (D023)
- `src/policyfoundry/pipeline/stages/decide.py` — Stage 4: proposals → LLM RuleDecisionList (D023, D024)
- `src/policyfoundry/pipeline/stages/validate.py` — Non-LLM filter via adapter.validate() (D026)
