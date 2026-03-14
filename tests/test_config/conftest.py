"""Shared test fixtures for configuration tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all POLICYFOUNDRY_ env vars to prevent pollution between tests."""
    for key in list(os.environ):
        if key.startswith("POLICYFOUNDRY_"):
            monkeypatch.delenv(key)


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temp directory structure mimicking ~/.policyfoundry/."""
    config_dir = tmp_path / ".policyfoundry"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_yaml_content() -> str:
    """Return a valid YAML string with all sections populated."""
    return (
        "llm:\n"
        "  provider: bedrock\n"
        "  model: claude-3\n"
        "  temperature: 0.2\n"
        "  max_tokens: 8192\n"
        "  base_url: https://api.example.com\n"
        "  api_key: test-key-123\n"
        "  timeout: 60\n"
        "\n"
        "sources:\n"
        "  log_paths:\n"
        "    - /var/log/vpc-flow/flow.log\n"
        "    - /tmp/logs/test.log\n"
        "  s3_bucket: my-vpc-logs\n"
        "  s3_prefix: flow-logs/\n"
        "  aws_profile: production\n"
        "\n"
        "targets:\n"
        "  security_group_ids:\n"
        "    - sg-abc123\n"
        "    - sg-def456\n"
        "\n"
        "output:\n"
        "  format: json\n"
    )


@pytest.fixture
def sample_yaml_dict() -> dict:
    """Return the dict equivalent of sample_yaml_content."""
    return {
        "llm": {
            "provider": "bedrock",
            "model": "claude-3",
            "temperature": 0.2,
            "max_tokens": 8192,
            "base_url": "https://api.example.com",
            "api_key": "test-key-123",
            "timeout": 60,
        },
        "sources": {
            "log_paths": ["/var/log/vpc-flow/flow.log", "/tmp/logs/test.log"],
            "s3_bucket": "my-vpc-logs",
            "s3_prefix": "flow-logs/",
            "aws_profile": "production",
        },
        "targets": {
            "security_group_ids": ["sg-abc123", "sg-def456"],
        },
        "output": {
            "format": "json",
        },
    }
