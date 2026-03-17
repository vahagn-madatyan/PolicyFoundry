"""Tests for AdapterRegistry plugin discovery."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.registry import AdapterRegistry
from policyfoundry.adapters.schema import AdapterCapabilities, UniversalRule, ValidationResult
from policyfoundry.exceptions import AdapterNotFoundError


class _FakeAdapter:
    """Concrete adapter for testing."""

    def get_rules(self) -> list[UniversalRule]:
        return []

    def validate(
        self, rule: UniversalRule, *, current_rule_count: int = 0, allow_wide_open: bool = False
    ) -> ValidationResult:
        return ValidationResult(valid=True)

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(name="fake", vendor="test")


def _make_entry_point(name: str, adapter_cls: type) -> MagicMock:
    """Create a mock entry point."""
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = adapter_cls
    return ep


class TestAdapterRegistry:
    """Tests for AdapterRegistry."""

    @pytest.fixture
    def mock_ep(self) -> MagicMock:
        with patch("policyfoundry.adapters.registry.entry_points") as mock_ep:
            yield mock_ep

    def test_list_adapters_returns_names(self, mock_ep: MagicMock) -> None:
        """list_adapters returns registered adapter names."""
        mock_ep.return_value = [_make_entry_point("fake", _FakeAdapter)]
        names = AdapterRegistry.list_adapters()
        assert "fake" in names

    def test_list_adapters_includes_aws_sg(self, mock_ep: MagicMock) -> None:
        """list_adapters always includes aws_sg."""
        mock_ep.return_value = []
        names = AdapterRegistry.list_adapters()
        assert "aws_sg" in names

    def test_get_adapter_found(self, mock_ep: MagicMock) -> None:
        """get_adapter loads and instantiates adapter from entry_points."""
        mock_ep.return_value = [_make_entry_point("fake", _FakeAdapter)]
        adapter = AdapterRegistry.get_adapter("fake")
        assert isinstance(adapter, _FakeAdapter)

    def test_get_adapter_not_found(self, mock_ep: MagicMock) -> None:
        """get_adapter raises AdapterNotFoundError for unknown names."""
        mock_ep.return_value = []
        with pytest.raises(AdapterNotFoundError):
            AdapterRegistry.get_adapter("nonexistent")

    def test_get_adapter_fallback_aws_sg(self, mock_ep: MagicMock) -> None:
        """get_adapter for aws_sg falls back to direct import when entry_points empty."""
        mock_ep.return_value = []
        adapter = AdapterRegistry.get_adapter("aws_sg", security_group_id="sg-test123")
        from policyfoundry.adapters.aws_sg import AwsSecurityGroupAdapter

        assert isinstance(adapter, AwsSecurityGroupAdapter)

    def test_get_adapter_passes_kwargs(self, mock_ep: MagicMock) -> None:
        """get_adapter passes kwargs to adapter constructor."""
        mock_cls = MagicMock(spec=FirewallAdapter, return_value=MagicMock())
        mock_ep.return_value = [_make_entry_point("fake", mock_cls)]
        AdapterRegistry.get_adapter("fake", sg_id="sg-123", region="us-east-1")
        mock_cls.assert_called_once_with(sg_id="sg-123", region="us-east-1")

    def test_get_adapter_logs_import_error(self, mock_ep: MagicMock) -> None:
        """get_adapter logs warning with exc_info when aws_sg import fails."""
        mock_ep.return_value = []

        with patch(
            "policyfoundry.adapters.registry.AdapterRegistry.get_adapter",
            wraps=AdapterRegistry.get_adapter,
        ):
            with patch(
                "policyfoundry.adapters.registry.logger"
            ) as mock_logger:
                # Make the aws_sg import raise ImportError
                import_target = (
                    "policyfoundry.adapters.aws_sg"
                )
                import builtins
                original_import = builtins.__import__

                def side_effect_import(name, *args, **kwargs):
                    if name == import_target:
                        raise ImportError("No module named 'policyfoundry.adapters.aws_sg'")
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=side_effect_import):
                    with pytest.raises(AdapterNotFoundError):
                        AdapterRegistry.get_adapter("aws_sg")

                mock_logger.warning.assert_called_once_with(
                    "Failed to import adapter module", exc_info=True
                )
