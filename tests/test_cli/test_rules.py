"""CLI integration tests for the `policyfoundry rules` command.

Tests cover:
- Display of current security group rules
- Rich and JSON output formats
- Error handling for adapter failures
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RuleAction,
    UniversalRule,
)
from policyfoundry.config.models import PolicyFoundryConfig
from policyfoundry.exceptions import AdapterError
from policyfoundry.main import app


def _mock_config(**overrides):
    """Create a PolicyFoundryConfig with test defaults."""
    return PolicyFoundryConfig(
        targets={"security_group_ids": ["sg-12345"]},
        **overrides,
    )


def _make_sample_rules() -> list[UniversalRule]:
    """Create sample UniversalRule instances for test output."""
    return [
        UniversalRule(
            name="allow-ssh",
            description="Allow SSH from internal network",
            direction=Direction.INBOUND,
            action=RuleAction.ALLOW,
            protocol="TCP",
            port_range=PortRange(from_port=22, to_port=22),
            source=[NetworkEndpoint(cidr="10.0.0.0/8")],
        ),
        UniversalRule(
            name="allow-https",
            description="Allow HTTPS from anywhere",
            direction=Direction.INBOUND,
            action=RuleAction.ALLOW,
            protocol="TCP",
            port_range=PortRange(from_port=443, to_port=443),
            source=[NetworkEndpoint(cidr="0.0.0.0/0")],
        ),
    ]


class TestRulesDisplay:
    """Tests for `policyfoundry rules` command."""

    def test_rules_exits_zero(self, cli_runner):
        """rules command exits 0 on success."""
        mock_adapter = MagicMock()
        mock_adapter.get_rules = AsyncMock(return_value=_make_sample_rules())

        with (
            patch("policyfoundry.main.load_config", return_value=_mock_config()),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
        ):
            result = cli_runner.invoke(app, ["rules", "--sg-id", "sg-12345"])
            assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"

    def test_rules_rich_output_shows_rule_table(self, cli_runner):
        """Rich output displays rules in a formatted table."""
        mock_adapter = MagicMock()
        mock_adapter.get_rules = AsyncMock(return_value=_make_sample_rules())

        with (
            patch("policyfoundry.main.load_config", return_value=_mock_config()),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
        ):
            result = cli_runner.invoke(app, ["rules", "--sg-id", "sg-12345"])
            assert "allow-ssh" in result.output
            # Rich may truncate long names; check prefix
            assert "allow-ht" in result.output
            assert "INBOUND" in result.output

    def test_rules_json_output_is_valid(self, cli_runner):
        """JSON output is parseable and contains rule data."""
        mock_adapter = MagicMock()
        mock_adapter.get_rules = AsyncMock(return_value=_make_sample_rules())

        with (
            patch("policyfoundry.main.load_config", return_value=_mock_config()),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
        ):
            result = cli_runner.invoke(app, ["rules", "--sg-id", "sg-12345", "--format", "json"])
            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)
            assert len(parsed) == 2

    def test_rules_empty_result_shows_message(self, cli_runner):
        """When no rules exist, shows informative message instead of empty table."""
        mock_adapter = MagicMock()
        mock_adapter.get_rules = AsyncMock(return_value=[])

        with (
            patch("policyfoundry.main.load_config", return_value=_mock_config()),
            patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=mock_adapter),
        ):
            result = cli_runner.invoke(app, ["rules", "--sg-id", "sg-12345"])
            assert result.exit_code == 0
            assert "No rules found" in result.output

    def test_rules_adapter_error_shows_actionable_message(self, cli_runner):
        """AdapterError produces exit code 1 with actionable context."""
        with (
            patch("policyfoundry.main.load_config", return_value=_mock_config()),
            patch(
                "policyfoundry.main.AdapterRegistry.get_adapter",
                side_effect=AdapterError(
                    "Failed to connect",
                    error_code="ADAPTER_AUTH_FAILED",
                    details={"adapter": "aws_sg"},
                ),
            ),
        ):
            result = cli_runner.invoke(app, ["rules", "--sg-id", "sg-12345"])
            assert result.exit_code == 1
            assert "AdapterError" in result.output
            assert "ADAPTER_AUTH_FAILED" in result.output
