"""Tests for output data models (PipelineResult, TokenUsage).

Verifies that PipelineResult can be constructed from PipelineState dicts
and that TokenUsage correctly defaults to zeros and supports accumulation.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from policyfoundry.output.models import PipelineResult, TokenUsage

if TYPE_CHECKING:
    from policyfoundry.pipeline.state import PipelineState


class TestPipelineResultFromState:
    """Verify PipelineResult construction from PipelineState dict."""

    def test_pipeline_result_from_state(self, sample_pipeline_state: PipelineState) -> None:
        """PipelineResult must be constructable from a full PipelineState dict."""
        result = PipelineResult.from_state(sample_pipeline_state)
        assert result.run_id == "run-test-20260311-001"
        assert result.started_at == "2026-03-11T10:00:00+00:00"
        assert result.current_stage == "decide"
        assert result.analysis is not None
        assert result.analysis.total_flows == 15000
        assert result.assessment is not None
        assert result.assessment.overall_risk.value == "MEDIUM"
        assert result.proposals is not None
        assert len(result.proposals) == 2
        assert result.decisions is not None
        assert len(result.decisions) == 3
        assert result.token_usage is not None
        assert result.token_usage.prompt_tokens == 4200
        assert result.token_usage.total_cost == pytest.approx(0.0042)


class TestPipelineResultSerialization:
    """Verify model_dump_json() produces valid JSON."""

    def test_pipeline_result_serialization(self, sample_pipeline_state: PipelineState) -> None:
        """PipelineResult.model_dump_json() must produce valid JSON."""
        result = PipelineResult.from_state(sample_pipeline_state)
        json_str = result.model_dump_json(indent=2)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["run_id"] == "run-test-20260311-001"
        assert "analysis" in parsed
        assert "assessment" in parsed
        assert "proposals" in parsed
        assert "decisions" in parsed


class TestTokenUsageDefaults:
    """Verify TokenUsage defaults to zeros."""

    def test_token_usage_defaults(self) -> None:
        """A default TokenUsage must have all counts at zero."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.total_cost == pytest.approx(0.0)


class TestTokenUsageAccumulation:
    """Verify TokenUsage can sum multiple calls."""

    def test_token_usage_accumulation(self) -> None:
        """Accumulating two TokenUsage instances must sum all fields."""
        usage1 = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            total_cost=0.001,
        )
        usage2 = TokenUsage(
            prompt_tokens=200,
            completion_tokens=80,
            total_tokens=280,
            total_cost=0.002,
        )
        combined = usage1 + usage2
        assert combined.prompt_tokens == 300
        assert combined.completion_tokens == 130
        assert combined.total_tokens == 430
        assert combined.total_cost == pytest.approx(0.003)
