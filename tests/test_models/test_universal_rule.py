"""Tests for UniversalRule domain model."""

from typing import Any

import pytest
from pydantic import ValidationError

from policyfoundry.adapters.schema import (
    Direction,
    PortRange,
    RuleAction,
    UniversalRule,
)


class TestUniversalRuleValid:
    """Tests for valid UniversalRule instantiation."""

    def test_valid_rule_creation(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """Instantiate with all fields populated."""
        rule = UniversalRule(**valid_universal_rule_data)
        assert rule.name == "Allow HTTPS inbound"
        assert rule.action == RuleAction.ALLOW
        assert rule.direction == Direction.INBOUND
        assert rule.protocol == "TCP"
        assert rule.priority == 100

    def test_rule_action_enum(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """ALLOW, DENY, DROP, REJECT are valid actions."""
        for action in ("ALLOW", "DENY", "DROP", "REJECT"):
            rule = UniversalRule(**{**valid_universal_rule_data, "action": action})
            assert rule.action.value == action

    def test_direction_enum(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """INBOUND and OUTBOUND are valid directions."""
        for direction in ("INBOUND", "OUTBOUND"):
            rule = UniversalRule(**{**valid_universal_rule_data, "direction": direction})
            assert rule.direction.value == direction

    def test_port_range_validation(self) -> None:
        """Valid port ranges, boundary values, and invalid ranges."""
        pr = PortRange(from_port=80, to_port=443)
        assert pr.from_port == 80
        assert pr.to_port == 443

        pr_boundary = PortRange(from_port=0, to_port=65535)
        assert pr_boundary.from_port == 0
        assert pr_boundary.to_port == 65535

        with pytest.raises(ValidationError):
            PortRange(from_port=-1, to_port=443)

        with pytest.raises(ValidationError):
            PortRange(from_port=80, to_port=65536)

    def test_optional_fields_defaults(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """id=None, port_range=None, priority=None, zone=None by default."""
        minimal = {k: v for k, v in valid_universal_rule_data.items()
                   if k not in ("id", "port_range", "priority")}
        rule = UniversalRule(**minimal)
        assert rule.id is None
        assert rule.port_range is None
        assert rule.priority is None
        assert rule.zone is None

    def test_source_destination_default_empty(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """source and destination default to empty lists."""
        minimal = {k: v for k, v in valid_universal_rule_data.items()
                   if k not in ("source", "destination")}
        rule = UniversalRule(**minimal)
        assert rule.source == []
        assert rule.destination == []


class TestUniversalRuleInvalid:
    """Tests for invalid UniversalRule data."""

    def test_invalid_action_rejected(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """Invalid action value should raise ValidationError."""
        valid_universal_rule_data["action"] = "BLOCK"
        with pytest.raises(ValidationError):
            UniversalRule(**valid_universal_rule_data)

    def test_invalid_direction_rejected(self, valid_universal_rule_data: dict[str, Any]) -> None:
        """Invalid direction value should raise ValidationError."""
        valid_universal_rule_data["direction"] = "BOTH"
        with pytest.raises(ValidationError):
            UniversalRule(**valid_universal_rule_data)

    def test_missing_required_fields(self) -> None:
        """Omitting required fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            UniversalRule()
