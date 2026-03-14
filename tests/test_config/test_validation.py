"""Tests for unknown key detection with fuzzy match suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from policyfoundry.config.validation import warn_unknown_keys
from pathlib import Path


class TestUnknownKeyDetection:
    """Tests for warn_unknown_keys() function."""

    def test_unknown_key_suggestion(self, tmp_path: Path) -> None:
        """YAML with 'lm:' at root produces warning suggesting 'llm'."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("lm:\n  provider: ollama\n")

        warnings = warn_unknown_keys(yaml_file)
        assert len(warnings) == 1
        assert "lm" in warnings[0]
        assert "Did you mean 'llm'?" in warnings[0]

    def test_unknown_key_no_suggestion(self, tmp_path: Path) -> None:
        """YAML with 'zzzzz:' at root produces warning without suggestion."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("zzzzz: true\n")

        warnings = warn_unknown_keys(yaml_file)
        assert len(warnings) == 1
        assert "zzzzz" in warnings[0]
        assert "Ignoring" in warnings[0]
        assert "Did you mean" not in warnings[0]

    def test_unknown_nested_key(self, tmp_path: Path) -> None:
        """YAML with 'llm.providr:' produces warning suggesting 'provider'."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("llm:\n  providr: bedrock\n")

        warnings = warn_unknown_keys(yaml_file)
        assert len(warnings) == 1
        assert "providr" in warnings[0]
        assert "Did you mean 'provider'?" in warnings[0]

    def test_unknown_key_continues_loading(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """YAML with unknown key + valid llm.provider still loads config."""
        from policyfoundry.config.loader import load_config

        yaml_file = tmp_path / ".policyfoundry.yaml"
        yaml_file.write_text("lm:\n  provider: ollama\nllm:\n  provider: bedrock\n")

        monkeypatch.chdir(tmp_path)
        (tmp_path / "fakehome").mkdir()
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path / "fakehome"))

        config = load_config()
        assert config.llm.provider == "bedrock"

    def test_no_warnings_valid_yaml(self, tmp_path: Path) -> None:
        """YAML with only known keys produces no warnings."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "llm:\n"
            "  provider: ollama\n"
            "  model: llama3.2\n"
            "sources:\n"
            "  s3_bucket: test\n"
            "targets:\n"
            "  security_group_ids:\n"
            "    - sg-123\n"
            "output:\n"
            "  format: json\n"
        )

        warnings = warn_unknown_keys(yaml_file)
        assert warnings == []

    def test_missing_file_no_warnings(self, tmp_path: Path) -> None:
        """warn_unknown_keys on nonexistent path returns empty list."""
        warnings = warn_unknown_keys(tmp_path / "nonexistent.yaml")
        assert warnings == []

    def test_invalid_config_error_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid type (temperature: 'hot') raises ConfigValidationError."""
        from policyfoundry.config.loader import load_config
        from policyfoundry.exceptions import ConfigValidationError

        yaml_file = tmp_path / ".policyfoundry.yaml"
        yaml_file.write_text("llm:\n  temperature: hot\n")

        monkeypatch.chdir(tmp_path)
        (tmp_path / "fakehome").mkdir(exist_ok=True)
        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path / "fakehome"))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config()

        assert "temperature" in str(exc_info.value)
