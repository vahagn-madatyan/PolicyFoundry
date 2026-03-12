"""Tests for configuration loader with source priority chain.

Covers CONF-01: User can configure the tool via YAML file with environment
variable overrides, and the merge order is honored.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from policyfoundry.config.loader import load_config
from policyfoundry.exceptions import ConfigValidationError

import pytest


class TestDefaultConfig:
    """Tests for default config with no files or env vars."""

    def test_defaults_when_no_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_config() with no YAML files and no env vars returns all defaults."""
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))

        config = load_config()
        assert config.llm.provider == "ollama"
        assert config.llm.model == "llama3.2"
        assert config.llm.temperature == 0.1
        assert config.llm.max_tokens == 4096
        assert config.llm.base_url is None
        assert config.llm.api_key is None
        assert config.llm.timeout == 120
        assert config.sources.log_paths == []
        assert config.sources.s3_bucket is None
        assert config.targets.security_group_ids == []
        assert config.output.format == "rich"


class TestYAMLLoading:
    """Tests for YAML file loading."""

    def test_load_global_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_config() reads global ~/.policyfoundry/config.yaml."""
        config_dir = tmp_path / ".policyfoundry"
        config_dir.mkdir()
        yaml_file = config_dir / "config.yaml"
        yaml_file.write_text("llm:\n  provider: bedrock\n")

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))

        config = load_config()
        assert config.llm.provider == "bedrock"

    def test_load_local_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_config() reads local .policyfoundry.yaml in CWD."""
        yaml_file = tmp_path / ".policyfoundry.yaml"
        yaml_file.write_text("llm:\n  model: custom-model\n")

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: tmp_path))

        config = load_config()
        assert config.llm.model == "custom-model"

    def test_partial_yaml_preserves_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """YAML with only llm.provider does NOT wipe other LLM defaults."""
        config_dir = tmp_path / ".policyfoundry"
        config_dir.mkdir()
        yaml_file = config_dir / "config.yaml"
        yaml_file.write_text("llm:\n  provider: bedrock\n")

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))

        config = load_config()
        assert config.llm.provider == "bedrock"
        assert config.llm.temperature == 0.1
        assert config.llm.max_tokens == 4096
        assert config.llm.model == "llama3.2"


class TestEnvOverrides:
    """Tests for environment variable overrides."""

    def test_env_overrides_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var overrides YAML value."""
        config_dir = tmp_path / ".policyfoundry"
        config_dir.mkdir()
        yaml_file = config_dir / "config.yaml"
        yaml_file.write_text("llm:\n  provider: ollama\n")

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setenv("POLICYFOUNDRY_LLM__PROVIDER", "bedrock")

        config = load_config()
        assert config.llm.provider == "bedrock"

    def test_env_nested_delimiter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """POLICYFOUNDRY_LLM__MODEL env var sets config.llm.model."""
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setenv("POLICYFOUNDRY_LLM__MODEL", "custom-model")

        config = load_config()
        assert config.llm.model == "custom-model"

    def test_comma_separated_env_var_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Comma-separated env var parses into Python list."""
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setenv("POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS", "sg-abc,sg-def")

        config = load_config()
        assert config.targets.security_group_ids == ["sg-abc", "sg-def"]


class TestMergePriority:
    """Tests for merge priority order."""

    def test_merge_priority_order(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """global YAML < local YAML < env var for same field."""
        global_dir = tmp_path / "home" / ".policyfoundry"
        global_dir.mkdir(parents=True)
        (global_dir / "config.yaml").write_text("llm:\n  provider: ollama\n")

        (tmp_path / "project").mkdir()
        (tmp_path / "project" / ".policyfoundry.yaml").write_text("llm:\n  provider: bedrock\n")

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path / "home"))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: tmp_path / "project"))
        monkeypatch.setenv("POLICYFOUNDRY_LLM__PROVIDER", "openai")

        config = load_config()
        assert config.llm.provider == "openai"

    def test_init_kwargs_highest_priority(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Init kwargs override both YAML and env vars."""
        config_dir = tmp_path / ".policyfoundry"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("llm:\n  provider: ollama\n")

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setenv("POLICYFOUNDRY_LLM__PROVIDER", "bedrock")

        config = load_config(llm={"provider": "openai"})
        assert config.llm.provider == "openai"


class TestValidationErrors:
    """Tests for invalid config error handling."""

    def test_invalid_config_error_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid config raises ConfigValidationError with field info."""
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: Path("/nonexistent")))
        monkeypatch.setattr("pathlib.Path.cwd", staticmethod(lambda: Path("/nonexistent")))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(llm={"temperature": "not_a_number"})

        assert exc_info.value.error_code == "CONFIG_INVALID"
        assert "temperature" in str(exc_info.value)
