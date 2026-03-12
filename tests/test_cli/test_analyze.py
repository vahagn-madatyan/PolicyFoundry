"""CLI integration tests for the `policyfoundry analyze` command.

Tests cover:
- Rich formatted output (default)
- JSON formatted output (--format json)
- Error handling for missing config / bad source
- Token cost display in output footer
- ReadOnlyAdapter safety enforcement
"""

from __future__ import annotations

import copy
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from policyfoundry.adapters.schema import AdapterCapabilities
from policyfoundry.exceptions import (
    AdapterError,
    ConfigError,
    PipelineError,
    PolicyFoundryError,
)
from policyfoundry.main import app
from policyfoundry.output.models import TokenUsage


def _make_mocks(sample_state: dict):
    """Create a full set of mocks for the analyze command."""
    from policyfoundry.config.models import PolicyFoundryConfig

    mock_cfg = PolicyFoundryConfig(
        targets={"security_group_ids": ["sg-12345"]},
    )

    mock_usage = TokenUsage(
        prompt_tokens=1500,
        completion_tokens=500,
        total_tokens=2000,
        total_cost=0.0045,
    )

    mock_llm = MagicMock()
    mock_llm.get_usage.return_value = mock_usage

    mock_adapter = MagicMock()
    mock_adapter.get_rules = AsyncMock(return_value=[])
    mock_adapter.validate = AsyncMock()
    mock_adapter.capabilities = MagicMock(
        return_value=AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
        )
    )

    # Pipeline state without token_usage — CLI adds it from llm_client.get_usage()
    pipeline_state = copy.deepcopy(sample_state)
    pipeline_state.pop("token_usage", None)

    return mock_cfg, mock_llm, mock_adapter, pipeline_state


def _patch_analyze(mock_cfg, mock_llm, mock_adapter, pipeline_state):
    """Return a context manager that patches all analyze dependencies."""
    from contextlib import ExitStack

    stack = ExitStack()

    def _enter(stack):
        stack.enter_context(patch("policyfoundry.main.load_config", return_value=mock_cfg))
        stack.enter_context(patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm))
        stack.enter_context(patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter))
        stack.enter_context(patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state))
        return stack

    return stack, _enter


class TestAnalyzeRichOutput:
    """Tests for `policyfoundry analyze` with Rich (default) output format."""

    def test_analyze_rich_output_exits_zero(self, cli_runner, sample_pipeline_state):
        """analyze command with --format rich exits 0 on success."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"

    def test_analyze_rich_output_contains_traffic_analysis(self, cli_runner, sample_pipeline_state):
        """Rich output includes traffic analysis section."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert "Traffic Analysis" in result.output

    def test_analyze_rich_output_contains_rule_proposals(self, cli_runner, sample_pipeline_state):
        """Rich output includes rule proposals section."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert "Policy Proposals" in result.output

    def test_analyze_rich_output_contains_risk_table(self, cli_runner, sample_pipeline_state):
        """Rich output includes decisions table."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert "Decisions" in result.output

    def test_analyze_rich_output_contains_token_cost(self, cli_runner, sample_pipeline_state):
        """Rich output includes token usage and cost summary in footer."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert "Token Usage" in result.output


class TestAnalyzeJsonOutput:
    """Tests for `policyfoundry analyze --format json` output."""

    def test_analyze_json_output_exits_zero(self, cli_runner, sample_pipeline_state):
        """analyze command with --format json exits 0 on success."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--format", "json", "--sg-ids", "sg-12345"])
            assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"

    def test_analyze_json_output_is_valid_json(self, cli_runner, sample_pipeline_state):
        """JSON output is parseable as valid JSON."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--format", "json", "--sg-ids", "sg-12345"])
            parsed = json.loads(result.output)
            assert isinstance(parsed, dict)

    def test_analyze_json_output_contains_pipeline_stages(self, cli_runner, sample_pipeline_state):
        """JSON output includes data from all pipeline stages."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--format", "json", "--sg-ids", "sg-12345"])
            parsed = json.loads(result.output)
            assert "run_id" in parsed
            assert "analysis" in parsed
            assert "assessment" in parsed

    def test_analyze_json_output_contains_token_usage(self, cli_runner, sample_pipeline_state):
        """JSON output includes token_usage field with counts and cost."""
        mock_cfg, mock_llm, mock_adapter, pipeline_state = _make_mocks(sample_pipeline_state)

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch("policyfoundry.main.run_pipeline", new_callable=AsyncMock, return_value=pipeline_state),
        ):
            result = cli_runner.invoke(app, ["analyze", "--format", "json", "--sg-ids", "sg-12345"])
            parsed = json.loads(result.output)
            assert "token_usage" in parsed
            assert parsed["token_usage"] is not None


class TestAnalyzeErrorHandling:
    """Tests for analyze command error paths."""

    def test_analyze_config_error_shows_actionable_message(self, cli_runner):
        """ConfigError produces exit code 1 with Rich error panel, not a traceback."""
        with patch(
            "policyfoundry.main.load_config",
            side_effect=ConfigError(
                "Invalid config",
                error_code="CONFIG_INVALID",
                details={"field": "llm.provider"},
            ),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert result.exit_code == 1
            assert "ConfigError" in result.output
            assert "CONFIG_INVALID" in result.output
            # Should NOT show raw traceback in non-debug mode
            assert "Traceback" not in result.output

    def test_analyze_adapter_error_shows_actionable_message(self, cli_runner):
        """AdapterError produces exit code 1 with error_code and details."""
        from policyfoundry.config.models import PolicyFoundryConfig

        mock_cfg = PolicyFoundryConfig(targets={"security_group_ids": ["sg-12345"]})

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=MagicMock()),
            patch(
                "policyfoundry.main.AdapterRegistry.get_adapter",
                side_effect=AdapterError(
                    "Adapter failed",
                    error_code="ADAPTER_FAILED",
                    details={"adapter": "aws_sg"},
                ),
            ),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert result.exit_code == 1
            assert "AdapterError" in result.output
            assert "ADAPTER_FAILED" in result.output

    def test_analyze_pipeline_error_shows_actionable_message(self, cli_runner):
        """PipelineError produces exit code 1 with stage context."""
        from policyfoundry.config.models import PolicyFoundryConfig

        mock_cfg = PolicyFoundryConfig(targets={"security_group_ids": ["sg-12345"]})
        mock_llm = MagicMock()
        mock_adapter = MagicMock()

        with (
            patch("policyfoundry.main.load_config", return_value=mock_cfg),
            patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=mock_llm),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
            patch(
                "policyfoundry.main.run_pipeline",
                new_callable=AsyncMock,
                side_effect=PipelineError(
                    "Pipeline failed at stage: analyze",
                    error_code="PIPELINE_STAGE_FAILED",
                    details={"stage": "analyze"},
                ),
            ),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert result.exit_code == 1
            assert "PipelineError" in result.output
            assert "PIPELINE_STAGE_FAILED" in result.output

    def test_analyze_unknown_error_shows_generic_message(self, cli_runner):
        """Unexpected exceptions produce exit code 1 with a generic error message."""
        with patch(
            "policyfoundry.main.load_config",
            side_effect=RuntimeError("Something unexpected"),
        ):
            result = cli_runner.invoke(app, ["analyze", "--sg-ids", "sg-12345"])
            assert result.exit_code == 1
            assert "Unexpected error" in result.output
