# Phase 6: LLM Integration - Research

**Researched:** 2026-03-10
**Domain:** LLM client integration (LiteLLM + Instructor + Ollama)
**Confidence:** HIGH

## Summary

Phase 6 builds the LLM client layer that all pipeline stages will call. The core stack is **Instructor wrapping LiteLLM** for structured Pydantic output with automatic validation retries, plus a transient-retry wrapper for network/timeout failures. The client factory creates an async-capable `LLMClient` that composes provider/model into LiteLLM format, health-checks the provider, and exposes a generic `complete()` method accepting any Pydantic `response_model`.

The research confirms the CONTEXT.md decisions are well-supported by current library versions. `instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)` is the correct async integration pattern. JSON mode is the right choice for maximum provider compatibility -- Ollama, OpenAI, and Bedrock all support it. The `from_provider` API does NOT support LiteLLM as a provider (confirmed via GitHub issue #1710), so `from_litellm` is the correct path.

**Primary recommendation:** Use `instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)` for async structured output, with Instructor's built-in `max_retries` for validation retries and tenacity decorator for transient retries around the outer call.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use Instructor library wrapping LiteLLM for automatic Pydantic validation and retry
- Async mode: `instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)`
- JSON mode chosen for maximum provider compatibility (Ollama, OpenAI, Bedrock all support it)
- Adds `instructor` and `litellm` as new dependencies
- Two retry layers: Inner (Instructor-managed, 3 validation retries) + Outer (our wrapper, 3 transient retries with exponential backoff 1s, 2s, 4s)
- Worst case: 3 * 4 = 12 LLM calls per request
- All retry config hardcoded as module constants (not in LLMConfig)
- On exhaustion: raise PipelineError with error_code="LLM_PARSE_FAILED", including model name, response_model name, attempt count, and last validation error
- Keep separate `provider` and `model` fields in LLMConfig; client auto-composes to LiteLLM format
- Auto-default base_url to `http://localhost:11434` when provider is `ollama` and base_url is None
- On client creation, ping LLM provider; for Ollama hit `/api/tags` and verify model is available
- Fail fast with PipelineError (error_code="LLM_UNREACHABLE" or "LLM_MODEL_NOT_FOUND")
- LLMClient class with generic `complete(messages, response_model, temperature?)` method
- Factory function: `create_llm_client(config: LLMConfig) -> LLMClient`
- Module location: `src/policyfoundry/pipeline/llm.py`
- Exported from `pipeline/__init__.py`

### Claude's Discretion
- Exact Instructor client initialization details
- Transient retry implementation (tenacity vs manual loop)
- Health check HTTP client choice (httpx, aiohttp, or raw urllib)
- How to handle non-Ollama provider health checks (OpenAI, Bedrock)
- PipelineError subclass naming for LLM-specific errors
- Test fixture design for mocking LLM responses

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-06 | LLM calls route through LiteLLM with Ollama as default local provider | Instructor wraps LiteLLM's `acompletion` for async calls; model naming uses `ollama/{model}` format with auto-composed provider prefix; health check verifies Ollama reachability and model availability |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| instructor | >=1.14 | Structured LLM output with Pydantic validation + automatic retry | 3M+ monthly downloads, de facto standard for structured LLM extraction; manages validation-retry loop natively |
| litellm | >=1.80 | Unified LLM provider routing (Ollama, OpenAI, Bedrock, etc.) | 100+ provider support; OpenAI-compatible interface; consistent exception hierarchy |

### Supporting (already in dependency tree)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | >=8.2.3 | Transient retry with exponential backoff | Outer retry layer for ConnectionError/Timeout; comes as dependency of both instructor and litellm |
| httpx | (via litellm) | Async HTTP client | Health check endpoint calls; already a litellm dependency |
| pydantic | >=2.12 | Response model definition | Already in project; Instructor leverages Pydantic v2 natively |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| instructor `from_litellm` | instructor `from_provider("ollama/...")` | `from_provider` does NOT support LiteLLM as a provider (GitHub issue #1710); `from_litellm` is the only correct path for LiteLLM integration |
| JSON mode | TOOLS mode | TOOLS mode only works with specific models (llama3.1, llama3.2, mistral-nemo, qwen2.5); JSON mode works universally -- correct choice for provider-agnostic design |
| tenacity (transient retry) | Manual retry loop | tenacity is already a dependency; provides async support, configurable backoff, exception filtering, and logging hooks out of the box |
| httpx (health check) | aiohttp | Both are litellm dependencies; httpx has cleaner async context manager API (`async with httpx.AsyncClient()`) and is more commonly used for simple HTTP calls |

**Installation:**
```bash
uv add "instructor[litellm]"
```

This installs both `instructor` and `litellm` as a single dependency group. The `[litellm]` extra ensures compatible versions.

## Architecture Patterns

### Recommended Project Structure
```
src/policyfoundry/pipeline/
  __init__.py          # exports LLMClient, create_llm_client
  llm.py               # LLMClient class + factory + retry logic + health check
  schema.py            # existing: TrafficAnalysis, SecurityAssessment, etc.
  state.py             # existing: PipelineState TypedDict
  stages/              # Phase 7
  prompts/             # Phase 7
```

### Pattern 1: Instructor Client Initialization (Async)
**What:** Create an Instructor-patched async client wrapping LiteLLM's `acompletion`
**When to use:** Once at client creation, stored as instance attribute on LLMClient
**Example:**
```python
# Source: https://docs.litellm.ai/docs/tutorials/instructor
import instructor
from litellm import acompletion

# Create instructor-patched client for async structured output
client = instructor.from_litellm(acompletion, mode=instructor.Mode.JSON)
```

### Pattern 2: Structured Output Call
**What:** Use the patched client to get validated Pydantic objects from LLM
**When to use:** Every LLM call in every pipeline stage
**Example:**
```python
# Source: https://docs.litellm.ai/docs/tutorials/instructor
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

# Async call with validation retries
result = await client.chat.completions.create(
    model="ollama/llama3.2",          # LiteLLM model format
    response_model=User,               # Pydantic model for structured output
    messages=[{"role": "user", "content": "Extract: Jason is 25"}],
    max_retries=3,                     # Instructor validation retries
    api_base="http://localhost:11434", # Ollama endpoint
    temperature=0.1,                   # Per-call temperature
    max_tokens=4096,                   # Token limit
    timeout=120,                       # Request timeout
)
assert isinstance(result, User)
```

### Pattern 3: Model Name Composition
**What:** Auto-compose LiteLLM model string from provider + model fields
**When to use:** When translating LLMConfig to LiteLLM call parameters
**Example:**
```python
# LiteLLM model naming conventions:
# - Ollama: "ollama/{model}"  (uses /api/generate endpoint)
# - Ollama chat: "ollama_chat/{model}" (uses /api/chat endpoint -- preferred)
# - OpenAI: "{model}" (passthrough, e.g., "gpt-4o-mini")
# - Bedrock: "bedrock/{model}"
# - Anthropic: "anthropic/{model}"

def _compose_model_name(provider: str, model: str) -> str:
    """Compose LiteLLM model identifier from provider and model name."""
    if provider == "ollama":
        return f"ollama_chat/{model}"   # ollama_chat preferred for better responses
    if provider in ("openai",):
        return model                     # Passthrough for OpenAI
    return f"{provider}/{model}"         # Generic prefix for others
```

**Important:** Use `ollama_chat/` prefix (not `ollama/`) for Ollama. The `ollama_chat` prefix routes through Ollama's `/api/chat` endpoint which produces better structured responses than the `/api/generate` endpoint used by `ollama/`.

### Pattern 4: Transient Retry with Tenacity
**What:** Wrap the Instructor call with tenacity for transient failures
**When to use:** Around every `complete()` call to handle network/timeout errors
**Example:**
```python
# Source: https://tenacity.readthedocs.io/
import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Transient errors that should trigger retry
_TRANSIENT_EXCEPTIONS = (
    litellm.APIConnectionError,   # Network unreachable, connection refused
    litellm.Timeout,              # Request timeout
    litellm.InternalServerError,  # Provider 500 errors
    litellm.ServiceUnavailableError,  # Provider 503 errors
    litellm.RateLimitError,       # Rate limiting (429)
)

@retry(
    retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
)
async def _call_with_transient_retry(...):
    ...
```

### Pattern 5: Health Check for Ollama
**What:** Verify Ollama is reachable and the configured model is available
**When to use:** During `create_llm_client()` factory call, before returning client
**Example:**
```python
import httpx

async def _check_ollama_health(base_url: str, model: str) -> None:
    """Ping Ollama and verify model availability."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            available = [m["name"] for m in data.get("models", [])]
            # Ollama model names may include ":latest" tag
            matches = [m for m in available if m.startswith(model)]
            if not matches:
                raise PipelineError(
                    f"Model '{model}' not found in Ollama",
                    error_code="LLM_MODEL_NOT_FOUND",
                    details={"model": model, "available_models": available},
                )
    except httpx.ConnectError as exc:
        raise PipelineError(
            f"Cannot reach Ollama at {base_url}",
            error_code="LLM_UNREACHABLE",
            details={"base_url": base_url},
        ) from exc
```

### Pattern 6: LiteLLM Exception Handling
**What:** Map LiteLLM/Instructor exceptions to PipelineError
**When to use:** When Instructor retries are exhausted (validation failure)
**Example:**
```python
from instructor.core.exceptions import InstructorRetryException

try:
    result = await self._call_with_transient_retry(...)
except InstructorRetryException as exc:
    raise PipelineError(
        f"LLM structured output failed after {exc.n_attempts} attempts",
        error_code="LLM_PARSE_FAILED",
        details={
            "model": self._model_name,
            "response_model": response_model.__name__,
            "attempts": exc.n_attempts,
            "last_error": str(exc.failed_attempts[-1].exception) if exc.failed_attempts else "unknown",
        },
    ) from exc
```

### Anti-Patterns to Avoid
- **Do NOT use `from_provider("litellm/...")`:** This API does not actually support LiteLLM as a backend. Use `from_litellm()` instead.
- **Do NOT use `ollama/` prefix when `ollama_chat/` is available:** The chat endpoint produces better structured JSON responses.
- **Do NOT create Instructor client per-call:** Create once in the factory, reuse for all calls. The patched client is stateless and thread-safe.
- **Do NOT catch broad `Exception` for transient retry:** Only retry specific transient exception types. Validation errors should be handled by Instructor's inner retry, not the outer transient retry.
- **Do NOT put retry config in LLMConfig:** These are internal tuning knobs, not user-facing settings. Hardcode as module constants.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON output parsing from LLM | Custom regex/JSON extraction | Instructor's `response_model` parameter | Handles schema injection into prompt, JSON extraction, Pydantic validation, and error feedback loop automatically |
| Validation retry with error feedback | Manual parse-validate-reask loop | Instructor's `max_retries` | Appends validation errors to message history and re-asks LLM automatically; handles edge cases like partial JSON, truncated output |
| Transient retry with backoff | Manual sleep/retry loop | tenacity `@retry` decorator | Production-grade retry with async support, jitter, configurable backoff, exception filtering, and logging hooks |
| Provider-agnostic LLM routing | Custom HTTP calls per provider | LiteLLM `acompletion` | Handles auth, endpoints, model naming, response normalization across 100+ providers |
| Pydantic error URL stripping | Manual env var management | `instructor.utils.disable_pydantic_error_url()` | Reduces token waste in validation error messages fed back to LLM |

**Key insight:** The Instructor + LiteLLM combination handles the entire structured-output lifecycle (prompt augmentation, JSON extraction, validation, retry-with-feedback, provider routing) -- custom solutions will miss edge cases around truncated output, malformed JSON, and provider-specific response formats.

## Common Pitfalls

### Pitfall 1: Using `ollama/` Instead of `ollama_chat/`
**What goes wrong:** LiteLLM routes `ollama/model` through `/api/generate` endpoint which returns plain text, not chat-formatted responses. Structured output parsing fails more often.
**Why it happens:** The `ollama/` prefix seems intuitive. Older documentation uses it.
**How to avoid:** Always use `ollama_chat/` prefix for Ollama models. This routes through `/api/chat` which supports proper message formatting and produces more reliable JSON output.
**Warning signs:** Frequent JSON parse failures with Ollama despite working with cloud providers.

### Pitfall 2: Instructor Retries Multiplied by Transient Retries
**What goes wrong:** With 3 Instructor retries and 3 transient retries, worst case is 12 LLM calls (3 transient * (1 initial + 3 validation)). This can be slow and expensive.
**Why it happens:** Two independent retry layers compound multiplicatively.
**How to avoid:** Keep both retry counts low (3 each). Log each retry attempt with level/type so debugging is clear. Document the worst-case math in code comments.
**Warning signs:** Unexpectedly long response times during validation failures.

### Pitfall 3: Ollama Model Name Tag Mismatch
**What goes wrong:** User configures `model: llama3.2` but Ollama has it as `llama3.2:latest` or `llama3.2:7b`. Health check model verification fails with a false negative.
**Why it happens:** Ollama uses `name:tag` format; users often omit the tag.
**How to avoid:** Use `startswith` matching when checking model availability, not exact match. The model name without tag should match any variant.
**Warning signs:** "Model not found" errors when `ollama list` shows the model is pulled.

### Pitfall 4: LiteLLM's `api_base` Required for Ollama
**What goes wrong:** LiteLLM calls fail with connection errors even though Ollama is running.
**Why it happens:** LiteLLM does not auto-default to `http://localhost:11434` for Ollama -- `api_base` must be explicitly passed to every call.
**How to avoid:** Always pass `api_base` as a keyword argument in the completion call, not just in client creation. The CONTEXT.md decision to auto-default `base_url` addresses this.
**Warning signs:** `APIConnectionError` when Ollama is confirmed running.

### Pitfall 5: InstructorRetryException vs Pydantic ValidationError
**What goes wrong:** Code catches `ValidationError` expecting it to be the final failure, but Instructor catches `ValidationError` internally for its retry loop and raises `InstructorRetryException` when retries are exhausted.
**Why it happens:** Confusion about which exception surfaces after retry exhaustion.
**How to avoid:** Catch `InstructorRetryException` (from `instructor.core.exceptions`) for exhausted validation retries. `ValidationError` is only raised if `max_retries=0`.
**Warning signs:** Unhandled `InstructorRetryException` propagating to the CLI.

### Pitfall 6: Pyright Strict Mode with Instructor's Dynamic Types
**What goes wrong:** `instructor.from_litellm()` returns a dynamically-typed client that Pyright strict mode flags.
**Why it happens:** Instructor patches functions dynamically; type stubs may be incomplete.
**How to avoid:** Use `type: ignore[...]` comments strategically (consistent with project's existing pattern for flexible types). Keep type ignores minimal and documented.
**Warning signs:** Pyright errors on the Instructor client initialization and `chat.completions.create` calls.

## Code Examples

Verified patterns from official sources:

### Complete LLMClient Skeleton
```python
# Source: Synthesized from https://docs.litellm.ai/docs/tutorials/instructor
#         and https://python.useinstructor.com/integrations/litellm/
"""LLM client with structured output via Instructor + LiteLLM."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import instructor
import litellm
from litellm import acompletion
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from policyfoundry.exceptions import PipelineError

if TYPE_CHECKING:
    from policyfoundry.config.models import LLMConfig

T = TypeVar("T", bound=BaseModel)

# --- Module constants (not user-configurable) ---
_MAX_VALIDATION_RETRIES = 3
_MAX_TRANSIENT_RETRIES = 3
_BACKOFF_MIN = 1
_BACKOFF_MAX = 4
_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"

_TRANSIENT_EXCEPTIONS = (
    litellm.APIConnectionError,
    litellm.Timeout,
    litellm.InternalServerError,
    litellm.ServiceUnavailableError,
    litellm.RateLimitError,
)
```

### Instructor Client Initialization for Async + JSON Mode
```python
# Source: https://docs.litellm.ai/docs/tutorials/instructor
client = instructor.from_litellm(
    acompletion,
    mode=instructor.Mode.JSON,
)
```

### Complete Async Call with Structured Output
```python
# Source: https://docs.litellm.ai/docs/tutorials/instructor
from instructor.core.exceptions import InstructorRetryException

async def complete(
    self,
    messages: list[dict[str, str]],
    response_model: type[T],
    temperature: float | None = None,
) -> T:
    """Call LLM and return validated Pydantic object."""
    try:
        result = await self._call_with_retry(
            messages=messages,
            response_model=response_model,
            temperature=temperature or self._default_temperature,
        )
        return result  # type: ignore[return-value]
    except InstructorRetryException as exc:
        raise PipelineError(
            f"Structured output failed after {exc.n_attempts} attempts",
            error_code="LLM_PARSE_FAILED",
            details={
                "model": self._model_name,
                "response_model": response_model.__name__,
                "attempts": exc.n_attempts,
                "last_error": str(exc.failed_attempts[-1].exception)
                    if exc.failed_attempts else "unknown",
            },
        ) from exc
```

### LiteLLM Exception Types for Transient Retry
```python
# Source: https://docs.litellm.ai/docs/exception_mapping
# All inherit from OpenAI exception types:
#   litellm.APIConnectionError  -> openai.APIConnectionError  (500)
#   litellm.Timeout             -> openai.APITimeoutError     (408)
#   litellm.InternalServerError -> openai.InternalServerError (>=500)
#   litellm.ServiceUnavailableError -> openai.APIStatusError  (503)
#   litellm.RateLimitError      -> openai.RateLimitError      (429)
#   litellm.AuthenticationError -> openai.AuthenticationError  (401)
#   litellm.BadRequestError     -> openai.BadRequestError     (400)
```

### Disable Pydantic Error URLs (Token Optimization)
```python
# Source: https://python.useinstructor.com/concepts/reask_validation/
from instructor.utils import disable_pydantic_error_url

# Call early (e.g., in factory function) to reduce token waste
# when validation errors are fed back to LLM
disable_pydantic_error_url()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `instructor.from_provider("litellm/...")` | `instructor.from_litellm(acompletion)` | Current (from_provider doesn't support LiteLLM) | Must use `from_litellm` for LiteLLM integration |
| `ollama/` model prefix | `ollama_chat/` model prefix | LiteLLM docs current | Better structured output from chat endpoint vs generate endpoint |
| Instructor `Mode.TOOLS` | Instructor `Mode.JSON` for broad compatibility | Current | JSON mode works across all providers; TOOLS mode limited to specific models |
| Manual JSON parse + retry | Instructor handles full lifecycle | Instructor >=1.0 | Eliminates custom parsing, validation, error feedback code |

**Deprecated/outdated:**
- `instructor.patch()` -- replaced by `instructor.from_litellm()` / `instructor.from_provider()` in v1.0+
- `instructor.from_provider("litellm/...")` -- documented but not actually supported; use `from_litellm()` instead

## Discretionary Recommendations

For items marked as "Claude's Discretion" in CONTEXT.md:

### Transient Retry: Use tenacity
**Recommendation:** tenacity decorator on an inner async method
**Rationale:** Already a dependency of both instructor and litellm. Provides async-aware retry (`retry` works on async functions natively), configurable exception filtering, exponential backoff, and logging hooks. A manual loop would duplicate these features.

### Health Check HTTP Client: Use httpx
**Recommendation:** httpx.AsyncClient for health check calls
**Rationale:** Already a litellm dependency. Clean async context manager API. Simple GET request to `/api/tags` does not need aiohttp's heavier connection pooling. httpx is the modern standard for async HTTP in Python.

### Non-Ollama Provider Health Checks: Simple completion ping
**Recommendation:** For non-Ollama providers (OpenAI, Bedrock), perform a minimal completion call with a trivial prompt rather than endpoint-specific health checks. Each cloud provider has different health check APIs. A small completion call (`"Respond with OK"`) verifies auth, model access, and connectivity in one step.
**Fallback:** If health check is deemed too expensive for cloud providers, make it Ollama-only and skip for others. The factory can check `provider == "ollama"` and only run the detailed health check for local providers.

### PipelineError Subclass Naming: No subclass needed
**Recommendation:** Use `PipelineError` directly with `error_code` field for LLM-specific errors. Error codes `LLM_UNREACHABLE`, `LLM_MODEL_NOT_FOUND`, and `LLM_PARSE_FAILED` provide sufficient granularity without adding new exception classes.
**Rationale:** Consistent with existing project pattern -- `PipelineError` already has `error_code` and `details` dict. Adding subclasses (e.g., `LLMUnreachableError`) would diverge from the established error_code pattern used by `AdapterError`, `IngestionError`, etc.

### Test Fixture Design: Mock at Instructor level
**Recommendation:** Mock `instructor.from_litellm` return value to return pre-built Pydantic objects. Do not mock raw HTTP responses.
**Rationale:** Tests should verify the LLMClient behavior (retry logic, error mapping, model name composition), not Instructor/LiteLLM internals. Mocking at the Instructor client level keeps tests fast and stable. Use `unittest.mock.AsyncMock` for the patched client's `chat.completions.create`.

## Open Questions

1. **Ollama `ollama_chat/` vs `ollama/` prefix confirmation**
   - What we know: LiteLLM docs recommend `ollama_chat/` for chat endpoint (better responses); `ollama/` uses generate endpoint
   - What's unclear: Whether Instructor's JSON mode injection works equally well with both prefixes
   - Recommendation: Use `ollama_chat/` as default; if JSON parsing issues arise during testing, fall back to `ollama/` with `format="json"` parameter

2. **Instructor `from_litellm` type annotations**
   - What we know: The function returns a dynamically patched client; Pyright strict mode may flag it
   - What's unclear: Exact type annotations available in instructor 1.14.x
   - Recommendation: Use `type: ignore` comments as needed, consistent with project's existing pattern for flexible types (see `list[dict]  # type: ignore[type-arg]` in schema.py)

3. **httpx as explicit dependency**
   - What we know: httpx is a dependency of litellm, so it is available at runtime
   - What's unclear: Whether it should be declared as an explicit dependency in pyproject.toml for the health check usage
   - Recommendation: Do NOT add httpx to pyproject.toml explicitly. It is a transitive dependency of litellm. If litellm ever drops httpx, the health check can switch to aiohttp (also a litellm dependency).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0 + pytest-asyncio 1.3 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_pipeline/ -x -q` |
| Full suite command | `pytest --tb=short -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-06a | LLM calls go through LiteLLM and reach Ollama when configured | unit | `pytest tests/test_pipeline/test_llm.py::test_complete_calls_litellm -x` | No -- Wave 0 |
| PIPE-06b | LLM responses parsed into Pydantic models without free-text parsing | unit | `pytest tests/test_pipeline/test_llm.py::test_complete_returns_pydantic_model -x` | No -- Wave 0 |
| PIPE-06c | Validation retry feeds error back to LLM (Instructor max_retries) | unit | `pytest tests/test_pipeline/test_llm.py::test_validation_retry_on_parse_failure -x` | No -- Wave 0 |
| PIPE-06d | Switching provider in config works without code changes | unit | `pytest tests/test_pipeline/test_llm.py::test_model_name_composition_providers -x` | No -- Wave 0 |
| PIPE-06e | Transient retry handles ConnectionError/Timeout | unit | `pytest tests/test_pipeline/test_llm.py::test_transient_retry_on_connection_error -x` | No -- Wave 0 |
| PIPE-06f | Health check detects unreachable Ollama | unit | `pytest tests/test_pipeline/test_llm.py::test_health_check_unreachable -x` | No -- Wave 0 |
| PIPE-06g | Health check detects missing model | unit | `pytest tests/test_pipeline/test_llm.py::test_health_check_model_not_found -x` | No -- Wave 0 |
| PIPE-06h | PipelineError raised with correct error_code on exhaustion | unit | `pytest tests/test_pipeline/test_llm.py::test_pipeline_error_on_retry_exhaustion -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pipeline/test_llm.py -x -q`
- **Per wave merge:** `pytest --tb=short -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pipeline/__init__.py` -- package init
- [ ] `tests/test_pipeline/conftest.py` -- shared fixtures (mock LLM client, sample messages, sample Pydantic response models)
- [ ] `tests/test_pipeline/test_llm.py` -- covers PIPE-06a through PIPE-06h

## Sources

### Primary (HIGH confidence)
- [LiteLLM Ollama docs](https://docs.litellm.ai/docs/providers/ollama) -- model naming, api_base, JSON mode, async support
- [LiteLLM Instructor tutorial](https://docs.litellm.ai/docs/tutorials/instructor) -- `from_litellm` pattern, sync/async examples, max_retries
- [LiteLLM Exception Mapping](https://docs.litellm.ai/docs/exception_mapping) -- complete exception hierarchy with HTTP status codes and inheritance
- [Instructor LiteLLM integration](https://python.useinstructor.com/integrations/litellm/) -- `from_litellm`, `from_provider`, async patterns
- [Instructor Ollama integration](https://python.useinstructor.com/integrations/ollama/) -- JSON mode vs TOOLS mode, timeout handling, async support
- [Instructor Retry Logic](https://python.useinstructor.com/concepts/retrying/) -- tenacity integration, max_retries, exponential backoff
- [Instructor Reask Validation](https://python.useinstructor.com/concepts/reask_validation/) -- how validation errors are fed back to LLM, disable_pydantic_error_url
- [Instructor Error Handling](https://python.useinstructor.com/concepts/error_handling/) -- InstructorRetryException, exception hierarchy, import paths

### Secondary (MEDIUM confidence)
- [Instructor PyPI](https://pypi.org/project/instructor/) -- version 1.14.5, dependencies, extras
- [LiteLLM PyPI](https://pypi.org/project/litellm/) -- version 1.82.1, dependencies
- [Instructor DeepWiki](https://deepwiki.com/instructor-ai/instructor/2.1-installation-and-setup) -- complete dependency list with versions
- [Instructor GitHub issue #1710](https://github.com/567-labs/instructor/issues/1710) -- `from_provider` does not support LiteLLM

### Tertiary (LOW confidence)
- [LiteLLM GitHub issue #17807](https://github.com/BerriAI/litellm/issues/17807) -- ollama_chat JSON/tool-call response issues (bug report, may be fixed)
- [LiteLLM GitHub issue #5172](https://github.com/BerriAI/litellm/issues/5172) -- Ollama structured output feature request

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- both libraries are well-documented, actively maintained (Jan 2026 releases), and the `from_litellm` pattern is verified across multiple official sources
- Architecture: HIGH -- CONTEXT.md decisions are specific and well-supported by library capabilities; patterns verified against official docs
- Pitfalls: HIGH -- identified from official GitHub issues, documentation, and known library behavior (ollama vs ollama_chat, from_provider limitation)
- Discretionary items: MEDIUM -- recommendations are informed by library capabilities but involve implementation choices that may need adjustment during coding

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (30 days -- libraries are stable, major versions unlikely to change)