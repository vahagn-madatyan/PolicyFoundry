# S08 ("Output And Safety") — Research

**Date:** 2026-03-11

## Summary

This slice delivers the output layer and safety enforcement for PolicyFoundry's pipeline results. It covers four Active requirements: **OUT-01** (Rich terminal display with color-coded risk tables), **OUT-02** (JSON export), **SAFE-01** (suggest-only mode enforcement), and **SAFE-02** (LLM token usage and cost tracking). The work is straightforward — all data contracts already exist in `pipeline/schema.py` (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision) and the `output/` package is scaffolded but empty. Rich 14.3.3 is already installed as a transitive dependency of `instructor`.

The main technical challenge is **token usage tracking** — the current `LLMClient.complete()` discards the raw Instructor/LiteLLM response and returns only the validated Pydantic model, losing all usage metadata. Instructor's `create_with_completion()` method returns `(model, raw_response)` and the raw LiteLLM `ModelResponse` carries a `.usage` object with `prompt_tokens`, `completion_tokens`, `total_tokens`, and `cost`. The `_raw_response` attribute is also accessible on the returned model itself. The LLMClient must be modified to capture and accumulate this data across pipeline stages, then surface it in PipelineState for the output layer.

The safety layer is the simplest component: the adapter ABC is already read-only (no `apply_rule()` method exists), so suggest-only mode is enforced by contract. A `SafetyError` exception and a `ReadOnlyAdapter` wrapper provide defense-in-depth for the future auto-apply path.

## Recommendation

**Approach:** Three independent modules in `src/policyfoundry/output/` plus targeted modifications to existing code:

1. **Token tracking** — Modify `LLMClient.complete()` to use `create_with_completion()` instead of `create()`. Add a `TokenUsage` dataclass that accumulates per-call usage. Add a `token_usage` field to `PipelineState`. Each stage already calls `ctx.llm_client.complete()` — no stage modifications needed if LLMClient tracks usage internally and exposes a `get_usage()` method.

2. **Rich output** — `output/rich_output.py` consuming `PipelineState` to render: a summary panel, risk-colored decisions table, proposals detail, and cost summary. Use `RiskLevel` enum values for color mapping (LOW→green, MEDIUM→yellow, HIGH→red, CRITICAL→bold red).

3. **JSON output** — `output/json_output.py` serializing `PipelineState` with Pydantic model reconstruction for clean JSON. Trivial since all stage outputs are already `dict` representations of Pydantic models.

4. **Safety enforcement** — Add `SafetyError` to exception hierarchy. Create a `ReadOnlyAdapter` wrapper that delegates reads and raises `SafetyError` on any future write method. This is purely defensive.

**Why:** This approach requires minimal changes to existing code (only `LLMClient._call_with_retry` and the return type of `complete()`), keeps output formatting isolated in its own package, and follows the established patterns from S07.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Terminal tables with colors | `rich.table.Table` + `rich.console.Console` | Already installed (14.3.3), battle-tested, handles terminal width, color support detection |
| Summary panels | `rich.panel.Panel` + `rich.text.Text` | Rich's panel API handles borders, titles, padding automatically |
| JSON serialization | `pydantic.BaseModel.model_dump_json()` | All output models are already Pydantic — free serialization |
| Token usage from LLM calls | `instructor.create_with_completion()` | Returns `(model, raw_response)` — raw response has `.usage` with token counts and LiteLLM's `._hidden_params["response_cost"]` |
| Cost estimation | `litellm.completion_cost()` or `response._hidden_params["response_cost"]` | LiteLLM tracks cost per model natively; no manual price table needed |

## Existing Code and Patterns

- `src/policyfoundry/pipeline/schema.py` — The 4 output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision) are the data contract for all formatters. Each has `model_dump()` for dict and `model_dump_json()` for JSON. RiskLevel is a StrEnum with LOW/MEDIUM/HIGH/CRITICAL.
- `src/policyfoundry/pipeline/state.py` — PipelineState TypedDict stores stage outputs as serialized dicts (`analysis: dict`, `assessment: dict`, `proposals: list[dict]`, `decisions: list[dict]`). Formatters must reconstruct Pydantic models via `TrafficAnalysis.model_validate(state["analysis"])` for typed access.
- `src/policyfoundry/pipeline/llm.py` — `LLMClient.complete()` currently calls `self._client.chat.completions.create()` (Instructor's `create`). Must switch to `create_with_completion()` to get the raw response with token usage. The `_call_with_retry` method is the single call site.
- `src/policyfoundry/pipeline/runner.py` — `run_pipeline()` returns `PipelineState` after all stages. The output layer consumes this return value. No modifications needed here.
- `src/policyfoundry/adapters/base.py` — `FirewallAdapter` ABC has only `get_rules()`, `validate()`, and `capabilities()` — already read-only by design. No write methods exist.
- `src/policyfoundry/config/models.py` — `OutputConfig` has `format: str = "rich"` field. This controls which formatter is invoked (S09 CLI will wire this).
- `src/policyfoundry/exceptions.py` — Exception hierarchy has `OutputError` but no `SafetyError`. Follow existing pattern (inherit from `PolicyFoundryError`).
- `src/policyfoundry/adapters/schema.py` — `RiskLevel` StrEnum (LOW/MEDIUM/HIGH/CRITICAL) imported by pipeline schema. Use for color mapping in Rich output.
- `tests/test_pipeline/conftest.py` — Rich set of mock fixtures (mock_adapter, mock_llm_client, sample_*) to reuse for output tests.

## Constraints

- **Rich is a transitive dependency only** — `instructor` pulls in `rich>=13.7.0`. It is NOT a direct dependency in `pyproject.toml`. Add `rich>=14.0` as a direct dependency for the output module to avoid implicit coupling.
- **PipelineState is a TypedDict with `total=False`** — New fields (like `token_usage`) can be added without breaking existing code, but they must be accessed via `.get()` with defaults since they may be absent in older states.
- **LiteLLM `ModelResponse.usage` is dynamically set** — The `usage` attribute is populated after API calls via `extra='allow'` on the Pydantic model. Access with `getattr(response, 'usage', None)` for safety.
- **LiteLLM `_hidden_params["response_cost"]`** — Cost is available via private attribute. For Ollama local models, this may be `0.0` or `None` since there's no real API cost. Handle gracefully.
- **Instructor `create_with_completion` is async** — Returns `tuple[T, Any]`. The second element is the raw LiteLLM `ModelResponse`. This is the async variant since the client is created with `instructor.from_litellm(acompletion, ...)`.
- **Pyright strict mode** — All new code in `src/` must satisfy pyright strict. Follow established patterns: `type: ignore` comments for dynamic LiteLLM/Instructor types, explicit return type annotations.
- **`dict[str, Any]` return pattern from stages** — Stage functions return `dict[str, Any]` to satisfy pyright with LangGraph dynamic types. Token usage accumulation must work within this constraint.

## Common Pitfalls

- **Discarding raw response metadata** — The biggest risk. Instructor's `create()` returns only the Pydantic model. You must use `create_with_completion()` to get the raw response with usage data. If this is overlooked, SAFE-02 cannot be delivered.
- **Assuming `response.usage` always exists** — LiteLLM's `ModelResponse` sets `usage` dynamically. With some providers or error paths, it may be absent. Always guard with `getattr(response, 'usage', None)`.
- **Hardcoding color codes instead of using RiskLevel mapping** — The `RiskLevel` enum is a StrEnum. Create a single `RISK_COLORS: dict[RiskLevel, str]` mapping and reference it everywhere. Avoids scattered color strings.
- **Breaking the `_call_with_retry` tenacity decorator** — The retry decorator on `_call_with_retry` must still work after switching to `create_with_completion`. The return type changes from `T` to `tuple[T, Any]` — update the retry wrapper and the outer `complete()` method signature together.
- **Token usage accumulation across retries** — If an LLM call retries 3 times before succeeding, the usage from failed attempts is lost. Instructor's `create_with_completion` only returns the final successful response. For accurate tracking, accept that usage reflects the final successful call only, and note in docs that retried calls are not counted.
- **Rich output in non-TTY environments** — `Console(force_terminal=False)` auto-detects. Don't force color in CI/pipe contexts. Use `Console()` with defaults and let Rich handle detection.
- **Modifying PipelineState TypedDict for token_usage** — Adding fields to TypedDict is safe with `total=False`, but LangGraph serializes the full state at checkpoints. Keep token_usage as a simple dict (not a complex nested model) to avoid serialization issues.

## Open Risks

- **Instructor `create_with_completion` behavior under retries** — When Instructor retries validation errors (inner retry loop), the raw response returned is from the final successful attempt. Token usage from intermediate failed attempts is not captured. This means cost tracking may undercount by up to `_MAX_VALIDATION_RETRIES` failed calls. Acceptable for MVP — document the limitation.
- **LiteLLM cost estimation for Ollama** — `response._hidden_params["response_cost"]` may be `0.0` or absent for Ollama local models since there's no real API cost. The output should show "N/A (local model)" or `$0.00` for local providers. Need to test this empirically.
- **Rich table width with long justification text** — PolicyProposal.justification and RuleDecision.reason can be multi-sentence strings. If the terminal is narrow (<80 cols), Rich tables may wrap poorly. Use `overflow="fold"` or `max_width` on text-heavy columns.
- **PipelineState checkpoint compatibility** — Adding `token_usage` field to PipelineState doesn't break existing checkpoints (TypedDict total=False), but older pipeline runs loaded from checkpoints won't have this field. Output formatters must handle its absence.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Rich terminal | `autumnsgrove/groveengine@rich-terminal-output` (57 installs) | available — low relevance (generic Rich usage, not security domain) |
| Rich terminal | `ingpoc/skills@terminal-ui-design` (8 installs) | available — low installs, skip |
| LangChain cost | `jeremylongshore/claude-code-plugins-plus-skills@langchain-cost-tuning` (16 installs) | available — tangentially relevant but targets LangChain directly, not Instructor+LiteLLM |

No skills are directly relevant enough to recommend installing. Rich and Instructor/LiteLLM are well-documented via Context7.

## Sources

- Instructor `create_with_completion` returns `(model, raw_response)` for token tracking (source: [Instructor usage docs](https://github.com/jxnl/instructor/blob/main/docs/concepts/usage.md))
- LiteLLM cost via `response._hidden_params["response_cost"]` (source: [Instructor LiteLLM integration](https://github.com/jxnl/instructor/blob/main/docs/integrations/litellm.md))
- `_raw_response` attribute set on Instructor model instances for metadata access (source: [Instructor debugging docs](https://github.com/jxnl/instructor/blob/main/docs/debugging.md))
- LiteLLM `ModelResponse` has `extra='allow'` so `usage` is set dynamically after calls (verified empirically via Python introspection)
- LiteLLM `Usage` model has fields: `completion_tokens`, `prompt_tokens`, `total_tokens`, `cost` (verified via `litellm.Usage.model_fields`)
- Rich Table, Panel, Console APIs for formatted terminal output (source: [Rich docs](https://rich.readthedocs.io/en/stable/))
- `litellm.completion_cost(completion_response)` calculates cost from a ModelResponse (verified via function signature introspection)
