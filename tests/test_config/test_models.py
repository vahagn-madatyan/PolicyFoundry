"""Tests for configuration Pydantic models.

Covers CONF-02: LLM provider, model, log sources, and target security groups
are configurable via typed Pydantic models with sensible defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from policyfoundry.config.models import (
    LLMConfig,
    OutputConfig,
    PolicyFoundryConfig,
    SourcesConfig,
    TargetsConfig,
)

import pytest


class TestLLMConfig:
    """LLM configuration model tests."""

    def test_llm_config_defaults(self) -> None:
        config = LLMConfig()
        assert config.provider == "ollama"
        assert config.model == "llama3.2"
        assert config.temperature == 0.1
        assert config.max_tokens == 4096
        assert config.base_url is None
        assert config.api_key is None
        assert config.timeout == 120

    def test_llm_config_custom(self) -> None:
        config = LLMConfig(provider="bedrock", model="claude-3")
        assert config.provider == "bedrock"
        assert config.model == "claude-3"
        assert config.temperature == 0.1
        assert config.max_tokens == 4096


class TestSourcesConfig:
    """Sources configuration model tests."""

    def test_sources_config_defaults(self) -> None:
        config = SourcesConfig()
        assert config.log_paths == []
        assert config.s3_bucket is None
        assert config.s3_prefix is None
        assert config.aws_profile is None

    def test_sources_config_log_paths(self) -> None:
        config = SourcesConfig(log_paths=["/var/log/vpc.log"])
        assert config.log_paths == ["/var/log/vpc.log"]


class TestTargetsConfig:
    """Targets configuration model tests."""

    def test_targets_config_defaults(self) -> None:
        config = TargetsConfig()
        assert config.security_group_ids == []

    def test_comma_separated_list(self) -> None:
        config = TargetsConfig(security_group_ids="sg-abc,sg-def")
        assert config.security_group_ids == ["sg-abc", "sg-def"]

    def test_comma_separated_list_with_spaces(self) -> None:
        config = TargetsConfig(security_group_ids="sg-abc, sg-def ")
        assert config.security_group_ids == ["sg-abc", "sg-def"]

    def test_comma_separated_list_passthrough(self) -> None:
        config = TargetsConfig(security_group_ids=["sg-abc"])
        assert config.security_group_ids == ["sg-abc"]


class TestOutputConfig:
    """Output configuration model tests."""

    def test_output_config_defaults(self) -> None:
        config = OutputConfig()
        assert config.format == "rich"


class TestPolicyFoundryConfig:
    """Root configuration model tests."""

    def test_root_config_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With no YAML files and no env vars, all nested defaults are produced."""
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: __import__("pathlib").Path("/nonexistent")))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: __import__("pathlib").Path("/nonexistent")))

        config = PolicyFoundryConfig()
        assert config.llm.provider == "ollama"
        assert config.llm.model == "llama3.2"
        assert config.sources.log_paths == []
        assert config.targets.security_group_ids == []
        assert config.output.format == "rich"

    def test_root_config_env_prefix(self) -> None:
        """PolicyFoundryConfig has correct env_prefix and env_nested_delimiter."""
        mc = PolicyFoundryConfig.model_config
        assert mc.get("env_prefix") == "POLICYFOUNDRY_"
        assert mc.get("env_nested_delimiter") == "__"

    def test_root_config_extra_ignore(self) -> None:
        """PolicyFoundryConfig ignores extra fields."""
        mc = PolicyFoundryConfig.model_config
        assert mc.get("extra") == "ignore"
