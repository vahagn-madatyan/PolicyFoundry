"""Shared fixtures for CLI integration tests.

Provides:
- CliRunner instance for invoking Typer commands
- Mock LLM client factory (prevents real API calls)
- Mock adapter factory (prevents real AWS calls)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CLI test runner for invoking commands."""
    return CliRunner()


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mock LLM client that returns deterministic pipeline responses.

    Prevents real LiteLLM/Instructor API calls during CLI tests.
    Downstream tasks will wire this into the actual pipeline interface.
    """
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock()
    return client


@pytest.fixture
def mock_llm_client_factory(mock_llm_client: MagicMock):
    """Factory fixture that returns the mock LLM client.

    Use with monkeypatch to replace the real LLM client builder.
    """
    def _factory(*args, **kwargs):
        return mock_llm_client
    return _factory


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Mock adapter that returns deterministic security group data.

    Prevents real AWS API calls during CLI tests.
    Downstream tasks will wire this into the adapter registry.
    """
    adapter = MagicMock()
    adapter.list_rules.return_value = []
    adapter.apply_rules.side_effect = NotImplementedError(
        "ReadOnlyAdapter should block writes"
    )
    return adapter


@pytest.fixture
def mock_adapter_factory(mock_adapter: MagicMock):
    """Factory fixture that returns the mock adapter.

    Use with monkeypatch to replace the real adapter loader.
    """
    def _factory(*args, **kwargs):
        return mock_adapter
    return _factory
