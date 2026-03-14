"""Tests for LLMClient with mocked Instructor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from policyfoundry.config.models import LLMConfig
from policyfoundry.exceptions import PipelineError
from policyfoundry.output.models import TokenUsage


class _SampleResponse(BaseModel):
    """Trivial Pydantic model used as a response_model in tests."""

    answer: str


def _mock_raw_response(*, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost: float) -> MagicMock:
    """Create a mock LiteLLM raw response with usage data."""
    raw = MagicMock()
    raw.usage = MagicMock(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    raw._hidden_params = {"response_cost": cost}
    return raw


def _mock_raw_response_no_usage() -> MagicMock:
    """Create a mock LiteLLM raw response without usage data."""
    raw = MagicMock(spec=[])
    return raw


class TestComposeModelName:
    """Tests for _compose_model_name helper."""

    def test_compose_model_name_ollama(self) -> None:
        from policyfoundry.pipeline.llm import _compose_model_name

        assert _compose_model_name("ollama", "llama3.2") == "ollama_chat/llama3.2"

    def test_compose_model_name_openai(self) -> None:
        from policyfoundry.pipeline.llm import _compose_model_name

        assert _compose_model_name("openai", "gpt-4o") == "gpt-4o"

    def test_compose_model_name_bedrock(self) -> None:
        from policyfoundry.pipeline.llm import _compose_model_name

        assert _compose_model_name("bedrock", "claude-3") == "bedrock/claude-3"

    def test_compose_model_name_anthropic(self) -> None:
        from policyfoundry.pipeline.llm import _compose_model_name

        assert _compose_model_name("anthropic", "claude-3") == "anthropic/claude-3"


class TestHealthCheck:
    """Tests for _check_ollama_health."""

    async def test_health_check_unreachable(self) -> None:
        from policyfoundry.pipeline.llm import _check_ollama_health

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("policyfoundry.pipeline.llm.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PipelineError) as exc_info:
                await _check_ollama_health("http://localhost:11434", "llama3.2")

            assert exc_info.value.error_code == "LLM_UNREACHABLE"
            assert "base_url" in exc_info.value.details

    async def test_health_check_model_not_found(self) -> None:
        from policyfoundry.pipeline.llm import _check_ollama_health

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:latest"},
                {"name": "codellama:7b"},
            ]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("policyfoundry.pipeline.llm.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PipelineError) as exc_info:
                await _check_ollama_health("http://localhost:11434", "llama3.2")

            assert exc_info.value.error_code == "LLM_MODEL_NOT_FOUND"
            assert "available_models" in exc_info.value.details

    async def test_health_check_model_found_with_tag(self) -> None:
        from policyfoundry.pipeline.llm import _check_ollama_health

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:latest"},
            ]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("policyfoundry.pipeline.llm.httpx.AsyncClient", return_value=mock_client):
            # Should not raise
            await _check_ollama_health("http://localhost:11434", "llama3.2")


class TestDefaults:
    """Tests for default configuration handling."""

    async def test_ollama_default_base_url(self) -> None:
        from policyfoundry.pipeline.llm import create_llm_client

        config = LLMConfig(provider="ollama", model="llama3.2", base_url=None)

        with (
            patch("policyfoundry.pipeline.llm.instructor") as mock_instructor,
            patch("policyfoundry.pipeline.llm._check_ollama_health", new_callable=AsyncMock) as mock_health,
        ):
            mock_instructor.from_litellm.return_value = MagicMock()
            mock_instructor.Mode.JSON = "json"

            await create_llm_client(config)

            mock_health.assert_awaited_once()
            call_args = mock_health.call_args
            assert call_args[0][0] == "http://localhost:11434"


class TestComplete:
    """Tests for LLMClient.complete()."""

    async def test_complete_calls_litellm(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="42")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse)

        mock_instructor_client.chat.completions.create_with_completion.assert_awaited_once()
        kwargs = mock_instructor_client.chat.completions.create_with_completion.call_args.kwargs
        assert kwargs["model"] == "ollama_chat/llama3.2"
        assert kwargs["response_model"] is _SampleResponse
        assert kwargs["messages"] == sample_messages

    async def test_complete_returns_pydantic_model(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="hello")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        result = await llm_client.complete(sample_messages, _SampleResponse)

        assert isinstance(result, _SampleResponse)
        assert result.answer == "hello"

    async def test_complete_temperature_override(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="warm")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse, temperature=0.9)

        kwargs = mock_instructor_client.chat.completions.create_with_completion.call_args.kwargs
        assert kwargs["temperature"] == 0.9

    async def test_complete_uses_default_temperature(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="cool")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse)

        kwargs = mock_instructor_client.chat.completions.create_with_completion.call_args.kwargs
        assert kwargs["temperature"] == 0.1


class TestTokenTracking:
    """Tests for LLMClient token usage tracking."""

    async def test_complete_tracks_token_usage(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        """Calling complete() twice accumulates token usage."""
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="42")
        raw1 = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)
        raw2 = _mock_raw_response(prompt_tokens=200, completion_tokens=80, total_tokens=280, cost=0.002)

        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=[(model, raw1), (model, raw2)]
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse, stage="analyze")
        await llm_client.complete(sample_messages, _SampleResponse, stage="assess")

        usage = llm_client.get_usage()
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 130
        assert usage.total_tokens == 430
        assert usage.total_cost == pytest.approx(0.003)
        assert len(usage.calls) == 2
        assert usage.calls[0]["stage"] == "analyze"
        assert usage.calls[1]["stage"] == "assess"

    async def test_complete_handles_missing_usage(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        """Raw response without .usage attribute doesn't crash."""
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="no-usage")
        raw = _mock_raw_response_no_usage()
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        result = await llm_client.complete(sample_messages, _SampleResponse)

        assert result.answer == "no-usage"
        usage = llm_client.get_usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert len(usage.calls) == 1

    async def test_get_usage_returns_token_usage(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
    ) -> None:
        """get_usage() returns a TokenUsage instance."""
        from policyfoundry.pipeline.llm import LLMClient

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        usage = llm_client.get_usage()
        assert isinstance(usage, TokenUsage)
        assert usage.prompt_tokens == 0
        assert usage.total_cost == 0.0

    async def test_cost_extraction_from_hidden_params(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        """Cost is correctly extracted from _hidden_params.response_cost."""
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="costly")
        raw = _mock_raw_response(prompt_tokens=50, completion_tokens=25, total_tokens=75, cost=0.0042)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="openai/gpt-4o",
            base_url=None,
        )

        await llm_client.complete(sample_messages, _SampleResponse, stage="assess")

        usage = llm_client.get_usage()
        assert usage.total_cost == pytest.approx(0.0042)
        assert usage.calls[0]["cost"] == pytest.approx(0.0042)

    async def test_cost_fallback_for_local_model(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        """Cost stays 0.0 when _hidden_params is missing or cost is None."""
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="local")

        # First raw: _hidden_params has response_cost = None
        raw1 = MagicMock()
        raw1.usage = MagicMock(prompt_tokens=20, completion_tokens=10, total_tokens=30)
        raw1._hidden_params = {"response_cost": None}

        # Second raw: _hidden_params is not a dict
        raw2 = MagicMock()
        raw2.usage = MagicMock(prompt_tokens=15, completion_tokens=5, total_tokens=20)
        raw2._hidden_params = None

        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=[(model, raw1), (model, raw2)]
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse, stage="s1")
        await llm_client.complete(sample_messages, _SampleResponse, stage="s2")

        usage = llm_client.get_usage()
        assert usage.total_cost == 0.0
        assert usage.calls[0]["cost"] == 0.0
        assert usage.calls[1]["cost"] == 0.0
        assert usage.prompt_tokens == 35
        assert usage.total_tokens == 50

    async def test_get_usage_returns_copy(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        """Modifying returned TokenUsage doesn't affect internal state."""
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="safe")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.01)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse)

        # Get a copy and mutate it
        usage_copy = llm_client.get_usage()
        usage_copy.prompt_tokens = 9999
        usage_copy.calls.clear()

        # Internal state should be unchanged
        internal = llm_client.get_usage()
        assert internal.prompt_tokens == 100
        assert len(internal.calls) == 1

    async def test_reset_usage(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        """reset_usage() clears accumulated data."""
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="42")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)
        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(model, raw)
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        await llm_client.complete(sample_messages, _SampleResponse)

        assert llm_client.get_usage().prompt_tokens == 100

        llm_client.reset_usage()

        usage = llm_client.get_usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.total_cost == 0.0
        assert len(usage.calls) == 0


class TestValidationRetry:
    """Tests for Instructor validation retry error handling."""

    async def test_validation_retry_on_parse_failure(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        from instructor.core.exceptions import InstructorRetryException
        from policyfoundry.pipeline.llm import LLMClient

        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=InstructorRetryException(
                n_attempts=3,
                messages=[],
                total_usage=100,
                last_completion=None,
            )
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        with pytest.raises(PipelineError) as exc_info:
            await llm_client.complete(sample_messages, _SampleResponse)

        assert exc_info.value.error_code == "LLM_PARSE_FAILED"
        assert "model" in exc_info.value.details
        assert exc_info.value.details["response_model"] == "_SampleResponse"
        assert exc_info.value.details["attempts"] == 3


class TestTransientRetry:
    """Tests for tenacity transient retry behaviour."""

    async def test_transient_retry_on_connection_error(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        import litellm
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="recovered")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)

        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=[
                litellm.APIConnectionError(message="Connection refused", llm_provider="ollama", model="llama3.2"),
                litellm.APIConnectionError(message="Connection refused", llm_provider="ollama", model="llama3.2"),
                (model, raw),
            ]
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        result = await llm_client.complete(sample_messages, _SampleResponse)

        assert result.answer == "recovered"
        assert mock_instructor_client.chat.completions.create_with_completion.await_count == 3

    async def test_transient_retry_on_timeout(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        import litellm
        from policyfoundry.pipeline.llm import LLMClient

        model = _SampleResponse(answer="after_timeout")
        raw = _mock_raw_response(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost=0.001)

        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=[
                litellm.Timeout(message="Request timed out", model="llama3.2", llm_provider="ollama"),
                (model, raw),
            ]
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        result = await llm_client.complete(sample_messages, _SampleResponse)

        assert result.answer == "after_timeout"
        assert mock_instructor_client.chat.completions.create_with_completion.await_count == 2

    async def test_pipeline_error_on_retry_exhaustion(
        self,
        mock_llm_config: LLMConfig,
        mock_instructor_client: MagicMock,
        sample_messages: list[dict[str, str]],
    ) -> None:
        import litellm
        from policyfoundry.pipeline.llm import LLMClient

        mock_instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=litellm.APIConnectionError(
                message="Connection refused", llm_provider="ollama", model="llama3.2"
            )
        )

        llm_client = LLMClient(
            config=mock_llm_config,
            client=mock_instructor_client,
            model_name="ollama_chat/llama3.2",
            base_url="http://localhost:11434",
        )

        with pytest.raises(PipelineError) as exc_info:
            await llm_client.complete(sample_messages, _SampleResponse)

        assert exc_info.value.error_code == "LLM_CALL_FAILED"


class TestFactory:
    """Tests for create_llm_client factory."""

    async def test_create_llm_client_factory(self) -> None:
        from policyfoundry.pipeline.llm import LLMClient, create_llm_client

        config = LLMConfig(provider="ollama", model="llama3.2")

        with (
            patch("policyfoundry.pipeline.llm.instructor") as mock_instructor,
            patch("policyfoundry.pipeline.llm._check_ollama_health", new_callable=AsyncMock),
        ):
            mock_instructor.from_litellm.return_value = MagicMock()
            mock_instructor.Mode.JSON = "json"

            client = await create_llm_client(config)
            assert isinstance(client, LLMClient)

    async def test_non_ollama_skips_health_check(self) -> None:
        from policyfoundry.pipeline.llm import create_llm_client

        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")

        with (
            patch("policyfoundry.pipeline.llm.instructor") as mock_instructor,
            patch("policyfoundry.pipeline.llm._check_ollama_health", new_callable=AsyncMock) as mock_health,
        ):
            mock_instructor.from_litellm.return_value = MagicMock()
            mock_instructor.Mode.JSON = "json"

            await create_llm_client(config)

            mock_health.assert_not_awaited()
