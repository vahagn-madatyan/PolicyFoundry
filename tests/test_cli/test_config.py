"""CLI integration tests for the `policyfoundry config` command.

Tests cover:
- Display of resolved configuration
- Sensitive value redaction
- Rich and JSON output formats
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from policyfoundry.config.models import PolicyFoundryConfig
from policyfoundry.main import app


def _mock_config(**overrides):
    """Create a PolicyFoundryConfig with test defaults."""
    return PolicyFoundryConfig(**overrides)


class TestConfigDisplay:
    """Tests for `policyfoundry config` command."""

    def test_config_exits_zero(self, cli_runner):
        """config command exits 0 on success."""
        with patch("policyfoundry.main.load_config", return_value=_mock_config()):
            result = cli_runner.invoke(app, ["config"])
            assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"

    def test_config_shows_resolved_settings(self, cli_runner):
        """Output includes resolved LLM, sources, targets, and output settings."""
        with patch("policyfoundry.main.load_config", return_value=_mock_config()):
            result = cli_runner.invoke(app, ["config"])
            assert "llm" in result.output
            assert "sources" in result.output
            assert "targets" in result.output
            assert "output" in result.output

    def test_config_redacts_sensitive_values(self, cli_runner):
        """API keys and credentials are redacted in output."""
        cfg = _mock_config(llm={"api_key": "sk-test-secret-key-12345"})
        with patch("policyfoundry.main.load_config", return_value=cfg):
            result = cli_runner.invoke(app, ["config"])
            # The full key should NOT appear in output
            assert "sk-test-secret-key-12345" not in result.output
            # But a redacted version should
            assert "sk-t" in result.output
            assert "****" in result.output or "***" in result.output

    def test_config_json_output_is_valid(self, cli_runner):
        """JSON output is parseable and contains config data."""
        with patch("policyfoundry.main.load_config", return_value=_mock_config()):
            result = cli_runner.invoke(app, ["config", "--format", "json"])
            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert "llm" in parsed
            assert "sources" in parsed


class TestHelpText:
    """Tests for CLI --help output."""

    def test_help_text_shows_all_commands(self, cli_runner):
        """--help lists analyze, rules, and config commands."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "analyze" in result.output
        assert "rules" in result.output
        assert "config" in result.output

    def test_analyze_help_shows_options(self, cli_runner):
        """analyze --help shows --source, --format, and --sg-ids options."""
        result = cli_runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--source" in result.output
        assert "--format" in result.output
        assert "--sg-ids" in result.output
