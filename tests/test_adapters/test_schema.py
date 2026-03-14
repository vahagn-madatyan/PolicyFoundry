"""Tests for enriched adapter schema models."""

from typing import Any

import pytest
from pydantic import ValidationError

from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    NetworkEndpoint,
    RuleAction,
    UniversalRule,
    ValidationIssue,
    ValidationResult,
)


class TestNetworkEndpoint:
    """Tests for NetworkEndpoint model."""

    def test_valid_cidr_endpoint(self, valid_network_endpoint_data: dict[str, Any]) -> None:
        """CIDR-based endpoint is valid."""
        ep = NetworkEndpoint(**valid_network_endpoint_data)
        assert ep.cidr == "10.0.0.0/8"
        assert ep.security_group_id is None
        assert ep.tag is None
        assert ep.is_any is False

    def test_valid_sg_endpoint(self, valid_sg_endpoint_data: dict[str, Any]) -> None:
        """Security-group-id-based endpoint is valid."""
        ep = NetworkEndpoint(**valid_sg_endpoint_data)
        assert ep.security_group_id == "sg-0123456789abcdef0"
        assert ep.cidr is None

    def test_valid_tag_endpoint(self) -> None:
        """Tag-based endpoint is valid."""
        ep = NetworkEndpoint(tag={"env": "production"})
        assert ep.tag == {"env": "production"}
        assert ep.cidr is None
        assert ep.security_group_id is None

    def test_is_any_true(self) -> None:
        """is_any=True endpoint is valid without other identifiers."""
        ep = NetworkEndpoint(is_any=True)
        assert ep.is_any is True
        assert ep.cidr is None

    def test_reject_all_none_and_not_any(self) -> None:
        """All None fields with is_any=False should raise ValidationError."""
        with pytest.raises(ValidationError):
            NetworkEndpoint()


class TestRuleActionEnum:
    """Tests for enriched RuleAction enum."""

    def test_all_four_values(self) -> None:
        """ALLOW, DENY, DROP, REJECT are all valid."""
        for action in ("ALLOW", "DENY", "DROP", "REJECT"):
            assert RuleAction(action).value == action

    def test_invalid_action(self) -> None:
        """Invalid action value raises ValueError."""
        with pytest.raises(ValueError):
            RuleAction("BLOCK")


class TestUniversalRuleEnriched:
    """Tests for enriched UniversalRule with NetworkEndpoint."""

    def test_source_destination_as_network_endpoints(self) -> None:
        """source and destination accept list[NetworkEndpoint]."""
        rule = UniversalRule(
            name="Test rule",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
            source=[{"cidr": "10.0.0.0/8"}],
            destination=[{"cidr": "192.168.1.0/24"}],
            port_range={"from_port": 443, "to_port": 443},
        )
        assert len(rule.source) == 1
        assert rule.source[0].cidr == "10.0.0.0/8"
        assert len(rule.destination) == 1

    def test_zone_field(self) -> None:
        """UniversalRule has optional zone field."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
            zone="dmz",
        )
        assert rule.zone == "dmz"

    def test_zone_default_none(self) -> None:
        """zone defaults to None."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
        )
        assert rule.zone is None

    def test_tags_field(self) -> None:
        """UniversalRule has tags dict field."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
            tags={"env": "prod"},
        )
        assert rule.tags == {"env": "prod"}

    def test_tags_default_empty(self) -> None:
        """tags defaults to empty dict."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
        )
        assert rule.tags == {}

    def test_no_risk_level_field(self) -> None:
        """risk_level is NOT on UniversalRule."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
        )
        assert not hasattr(rule, "risk_level")

    def test_no_ai_metadata_fields(self) -> None:
        """ai_confidence, justification, business_justification NOT on UniversalRule."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
        )
        assert not hasattr(rule, "ai_confidence")
        assert not hasattr(rule, "justification")
        assert not hasattr(rule, "business_justification")

    def test_source_destination_default_empty(self) -> None:
        """source and destination default to empty lists."""
        rule = UniversalRule(
            name="Test",
            description="Test",
            action="ALLOW",
            direction="INBOUND",
            protocol="TCP",
        )
        assert rule.source == []
        assert rule.destination == []


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_valid_issue(self, valid_validation_issue_data: dict[str, Any]) -> None:
        """ValidationIssue with code, message, field."""
        issue = ValidationIssue(**valid_validation_issue_data)
        assert issue.code == "INVALID_CIDR"
        assert issue.message == "CIDR notation is invalid"
        assert issue.field == "source"


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_result_empty_errors(self) -> None:
        """valid=True with empty error/warning lists."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self) -> None:
        """valid=False with populated errors list."""
        issue = ValidationIssue(code="RULE_LIMIT", message="Exceeds 60-rule limit", field="rules")
        result = ValidationResult(valid=False, errors=[issue])
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "RULE_LIMIT"
        assert result.warnings == []


class TestAdapterCapabilities:
    """Tests for AdapterCapabilities model."""

    def test_defaults(self) -> None:
        """Default values for adapter capabilities."""
        caps = AdapterCapabilities(name="test", vendor="test-vendor")
        assert caps.supports_deny_rules is True
        assert caps.max_rules_per_direction == 60
        assert caps.supports_l7_app_filtering is False
        assert caps.allows_all_outbound_default is True

    def test_custom_values(self) -> None:
        """Custom values override defaults."""
        caps = AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=120,
            supports_l7_app_filtering=True,
            allows_all_outbound_default=True,
        )
        assert caps.supports_deny_rules is False
        assert caps.max_rules_per_direction == 120
        assert caps.supports_l7_app_filtering is True
        assert caps.allows_all_outbound_default is True
        assert caps.name == "aws_sg"
        assert caps.vendor == "AWS"
