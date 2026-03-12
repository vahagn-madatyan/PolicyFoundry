"""Constraint validation tests for AwsSecurityGroupAdapter.validate().

Tests cover: DENY rejection, wide-open source rejection, rule limit,
invalid protocol, invalid port range, invalid CIDR, and multiple errors.
"""

import pytest

from policyfoundry.adapters.aws_sg.adapter import AwsSecurityGroupAdapter
from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RuleAction,
    UniversalRule,
)


def _make_rule(
    *,
    action: str = "ALLOW",
    direction: str = "INBOUND",
    protocol: str = "tcp",
    source_cidr: str = "10.0.0.0/8",
    source_sg_id: str | None = None,
    port_range: PortRange | None = None,
) -> UniversalRule:
    """Helper to build a UniversalRule for validation tests."""
    source: list[NetworkEndpoint] = []
    if source_cidr:
        source.append(NetworkEndpoint(cidr=source_cidr))
    if source_sg_id:
        source.append(NetworkEndpoint(security_group_id=source_sg_id))
    return UniversalRule(
        name="test-rule",
        description="test rule for validation",
        action=action,
        direction=direction,
        protocol=protocol,
        source=source,
        destination=[],
        port_range=port_range,
    )


@pytest.fixture
def adapter() -> AwsSecurityGroupAdapter:
    """Create adapter instance (not used for API calls, just validation)."""
    return AwsSecurityGroupAdapter("sg-test123", region="us-east-1")


class TestDenyRejection:
    """DENY/DROP/REJECT actions must be rejected (AWS SGs are allow-only)."""

    async def test_deny_action_produces_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(action=RuleAction.DENY)
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "DENY_NOT_SUPPORTED" for e in result.errors)
        assert any(e.field == "action" for e in result.errors)

    async def test_drop_action_produces_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(action=RuleAction.DROP)
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "DENY_NOT_SUPPORTED" for e in result.errors)

    async def test_reject_action_produces_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(action=RuleAction.REJECT)
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "DENY_NOT_SUPPORTED" for e in result.errors)

    async def test_allow_action_no_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(action=RuleAction.ALLOW)
        result = await adapter.validate(rule)
        assert result.valid
        assert len(result.errors) == 0


class TestWideOpenRejection:
    """0.0.0.0/0 and ::/0 sources must be rejected without allow_wide_open."""

    async def test_ipv4_any_without_flag(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="0.0.0.0/0")
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "OVERLY_PERMISSIVE_SOURCE" for e in result.errors)

    async def test_ipv6_any_without_flag(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="::/0")
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "OVERLY_PERMISSIVE_SOURCE" for e in result.errors)

    async def test_ipv4_any_with_flag(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="0.0.0.0/0")
        result = await adapter.validate(rule, allow_wide_open=True)
        assert result.valid

    async def test_specific_cidr_no_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="10.0.0.0/8")
        result = await adapter.validate(rule)
        assert result.valid


class TestRuleLimitExceeded:
    """Rule count at or above 60 must be rejected."""

    async def test_at_limit_produces_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule()
        result = await adapter.validate(rule, current_rule_count=60)
        assert not result.valid
        assert any(e.code == "RULE_LIMIT_EXCEEDED" for e in result.errors)

    async def test_below_limit_no_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule()
        result = await adapter.validate(rule, current_rule_count=59)
        assert result.valid

    async def test_zero_count_no_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule()
        result = await adapter.validate(rule, current_rule_count=0)
        assert result.valid


class TestFieldValidation:
    """Protocol, port range, and CIDR validation."""

    async def test_invalid_protocol_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(protocol="xyz")
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "INVALID_PROTOCOL" for e in result.errors)

    @pytest.mark.parametrize("proto", ["tcp", "udp", "icmp", "-1"])
    async def test_valid_protocols_no_error(self, adapter: AwsSecurityGroupAdapter, proto: str) -> None:
        rule = _make_rule(protocol=proto)
        result = await adapter.validate(rule)
        assert not any(e.code == "INVALID_PROTOCOL" for e in result.errors)

    async def test_port_range_from_greater_than_to(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(port_range=PortRange(from_port=8080, to_port=80))
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "INVALID_PORT_RANGE" for e in result.errors)

    async def test_invalid_cidr_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="not-a-cidr")
        result = await adapter.validate(rule)
        assert not result.valid
        assert any(e.code == "INVALID_CIDR" for e in result.errors)

    async def test_valid_ipv4_cidr_no_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="10.0.0.0/8")
        result = await adapter.validate(rule)
        assert not any(e.code == "INVALID_CIDR" for e in result.errors)

    async def test_valid_ipv6_cidr_no_error(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(source_cidr="2001:db8::/32")
        result = await adapter.validate(rule)
        assert not any(e.code == "INVALID_CIDR" for e in result.errors)


class TestMultipleErrors:
    """Rules with multiple violations should return all errors."""

    async def test_deny_and_wide_open(self, adapter: AwsSecurityGroupAdapter) -> None:
        rule = _make_rule(action=RuleAction.DENY, source_cidr="0.0.0.0/0")
        result = await adapter.validate(rule)
        assert not result.valid
        error_codes = {e.code for e in result.errors}
        assert "DENY_NOT_SUPPORTED" in error_codes
        assert "OVERLY_PERMISSIVE_SOURCE" in error_codes
