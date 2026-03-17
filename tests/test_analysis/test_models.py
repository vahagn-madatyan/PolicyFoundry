"""Tests for analysis domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from policyfoundry.analysis.models import (
    AggregatedFlow,
    DirectionLabel,
    DirectionResult,
    SubnetGroup,
)


# ---------------------------------------------------------------------------
# DirectionLabel
# ---------------------------------------------------------------------------

class TestDirectionLabel:
    """DirectionLabel StrEnum tests."""

    def test_has_inbound(self) -> None:
        assert DirectionLabel.INBOUND == "INBOUND"

    def test_has_outbound(self) -> None:
        assert DirectionLabel.OUTBOUND == "OUTBOUND"

    def test_has_unknown(self) -> None:
        assert DirectionLabel.UNKNOWN == "UNKNOWN"

    def test_all_values(self) -> None:
        assert set(DirectionLabel) == {"INBOUND", "OUTBOUND", "UNKNOWN"}

    def test_is_str(self) -> None:
        assert isinstance(DirectionLabel.INBOUND, str)


# ---------------------------------------------------------------------------
# DirectionResult
# ---------------------------------------------------------------------------

class TestDirectionResult:
    """DirectionResult validation tests."""

    def test_valid_construction(self) -> None:
        dr = DirectionResult(
            direction=DirectionLabel.OUTBOUND,
            src_ip="10.0.0.1",
            dst_ip="1.2.3.4",
            service_port=443,
            client_port=50000,
        )
        assert dr.direction == DirectionLabel.OUTBOUND
        assert dr.src_ip == "10.0.0.1"
        assert dr.dst_ip == "1.2.3.4"
        assert dr.service_port == 443
        assert dr.client_port == 50000

    def test_unknown_direction(self) -> None:
        dr = DirectionResult(
            direction=DirectionLabel.UNKNOWN,
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            service_port=12345,
            client_port=54321,
        )
        assert dr.direction == DirectionLabel.UNKNOWN

    def test_port_out_of_range_high(self) -> None:
        with pytest.raises(ValidationError, match="service_port"):
            DirectionResult(
                direction=DirectionLabel.OUTBOUND,
                src_ip="10.0.0.1",
                dst_ip="1.2.3.4",
                service_port=70000,
                client_port=50000,
            )

    def test_port_out_of_range_negative(self) -> None:
        with pytest.raises(ValidationError, match="client_port"):
            DirectionResult(
                direction=DirectionLabel.OUTBOUND,
                src_ip="10.0.0.1",
                dst_ip="1.2.3.4",
                service_port=443,
                client_port=-1,
            )

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            DirectionResult(  # type: ignore[call-arg]
                direction=DirectionLabel.OUTBOUND,
                src_ip="10.0.0.1",
            )


# ---------------------------------------------------------------------------
# AggregatedFlow
# ---------------------------------------------------------------------------

class TestAggregatedFlow:
    """AggregatedFlow validation tests."""

    def test_valid_construction(self) -> None:
        af = AggregatedFlow(
            src_ip="10.0.0.1",
            dst_ip="1.2.3.4",
            service_port=443,
            protocol="TCP",
            direction=DirectionLabel.OUTBOUND,
            flow_count=150,
            src_interface="zoneA",
            dst_interface="inet",
            sample_src_ports=[50000, 50001, 50002],
        )
        assert af.flow_count == 150
        assert af.sample_src_ports == [50000, 50001, 50002]

    def test_flow_count_minimum(self) -> None:
        with pytest.raises(ValidationError, match="flow_count"):
            AggregatedFlow(
                src_ip="10.0.0.1",
                dst_ip="1.2.3.4",
                service_port=443,
                protocol="TCP",
                direction=DirectionLabel.OUTBOUND,
                flow_count=0,
                src_interface="zoneA",
                dst_interface="inet",
            )

    def test_default_sample_src_ports(self) -> None:
        af = AggregatedFlow(
            src_ip="10.0.0.1",
            dst_ip="1.2.3.4",
            service_port=443,
            protocol="TCP",
            direction=DirectionLabel.OUTBOUND,
            flow_count=1,
            src_interface="zoneA",
            dst_interface="inet",
        )
        assert af.sample_src_ports == []


# ---------------------------------------------------------------------------
# SubnetGroup
# ---------------------------------------------------------------------------

class TestSubnetGroup:
    """SubnetGroup validation tests."""

    def test_valid_construction(self) -> None:
        sg = SubnetGroup(
            cidr="10.195.231.0/24",
            member_ips=["10.195.231.1", "10.195.231.2"],
            member_count=2,
            shared_patterns=[{"dst_ip": "1.2.3.4", "service_port": 443, "protocol": "TCP"}],
        )
        assert sg.cidr == "10.195.231.0/24"
        assert sg.member_count == 2

    def test_member_count_minimum(self) -> None:
        with pytest.raises(ValidationError, match="member_count"):
            SubnetGroup(
                cidr="10.0.0.0/24",
                member_ips=["10.0.0.1"],
                member_count=1,
                shared_patterns=[],
            )

    def test_empty_shared_patterns_allowed(self) -> None:
        sg = SubnetGroup(
            cidr="10.0.0.0/24",
            member_ips=["10.0.0.1", "10.0.0.2"],
            member_count=2,
            shared_patterns=[],
        )
        assert sg.shared_patterns == []
