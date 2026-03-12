"""Tests for NormalizedFlowLog domain model."""

from typing import Any

import pytest
from pydantic import ValidationError

from policyfoundry.ingestion.schema import NormalizedFlowLog


class TestNormalizedFlowLogValid:
    """Tests for valid NormalizedFlowLog instantiation."""

    def test_valid_flow_log_creation(self, valid_flow_log_data: dict[str, Any]) -> None:
        """All 12 fields populated should succeed."""
        log = NormalizedFlowLog(**valid_flow_log_data)
        assert log.src_port == 52431
        assert log.dst_port == 443
        assert log.bytes_transferred == 1500
        assert log.packets_count == 10
        assert log.rule_id == "sgr-abc123"
        assert log.app_name == "web-server"

    def test_ipv4_and_ipv6_addresses(self, valid_flow_log_data: dict[str, Any]) -> None:
        """Both IPv4 and IPv6 addresses should be accepted."""
        data_v4 = {**valid_flow_log_data, "src_ip": "10.0.1.5", "dst_ip": "172.16.0.1"}
        log_v4 = NormalizedFlowLog(**data_v4)
        assert str(log_v4.src_ip) == "10.0.1.5"

        data_v6 = {**valid_flow_log_data, "src_ip": "::1", "dst_ip": "2001:db8::1"}
        log_v6 = NormalizedFlowLog(**data_v6)
        assert str(log_v6.dst_ip) == "2001:db8::1"

    def test_port_boundary_values(self, valid_flow_log_data: dict[str, Any]) -> None:
        """Port 0 and 65535 should be accepted; -1 and 65536 rejected."""
        data_zero = {**valid_flow_log_data, "src_port": 0, "dst_port": 0}
        log = NormalizedFlowLog(**data_zero)
        assert log.src_port == 0

        data_max = {**valid_flow_log_data, "src_port": 65535}
        NormalizedFlowLog(**data_max)

        with pytest.raises(ValidationError):
            NormalizedFlowLog(**{**valid_flow_log_data, "src_port": -1})

        with pytest.raises(ValidationError):
            NormalizedFlowLog(**{**valid_flow_log_data, "dst_port": 65536})

    def test_protocol_enum_values(self, valid_flow_log_data: dict[str, Any]) -> None:
        """TCP, UDP, ICMP are valid; UNKNOWN is rejected."""
        for proto in ("TCP", "UDP", "ICMP"):
            log = NormalizedFlowLog(**{**valid_flow_log_data, "protocol": proto})
            assert log.protocol.value == proto

        with pytest.raises(ValidationError):
            NormalizedFlowLog(**{**valid_flow_log_data, "protocol": "UNKNOWN"})

    def test_action_enum_values(self, valid_flow_log_data: dict[str, Any]) -> None:
        """ALLOW, DENY, DROP are valid; BLOCK is rejected."""
        for action in ("ALLOW", "DENY", "DROP"):
            log = NormalizedFlowLog(**{**valid_flow_log_data, "action": action})
            assert log.action.value == action

        with pytest.raises(ValidationError):
            NormalizedFlowLog(**{**valid_flow_log_data, "action": "BLOCK"})

    def test_flow_direction_enum(self, valid_flow_log_data: dict[str, Any]) -> None:
        """INBOUND and OUTBOUND are valid."""
        for direction in ("INBOUND", "OUTBOUND"):
            log = NormalizedFlowLog(**{**valid_flow_log_data, "flow_direction": direction})
            assert log.flow_direction.value == direction

    def test_default_values(self, valid_flow_log_data: dict[str, Any]) -> None:
        """Default values: bytes=0, packets=0, rule_id/app_name=None."""
        minimal = {k: v for k, v in valid_flow_log_data.items()
                   if k not in ("bytes_transferred", "packets_count", "rule_id", "app_name")}
        log = NormalizedFlowLog(**minimal)
        assert log.bytes_transferred == 0
        assert log.packets_count == 0
        assert log.rule_id is None
        assert log.app_name is None


class TestNormalizedFlowLogInvalid:
    """Tests for invalid NormalizedFlowLog data."""

    def test_negative_bytes_rejected(self, valid_flow_log_data: dict[str, Any]) -> None:
        """bytes_transferred=-1 should raise ValidationError."""
        valid_flow_log_data["bytes_transferred"] = -1
        with pytest.raises(ValidationError):
            NormalizedFlowLog(**valid_flow_log_data)

    def test_negative_packets_rejected(self, valid_flow_log_data: dict[str, Any]) -> None:
        """packets_count=-1 should raise ValidationError."""
        valid_flow_log_data["packets_count"] = -1
        with pytest.raises(ValidationError):
            NormalizedFlowLog(**valid_flow_log_data)

    def test_missing_required_fields(self, valid_flow_log_data: dict[str, Any]) -> None:
        """Omitting required fields should raise ValidationError."""
        required_fields = (
            "timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
            "protocol", "action", "flow_direction",
        )
        for field in required_fields:
            data = {k: v for k, v in valid_flow_log_data.items() if k != field}
            with pytest.raises(ValidationError):
                NormalizedFlowLog(**data)

    def test_invalid_ip_rejected(self, valid_flow_log_data: dict[str, Any]) -> None:
        """Invalid IP address strings should raise ValidationError."""
        valid_flow_log_data["src_ip"] = "not-an-ip"
        with pytest.raises(ValidationError):
            NormalizedFlowLog(**valid_flow_log_data)
