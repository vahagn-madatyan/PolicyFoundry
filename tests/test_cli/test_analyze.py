"""CLI integration tests for the `policyfoundry analyze` command.

Tests cover:
- Rich formatted output (default)
- JSON formatted output (--format json)
- Error handling for missing config / bad source
- Token cost display in output footer
- ReadOnlyAdapter safety enforcement
"""

from __future__ import annotations

import pytest


class TestAnalyzeRichOutput:
    """Tests for `policyfoundry analyze` with Rich (default) output format."""

    def test_analyze_rich_output_exits_zero(self, cli_runner):
        """analyze command with --format rich exits 0 on success."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_rich_output_contains_traffic_analysis(self, cli_runner):
        """Rich output includes traffic analysis section."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_rich_output_contains_rule_proposals(self, cli_runner):
        """Rich output includes rule proposals section."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_rich_output_contains_risk_table(self, cli_runner):
        """Rich output includes color-coded risk table."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_rich_output_contains_token_cost(self, cli_runner):
        """Rich output includes token usage and cost summary in footer."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")


class TestAnalyzeJsonOutput:
    """Tests for `policyfoundry analyze --format json` output."""

    def test_analyze_json_output_exits_zero(self, cli_runner):
        """analyze command with --format json exits 0 on success."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_json_output_is_valid_json(self, cli_runner):
        """JSON output is parseable as valid JSON."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_json_output_contains_pipeline_stages(self, cli_runner):
        """JSON output includes data from all pipeline stages."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_json_output_contains_token_usage(self, cli_runner):
        """JSON output includes token_usage field with counts and cost."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")


class TestAnalyzeErrorHandling:
    """Tests for analyze command error paths."""

    def test_analyze_config_error_shows_actionable_message(self, cli_runner):
        """ConfigError produces exit code 1 with Rich error panel, not a traceback."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_adapter_error_shows_actionable_message(self, cli_runner):
        """AdapterError produces exit code 1 with error_code and details."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_pipeline_error_shows_actionable_message(self, cli_runner):
        """PipelineError produces exit code 1 with stage context."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_analyze_unknown_error_shows_generic_message(self, cli_runner):
        """Unexpected exceptions produce exit code 1 with a generic error message."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")
