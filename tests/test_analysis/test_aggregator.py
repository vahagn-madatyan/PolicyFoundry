"""Tests for flow aggregation — deduplication, counting, service port in key."""

from __future__ import annotations

import pytest

from policyfoundry.analysis.aggregator import aggregate_flows
from policyfoundry.analysis.models import DirectionLabel
from policyfoundry.ingestion.excel_schema import ExcelTrafficRecord


def _record(
    *,
    ip1: str = "1.2.3.4",
    port1: int = 443,
    interface1: str = "inet",
    hostname1: str = "server.example.com",
    ip2: str = "10.0.0.1",
    port2: int = 50000,
    interface2: str = "zoneA",
    hostname2: str = "client.internal",
    flag: str = "UIO",
    protocol: str = "TCP",
) -> ExcelTrafficRecord:
    return ExcelTrafficRecord(
        protocol=protocol,
        ip1=ip1,
        port1=port1,
        interface1=interface1,
        hostname1=hostname1,
        ip2=ip2,
        port2=port2,
        interface2=interface2,
        hostname2=hostname2,
        flag=flag,
    )


# ---------------------------------------------------------------------------
# Basic aggregation
# ---------------------------------------------------------------------------

class TestBasicAggregation:
    """Core aggregation behaviour."""

    def test_single_record(self) -> None:
        flows = aggregate_flows([_record()])
        assert len(flows) == 1
        f = flows[0]
        assert f.flow_count == 1
        assert f.service_port == 443
        assert f.direction == DirectionLabel.OUTBOUND
        # src_ip = client (ip2), dst_ip = server (ip1)
        assert f.src_ip == "10.0.0.1"
        assert f.dst_ip == "1.2.3.4"

    def test_same_tuple_aggregates(self) -> None:
        """Multiple records with same (src, dst, service_port, proto, dir) → one flow."""
        records = [
            _record(port2=50000),
            _record(port2=50001),
            _record(port2=50002),
        ]
        flows = aggregate_flows(records)
        assert len(flows) == 1
        assert flows[0].flow_count == 3

    def test_different_service_ports_separate(self) -> None:
        """Same src/dst but different service ports → separate flows."""
        records = [
            _record(port1=80, port2=50000),
            _record(port1=443, port2=50001),
        ]
        flows = aggregate_flows(records)
        assert len(flows) == 2
        ports = {f.service_port for f in flows}
        assert ports == {80, 443}

    def test_different_dst_ips_separate(self) -> None:
        records = [
            _record(ip1="1.2.3.4", port2=50000),
            _record(ip1="5.6.7.8", port2=50001),
        ]
        flows = aggregate_flows(records)
        assert len(flows) == 2

    def test_different_src_ips_separate(self) -> None:
        records = [
            _record(ip2="10.0.0.1", port2=50000),
            _record(ip2="10.0.0.2", port2=50001),
        ]
        flows = aggregate_flows(records)
        assert len(flows) == 2


# ---------------------------------------------------------------------------
# Ephemeral port exclusion
# ---------------------------------------------------------------------------

class TestEphemeralPortExclusion:
    """Ephemeral ports must NOT appear in aggregation key."""

    def test_different_ephemeral_ports_same_group(self) -> None:
        """Records differing only in ephemeral port → one aggregated flow."""
        records = [_record(port2=p) for p in range(40000, 40010)]
        flows = aggregate_flows(records)
        assert len(flows) == 1
        assert flows[0].flow_count == 10

    def test_sample_ports_collected(self) -> None:
        """Sample ephemeral ports are stored for reference, up to 5."""
        records = [_record(port2=40000 + i) for i in range(10)]
        flows = aggregate_flows(records)
        assert len(flows[0].sample_src_ports) == 5
        assert flows[0].sample_src_ports == list(range(40000, 40005))


# ---------------------------------------------------------------------------
# Direction-aware grouping
# ---------------------------------------------------------------------------

class TestDirectionAwareGrouping:
    """Direction is part of the grouping key."""

    def test_outbound_and_unknown_separate(self) -> None:
        """Same IPs but different direction → separate flows."""
        outbound_rec = _record(port1=443, port2=50000)
        # Both ephemeral, non-inet interface, no O flag → UNKNOWN
        unknown_rec = _record(
            port1=40000,
            port2=50000,
            interface1="dmz",
            interface2="internal",
            flag="U",
        )
        flows = aggregate_flows([outbound_rec, unknown_rec])
        directions = {f.direction for f in flows}
        assert DirectionLabel.OUTBOUND in directions
        assert DirectionLabel.UNKNOWN in directions


# ---------------------------------------------------------------------------
# Interface mapping
# ---------------------------------------------------------------------------

class TestInterfaceMapping:
    """src_interface and dst_interface are correctly mapped."""

    def test_outbound_interfaces(self) -> None:
        """For outbound: src is client (ip2/zoneA), dst is server (ip1/inet)."""
        flows = aggregate_flows([_record()])
        f = flows[0]
        assert f.src_interface == "zoneA"
        assert f.dst_interface == "inet"

    def test_inbound_interfaces(self) -> None:
        """For inbound: ip2 is server (inet side), ip1 is client."""
        rec = _record(
            port1=50000,
            port2=443,
            interface1="zoneA",
            interface2="inet",
        )
        flows = aggregate_flows([rec])
        f = flows[0]
        assert f.direction == DirectionLabel.INBOUND
        # src = client = ip1, dst = server = ip2
        assert f.src_interface == "zoneA"
        assert f.dst_interface == "inet"


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------

class TestSortOrder:
    """Flows are sorted by flow_count descending."""

    def test_highest_count_first(self) -> None:
        records = (
            [_record(ip1="1.1.1.1", port1=443, port2=50000 + i) for i in range(5)]
            + [_record(ip1="2.2.2.2", port1=80, port2=50000 + i) for i in range(10)]
        )
        flows = aggregate_flows(records)
        assert flows[0].flow_count == 10
        assert flows[1].flow_count == 5


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    """Edge case: no records."""

    def test_empty_list(self) -> None:
        flows = aggregate_flows([])
        assert flows == []
