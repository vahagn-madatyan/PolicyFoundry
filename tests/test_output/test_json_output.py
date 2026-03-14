"""Tests for JSON output formatter.

Verifies that format_json() serializes PipelineState to valid JSON with
all pipeline stage data, token usage, and round-trip capability through
PipelineResult.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from policyfoundry.output.json_output import format_json
from policyfoundry.output.models import PipelineResult

if TYPE_CHECKING:
    from policyfoundry.pipeline.state import PipelineState


class TestFormatJsonValidJson:
    """Verify output is valid JSON."""

    def test_format_json_valid_json(self, sample_pipeline_state: PipelineState) -> None:
        """format_json() must produce a string that parses as valid JSON."""
        result = format_json(sample_pipeline_state)
        parsed = json.loads(result)
        assert isinstance(parsed, dict), "JSON output must be a dict"


class TestFormatJsonContainsAllStages:
    """Verify JSON has all pipeline stage keys."""

    def test_format_json_contains_all_stages(self, sample_pipeline_state: PipelineState) -> None:
        """JSON must contain analysis, assessment, proposals, and decisions keys."""
        result = format_json(sample_pipeline_state)
        parsed = json.loads(result)
        assert "analysis" in parsed, "Missing 'analysis' in JSON output"
        assert "assessment" in parsed, "Missing 'assessment' in JSON output"
        assert "proposals" in parsed, "Missing 'proposals' in JSON output"
        assert "decisions" in parsed, "Missing 'decisions' in JSON output"
        assert parsed["analysis"]["total_flows"] == 15000
        assert parsed["assessment"]["overall_risk"] == "MEDIUM"
        assert len(parsed["proposals"]) == 2
        assert len(parsed["decisions"]) == 3


class TestFormatJsonRoundtrip:
    """Verify JSON round-trips through PipelineResult model."""

    def test_format_json_roundtrips_through_pipeline_result(
        self, sample_pipeline_state: PipelineState
    ) -> None:
        """JSON output must be loadable back into a PipelineResult model."""
        json_str = format_json(sample_pipeline_state)
        parsed = json.loads(json_str)
        result = PipelineResult(**parsed)
        assert result.run_id == "run-test-20260311-001"
        assert result.analysis is not None
        assert result.assessment is not None
        assert result.proposals is not None
        assert len(result.proposals) == 2
        assert result.decisions is not None
        assert len(result.decisions) == 3


class TestFormatJsonTokenUsage:
    """Verify token_usage is included in JSON output."""

    def test_format_json_includes_token_usage(self, sample_pipeline_state: PipelineState) -> None:
        """JSON output must include token_usage with totals."""
        result = format_json(sample_pipeline_state)
        parsed = json.loads(result)
        assert "token_usage" in parsed, "Missing 'token_usage' in JSON output"
        usage = parsed["token_usage"]
        assert usage["prompt_tokens"] == 4200
        assert usage["completion_tokens"] == 1800
        assert usage["total_tokens"] == 6000
        assert usage["total_cost"] == pytest.approx(0.0042)


class TestFormatJsonMissingStages:
    """Verify empty state produces valid JSON with null/empty fields."""

    def test_format_json_missing_stages(self, sample_pipeline_state_empty: PipelineState) -> None:
        """Minimal state must serialize to valid JSON with null/empty fields."""
        result = format_json(sample_pipeline_state_empty)
        parsed = json.loads(result)
        assert isinstance(parsed, dict), "JSON output must be a dict"
        assert parsed["run_id"] == "run-empty-20260311-001"
        assert parsed.get("analysis") is None or parsed.get("analysis") == []
        assert parsed.get("assessment") is None
        assert parsed.get("proposals") is not None
        assert parsed.get("decisions") is not None
