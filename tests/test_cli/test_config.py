"""CLI integration tests for the `policyfoundry config` command.

Tests cover:
- Display of resolved configuration
- Sensitive value redaction
- Rich and JSON output formats
"""

from __future__ import annotations

import pytest


class TestConfigDisplay:
    """Tests for `policyfoundry config` command."""

    def test_config_exits_zero(self, cli_runner):
        """config command exits 0 on success."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_config_shows_resolved_settings(self, cli_runner):
        """Output includes resolved LLM, sources, targets, and output settings."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_config_redacts_sensitive_values(self, cli_runner):
        """API keys and credentials are redacted in output."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")

    def test_config_json_output_is_valid(self, cli_runner):
        """JSON output is parseable and contains config data."""
        pytest.fail("Not yet implemented — waiting for CLI module reconstruction (T10)")
