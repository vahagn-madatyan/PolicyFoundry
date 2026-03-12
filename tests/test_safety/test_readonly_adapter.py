"""Tests for ReadOnlyAdapter safety wrapper.

Verifies that ReadOnlyAdapter delegates read operations (get_rules, validate,
capabilities) to the wrapped adapter and raises SafetyError on any write
operation (apply_rule, apply_rules).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from policyfoundry.adapters.safety import ReadOnlyAdapter
from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.schema import AdapterCapabilities
from policyfoundry.exceptions import SafetyError


@pytest.fixture
def mock_adapter() -> AsyncMock:
    """Mock FirewallAdapter with read methods configured."""
    adapter = AsyncMock(spec=FirewallAdapter)
    adapter.get_rules = AsyncMock(return_value=[])
    adapter.validate = AsyncMock(return_value=AsyncMock(valid=True))
    adapter.capabilities = AsyncMock(
        return_value=AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
        )
    )
    return adapter


@pytest.fixture
def readonly_adapter(mock_adapter: AsyncMock) -> ReadOnlyAdapter:
    """ReadOnlyAdapter wrapping a mock FirewallAdapter."""
    return ReadOnlyAdapter(mock_adapter)


@pytest.fixture
def sample_rule() -> dict:
    """Sample rule for testing delegation."""
    return {"name": "test-rule", "action": "ALLOW"}


class TestReadOnlyDelegatesGetRules:
    """TestReadOnlyDelegatesGetRules"""

    async def test_readonly_delegates_get_rules(
        self, readonly_adapter: ReadOnlyAdapter, mock_adapter: AsyncMock,
    ) -> None:
        """get_rules() must forward to wrapped adapter and return its result."""
        result = await readonly_adapter.get_rules()
        mock_adapter.get_rules.assert_called_once()
        assert result == mock_adapter.get_rules.return_value


class TestReadOnlyDelegatesValidate:
    """TestReadOnlyDelegatesValidate"""

    async def test_readonly_delegates_validate(
        self, readonly_adapter: ReadOnlyAdapter, mock_adapter: AsyncMock, sample_rule: dict,
    ) -> None:
        """validate() must forward to wrapped adapter and return its result."""
        result = await readonly_adapter.validate(sample_rule)
        mock_adapter.validate.assert_called_once_with(sample_rule)
        assert result == mock_adapter.validate.return_value


class TestReadOnlyDelegatesCapabilities:
    """TestReadOnlyDelegatesCapabilities"""

    async def test_readonly_delegates_capabilities(
        self, readonly_adapter: ReadOnlyAdapter, mock_adapter: AsyncMock,
    ) -> None:
        """capabilities() must forward to wrapped adapter and return its result."""
        result = await readonly_adapter.capabilities()
        mock_adapter.capabilities.assert_called_once()
        assert result == mock_adapter.capabilities.return_value


class TestReadOnlyBlocksApplyRule:
    """TestReadOnlyBlocksApplyRule"""

    async def test_readonly_blocks_apply_rule(
        self, readonly_adapter: ReadOnlyAdapter, sample_rule: dict,
    ) -> None:
        """apply_rule() must raise SafetyError with SAFETY_WRITE_BLOCKED code."""
        with pytest.raises(SafetyError) as exc_info:
            await readonly_adapter.apply_rule(sample_rule)

        assert exc_info.value.error_code == "SAFETY_WRITE_BLOCKED"


class TestReadOnlyBlocksApplyRules:
    """TestReadOnlyBlocksApplyRules"""

    async def test_readonly_blocks_apply_rules(
        self, readonly_adapter: ReadOnlyAdapter, sample_rule: dict,
    ) -> None:
        """apply_rules() must raise SafetyError with SAFETY_WRITE_BLOCKED code."""
        with pytest.raises(SafetyError) as exc_info:
            await readonly_adapter.apply_rules([sample_rule])

        assert exc_info.value.error_code == "SAFETY_WRITE_BLOCKED"


class TestSafetyErrorStructuredDetails:
    """TestSafetyErrorStructuredDetails"""

    async def test_safety_error_has_structured_details(
        self, readonly_adapter: ReadOnlyAdapter, sample_rule: dict,
    ) -> None:
        """SafetyError must include the attempted method name in its details dict."""
        with pytest.raises(SafetyError) as exc_info:
            await readonly_adapter.apply_rule(sample_rule)

        assert "method" in exc_info.value.details
