"""Tests for VPC pipeline runner error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.runner import run_pipeline


class TestRunnerErrorHandler:
    """Tests for run_pipeline error handler stage extraction."""

    async def test_pipeline_error_passes_through(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """PipelineError raised by a stage passes through unchanged."""
        original = PipelineError(
            "Stage failed",
            error_code="LLM_PARSE_FAILED",
            details={"stage": "generate", "model": "test"},
        )

        with patch(
            "policyfoundry.pipeline.runner.build_pipeline",
        ) as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.ainvoke = AsyncMock(side_effect=original)
            mock_build.return_value = mock_pipeline

            with pytest.raises(PipelineError) as exc_info:
                await run_pipeline(mock_llm_client, mock_adapter, "/tmp/data", ["sg-1"])

            assert exc_info.value is original
            assert exc_info.value.details["stage"] == "generate"

    async def test_non_pipeline_error_wrapped_with_unknown_stage(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """Non-PipelineError with no __cause__ reports stage as 'unknown'."""
        with patch(
            "policyfoundry.pipeline.runner.build_pipeline",
        ) as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.ainvoke = AsyncMock(side_effect=RuntimeError("unexpected"))
            mock_build.return_value = mock_pipeline

            with pytest.raises(PipelineError) as exc_info:
                await run_pipeline(mock_llm_client, mock_adapter, "/tmp/data", ["sg-1"])

            assert exc_info.value.error_code == "PIPELINE_STAGE_FAILED"
            assert exc_info.value.details["stage"] == "unknown"

    async def test_wrapped_pipeline_error_extracts_stage(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """Exception with PipelineError __cause__ extracts stage from cause."""
        cause = PipelineError(
            "LLM failed",
            error_code="LLM_CALL_FAILED",
            details={"stage": "assess"},
        )
        wrapper = RuntimeError("graph execution failed")
        wrapper.__cause__ = cause

        with patch(
            "policyfoundry.pipeline.runner.build_pipeline",
        ) as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.ainvoke = AsyncMock(side_effect=wrapper)
            mock_build.return_value = mock_pipeline

            with pytest.raises(PipelineError) as exc_info:
                await run_pipeline(mock_llm_client, mock_adapter, "/tmp/data", ["sg-1"])

            assert exc_info.value.details["stage"] == "assess"
            assert "assess" in str(exc_info.value)

    async def test_does_not_use_initial_state_for_stage(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """Runner does NOT report 'starting' from initial_state — reports 'unknown'."""
        with patch(
            "policyfoundry.pipeline.runner.build_pipeline",
        ) as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.ainvoke = AsyncMock(side_effect=ValueError("boom"))
            mock_build.return_value = mock_pipeline

            with pytest.raises(PipelineError) as exc_info:
                await run_pipeline(mock_llm_client, mock_adapter, "/tmp/data", ["sg-1"])

            # Must NOT be "starting" — that was the old bug
            assert exc_info.value.details["stage"] != "starting"
            assert exc_info.value.details["stage"] == "unknown"
