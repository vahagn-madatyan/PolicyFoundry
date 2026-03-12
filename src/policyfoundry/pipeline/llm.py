"""LLM client with structured output via Instructor + LiteLLM.

Provides an async LLMClient that wraps Instructor's patched LiteLLM client
for structured Pydantic output.  Two retry layers protect calls:

- **Inner (Instructor-managed):** Validation retries that feed Pydantic errors
  back to the LLM automatically (``max_retries``).
- **Outer (tenacity):** Transient network/timeout retries with exponential
  backoff.

Worst case: ``_MAX_TRANSIENT_RETRIES * (1 + _MAX_VALIDATION_RETRIES)`` LLM
calls per request.

Token usage from each successful call is captured via Instructor's
``create_with_completion()`` and accumulated in a :class:`TokenUsage`
instance accessible via :meth:`LLMClient.get_usage`.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any, TypeVar

import httpx
import instructor
import litellm
from instructor.core.exceptions import InstructorRetryException
from instructor.utils import disable_pydantic_error_url
from litellm import acompletion
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from policyfoundry.exceptions import PipelineError
from policyfoundry.output.models import TokenUsage

if TYPE_CHECKING:
    from policyfoundry.config.models import LLMConfig

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# --- Constants -----------------------------------------------------------

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


# --- Helpers -------------------------------------------------------------


def _compose_model_name(provider: str, model: str) -> str:
    """Compose LiteLLM model identifier from provider and model name.

    - ``ollama`` -> ``ollama_chat/{model}`` (chat endpoint prefix)
    - ``openai`` -> ``{model}`` (native LiteLLM support)
    - Other -> ``{provider}/{model}``
    """
    if provider == "ollama":
        return f"ollama_chat/{model}"
    if provider == "openai":
        return model
    return f"{provider}/{model}"


async def _check_ollama_health(base_url: str, model: str) -> None:
    """Verify that Ollama is reachable and the configured model is pulled.

    Raises:
        PipelineError: With ``error_code="LLM_MODEL_NOT_FOUND"`` if the
            model is not available, or ``error_code="LLM_UNREACHABLE"``
            if Ollama cannot be reached.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            available = [m["name"] for m in data.get("models", [])]

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


def _extract_cost(raw_response: Any) -> float:
    """Extract response cost from LiteLLM hidden params.

    Returns 0.0 when ``_hidden_params`` is absent, not a dict, or
    ``response_cost`` is missing.
    """
    hidden_params = getattr(raw_response, "_hidden_params", None)
    if not isinstance(hidden_params, dict):
        return 0.0
    raw_cost = hidden_params.get("response_cost")
    return float(raw_cost) if raw_cost else 0.0


# --- LLMClient ----------------------------------------------------------


class LLMClient:
    """Async LLM client for structured Pydantic output.

    Created via the :func:`create_llm_client` factory which handles provider
    detection, model name composition, and Ollama health checks.
    """

    def __init__(
        self,
        config: LLMConfig,
        client: instructor.AsyncInstructor,
        model_name: str,
        base_url: str | None,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._base_url = base_url
        self._default_temperature = config.temperature
        self._max_tokens = config.max_tokens
        self._timeout = config.timeout
        self._api_key = config.api_key
        self._usage = TokenUsage()

    @retry(
        retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
        stop=stop_after_attempt(_MAX_TRANSIENT_RETRIES),
        wait=wait_exponential(min=_BACKOFF_MIN, max=_BACKOFF_MAX),
    )
    async def _call_with_retry(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float,
        stage: str,
    ) -> T:
        """Execute the Instructor call with transient-retry protection.

        Uses ``create_with_completion()`` to capture the raw LLM response
        alongside the validated Pydantic model, enabling token usage
        extraction.
        """
        result = await self._client.chat.completions.create_with_completion(
            model=self._model_name,
            response_model=response_model,
            messages=messages,
            max_retries=_MAX_VALIDATION_RETRIES,
            temperature=temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
            api_base=self._base_url,
            api_key=self._api_key,
        )

        model, raw_response = result

        # Extract usage metadata
        usage = getattr(raw_response, "usage", None)
        if usage is not None:
            prompt_tok = getattr(usage, "prompt_tokens", 0) or 0
            completion_tok = getattr(usage, "completion_tokens", 0) or 0
            total_tok = getattr(usage, "total_tokens", 0) or 0

            # Extract cost from LiteLLM hidden params
            cost = _extract_cost(raw_response)

            self._usage.add_call(
                prompt_tokens=prompt_tok,
                completion_tokens=completion_tok,
                total_tokens=total_tok,
                cost=cost,
                stage=stage,
            )
        else:
            logger.warning(
                "LLM response missing usage metadata; recording zeros (model=%s, stage=%s)",
                self._model_name,
                stage,
            )
            self._usage.add_call(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost=0.0,
                stage=stage,
            )

        return model

    async def complete(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float | None = None,
        stage: str = "unknown",
    ) -> T:
        """Call LLM and return a validated Pydantic object.

        Args:
            messages: Chat messages to send.
            response_model: Pydantic model class to validate against.
            temperature: Override default temperature (optional).
            stage: Pipeline stage label for usage tracking.

        Returns:
            Validated Pydantic model instance.

        Raises:
            PipelineError: On validation exhaustion or transient failure.
        """
        effective_temperature = temperature if temperature is not None else self._default_temperature

        try:
            return await self._call_with_retry(
                messages=messages,
                response_model=response_model,
                temperature=effective_temperature,
                stage=stage,
            )
        except InstructorRetryException as exc:
            raise PipelineError(
                f"Structured output failed after {exc.n_attempts} attempts",
                error_code="LLM_PARSE_FAILED",
                details={
                    "model": self._model_name,
                    "response_model": response_model.__name__,
                    "attempts": exc.n_attempts,
                    "last_error": str(exc.messages[-1]) if exc.messages else "unknown",
                },
            ) from exc
        except _TRANSIENT_EXCEPTIONS as exc:
            raise PipelineError(
                f"LLM call failed after {_MAX_TRANSIENT_RETRIES} retries: {exc}",
                error_code="LLM_CALL_FAILED",
                details={
                    "model": self._model_name,
                    "error": str(exc),
                },
            ) from exc

    def get_usage(self) -> TokenUsage:
        """Return a copy of the accumulated token usage across all calls.

        The returned copy is independent of internal state — mutations
        to the returned object do not affect the client's tracking.
        """
        return copy.deepcopy(self._usage)

    def reset_usage(self) -> None:
        """Reset accumulated token usage to zero.

        Useful for test isolation or per-stage tracking resets.
        """
        self._usage = TokenUsage()


# --- Factory -------------------------------------------------------------


async def create_llm_client(config: LLMConfig) -> LLMClient:
    """Create a ready-to-use :class:`LLMClient`.

    For Ollama providers, verifies that the server is reachable and the
    configured model is pulled before returning the client.

    Args:
        config: LLM configuration from settings.

    Returns:
        Configured :class:`LLMClient` ready for structured output calls.

    Raises:
        PipelineError: If Ollama health check fails.
    """
    disable_pydantic_error_url()

    # Resolve base URL
    base_url = config.base_url
    if config.provider == "ollama" and not base_url:
        base_url = _OLLAMA_DEFAULT_BASE_URL

    # Compose model identifier
    model_name = _compose_model_name(config.provider, config.model)

    # Create Instructor-patched async client
    client = instructor.from_litellm(acompletion, mode=instructor.Mode.JSON)

    # Ollama health check
    if config.provider == "ollama":
        await _check_ollama_health(base_url, config.model)

    return LLMClient(
        config=config,
        client=client,
        model_name=model_name,
        base_url=base_url,
    )
