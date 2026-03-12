"""CLI integration tests for the `policyfoundry rules` command.

Tests cover:
- Display of current security group rules
- Rich and JSON output formats
- Error handling for adapter failures
"""

from __future__ import annotations

import pytest


class TestRulesDisplay:
    """Tests for `policyfoundry rules` command."""

    def test_rules_exits_zero(self, cli_runner):
        """rules command exits 0 on success."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_rules_rich_output_shows_rule_table(self, cli_runner):
        """Rich output displays rules in a formatted table."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_rules_json_output_is_valid(self, cli_runner):
        """JSON output is parseable and contains rule data."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_rules_empty_result_shows_message(self, cli_runner):
        """When no rules exist, shows informative message instead of empty table."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_rules_adapter_error_shows_actionable_message(self, cli_runner):
        """AdapterError produces exit code 1 with actionable context."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")
