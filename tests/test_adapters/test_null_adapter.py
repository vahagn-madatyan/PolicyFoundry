"""Tests for NullAdapter: FirewallAdapter ABC contract compliance."""

import pytest

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.null import NullAdapter
from policyfoundry.adapters.registry import AdapterRegistry
from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    NetworkEndpoint,
    PortRange,
    RuleAction,
    UniversalRule,
    ValidationResult,
)


@pytest.fixture
def adapter() -> NullAdapter:
    """Return a NullAdapter instance."""
    return NullAdapter()


@pytest.fixture
def sample_rule() -> UniversalRule:
    """Return a realistic UniversalRule for validation tests."""
    return UniversalRule(
        name="allow-https",
        description="Allow HTTPS from internal network",
        action=RuleAction.ALLOW,
        direction="INBOUND",
        protocol="tcp",
        source=[NetworkEndpoint(cidr="10.0.0.0/8")],
        destination=[NetworkEndpoint(cidr="172.16.0.0/12")],
        port_range=PortRange(from_port=443, to_port=443),
    )


class TestNullAdapterABCContract:
    """NullAdapter is a proper FirewallAdapter subclass."""

    def test_is_firewall_adapter_subclass(self) -> None:
        assert issubclass(NullAdapter, FirewallAdapter)

    def test_instance_is_firewall_adapter(self, adapter: NullAdapter) -> None:
        assert isinstance(adapter, FirewallAdapter)


class TestGetRules:
    """get_rules() always returns an empty list."""

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, adapter: NullAdapter) -> None:
        rules = await adapter.get_rules()
        assert rules == []

    @pytest.mark.asyncio
    async def test_returns_list_type(self, adapter: NullAdapter) -> None:
        rules = await adapter.get_rules()
        assert isinstance(rules, list)

    @pytest.mark.asyncio
    async def test_idempotent(self, adapter: NullAdapter) -> None:
        first = await adapter.get_rules()
        second = await adapter.get_rules()
        assert first == second == []


class TestValidate:
    """validate() always returns valid for any rule."""

    @pytest.mark.asyncio
    async def test_returns_valid(
        self, adapter: NullAdapter, sample_rule: UniversalRule
    ) -> None:
        result = await adapter.validate(sample_rule)
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_returns_validation_result_type(
        self, adapter: NullAdapter, sample_rule: UniversalRule
    ) -> None:
        result = await adapter.validate(sample_rule)
        assert isinstance(result, ValidationResult)

    @pytest.mark.asyncio
    async def test_no_errors_or_warnings(
        self, adapter: NullAdapter, sample_rule: UniversalRule
    ) -> None:
        result = await adapter.validate(sample_rule)
        assert result.errors == []
        assert result.warnings == []

    @pytest.mark.asyncio
    async def test_valid_with_optional_params(
        self, adapter: NullAdapter, sample_rule: UniversalRule
    ) -> None:
        """Validate respects the full signature including optional kwargs."""
        result = await adapter.validate(
            sample_rule,
            current_rule_count=50,
            allow_wide_open=True,
        )
        assert result.valid is True


class TestCapabilities:
    """capabilities() returns expected shape."""

    def test_returns_adapter_capabilities(self, adapter: NullAdapter) -> None:
        caps = adapter.capabilities()
        assert isinstance(caps, AdapterCapabilities)

    def test_name_is_null(self, adapter: NullAdapter) -> None:
        caps = adapter.capabilities()
        assert caps.name == "null"

    def test_vendor_is_none(self, adapter: NullAdapter) -> None:
        caps = adapter.capabilities()
        assert caps.vendor == "none"

    def test_permissive_defaults(self, adapter: NullAdapter) -> None:
        caps = adapter.capabilities()
        assert caps.supports_deny_rules is True
        assert caps.max_rules_per_direction >= 100
        assert caps.allows_all_outbound_default is True


class TestRegistryIntegration:
    """NullAdapter is discoverable via AdapterRegistry."""

    def test_listed_in_registry(self) -> None:
        adapters = AdapterRegistry.list_adapters()
        assert "null" in adapters

    def test_loadable_from_registry(self) -> None:
        adapter = AdapterRegistry.get_adapter("null")
        assert isinstance(adapter, NullAdapter)
        assert isinstance(adapter, FirewallAdapter)
