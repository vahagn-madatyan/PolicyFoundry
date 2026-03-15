"""Tests for subnet grouping — /24 candidates, min 2 IPs, pattern matching."""

from __future__ import annotations

from policyfoundry.analysis.models import AggregatedFlow, DirectionLabel, SubnetGroup
from policyfoundry.analysis.subnet import group_to_subnets


def _flow(
    *,
    src_ip: str = "10.0.0.1",
    dst_ip: str = "1.2.3.4",
    service_port: int = 443,
    protocol: str = "TCP",
    direction: DirectionLabel = DirectionLabel.OUTBOUND,
    flow_count: int = 1,
    src_interface: str = "zoneA",
    dst_interface: str = "inet",
) -> AggregatedFlow:
    return AggregatedFlow(
        src_ip=src_ip,
        dst_ip=dst_ip,
        service_port=service_port,
        protocol=protocol,
        direction=direction,
        flow_count=flow_count,
        src_interface=src_interface,
        dst_interface=dst_interface,
    )


# ---------------------------------------------------------------------------
# Basic /24 grouping — source side
# ---------------------------------------------------------------------------

class TestSourceSideGrouping:
    """IPs in the same /24 sharing a traffic pattern → SubnetGroup."""

    def test_two_ips_same_subnet_same_pattern(self) -> None:
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.0.2", dst_ip="1.2.3.4", service_port=443),
        ]
        groups = group_to_subnets(flows)
        src_groups = [g for g in groups if "10.0.0." in g.cidr]
        assert len(src_groups) >= 1
        sg = src_groups[0]
        assert sg.cidr == "10.0.0.0/24"
        assert set(sg.member_ips) == {"10.0.0.1", "10.0.0.2"}
        assert sg.member_count == 2

    def test_three_ips_same_subnet(self) -> None:
        flows = [
            _flow(src_ip=f"10.195.231.{i}", dst_ip="1.2.3.4", service_port=80)
            for i in range(1, 4)
        ]
        groups = group_to_subnets(flows)
        src_groups = [g for g in groups if g.cidr == "10.195.231.0/24"]
        assert len(src_groups) >= 1
        assert src_groups[0].member_count == 3

    def test_different_subnets_separate(self) -> None:
        """IPs in different /24s → separate groups (or no group if <2)."""
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.1.1", dst_ip="1.2.3.4", service_port=443),
        ]
        groups = group_to_subnets(flows)
        # Each /24 has only 1 IP → no group should be created
        src_groups = [g for g in groups if g.cidr in ("10.0.0.0/24", "10.0.1.0/24")]
        assert len(src_groups) == 0

    def test_different_patterns_separate_groups(self) -> None:
        """Same /24 IPs but different patterns → separate groups."""
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.0.2", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.0.1", dst_ip="5.6.7.8", service_port=80),
            _flow(src_ip="10.0.0.3", dst_ip="5.6.7.8", service_port=80),
        ]
        groups = group_to_subnets(flows)
        src_groups = [g for g in groups if g.cidr == "10.0.0.0/24"]
        # Should have groups for both patterns
        assert len(src_groups) >= 1
        # At least one group has the 443 pattern, one has the 80 pattern
        all_patterns = []
        for sg in src_groups:
            all_patterns.extend(sg.shared_patterns)
        ports_in_patterns = {p.get("service_port") for p in all_patterns}
        assert 443 in ports_in_patterns
        assert 80 in ports_in_patterns


# ---------------------------------------------------------------------------
# Destination-side grouping
# ---------------------------------------------------------------------------

class TestDestinationSideGrouping:
    """dst_ips in the same /24 receiving similar traffic → SubnetGroup."""

    def test_two_dst_ips_same_subnet(self) -> None:
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.10", service_port=443),
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.20", service_port=443),
        ]
        groups = group_to_subnets(flows)
        dst_groups = [g for g in groups if g.cidr == "1.2.3.0/24"]
        assert len(dst_groups) >= 1
        sg = dst_groups[0]
        assert set(sg.member_ips) == {"1.2.3.10", "1.2.3.20"}


# ---------------------------------------------------------------------------
# Minimum member threshold
# ---------------------------------------------------------------------------

class TestMinimumMembers:
    """Require ≥ 2 IPs per subnet to form a candidate."""

    def test_single_ip_no_group(self) -> None:
        flows = [_flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443)]
        groups = group_to_subnets(flows)
        # No group has only 1 member
        for g in groups:
            assert g.member_count >= 2

    def test_exactly_two_ips_creates_group(self) -> None:
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.0.2", dst_ip="1.2.3.4", service_port=443),
        ]
        groups = group_to_subnets(flows)
        assert any(g.member_count == 2 for g in groups)


# ---------------------------------------------------------------------------
# Shared patterns
# ---------------------------------------------------------------------------

class TestSharedPatterns:
    """SubnetGroup records the traffic patterns shared by member IPs."""

    def test_pattern_recorded(self) -> None:
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443, protocol="TCP"),
            _flow(src_ip="10.0.0.2", dst_ip="1.2.3.4", service_port=443, protocol="TCP"),
        ]
        groups = group_to_subnets(flows)
        src_groups = [g for g in groups if g.cidr == "10.0.0.0/24"]
        assert len(src_groups) >= 1
        patterns = src_groups[0].shared_patterns
        assert len(patterns) >= 1
        p = patterns[0]
        assert p["dst_ip"] == "1.2.3.4"
        assert p["service_port"] == 443
        assert p["protocol"] == "TCP"


# ---------------------------------------------------------------------------
# Custom prefix length
# ---------------------------------------------------------------------------

class TestCustomPrefixLength:
    """Prefix length is parameterizable."""

    def test_prefix_25(self) -> None:
        """With /25, 10.0.0.1 and 10.0.0.200 are in different subnets."""
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.0.200", dst_ip="1.2.3.4", service_port=443),
        ]
        groups = group_to_subnets(flows, prefix_len=25)
        # 10.0.0.1 → 10.0.0.0/25, 10.0.0.200 → 10.0.0.128/25
        src_groups = [g for g in groups if "10.0.0." in g.cidr]
        assert len(src_groups) == 0  # Each /25 has only 1 IP

    def test_prefix_16(self) -> None:
        """With /16, IPs from different /24s can group."""
        flows = [
            _flow(src_ip="10.0.0.1", dst_ip="1.2.3.4", service_port=443),
            _flow(src_ip="10.0.1.1", dst_ip="1.2.3.4", service_port=443),
        ]
        groups = group_to_subnets(flows, prefix_len=16)
        src_groups = [g for g in groups if g.cidr == "10.0.0.0/16"]
        assert len(src_groups) >= 1
        assert src_groups[0].member_count == 2


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    """Edge case: no flows."""

    def test_empty_list(self) -> None:
        groups = group_to_subnets([])
        assert groups == []


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------

class TestSortOrder:
    """Groups sorted by member_count descending."""

    def test_largest_group_first(self) -> None:
        flows = (
            [_flow(src_ip=f"10.0.0.{i}", dst_ip="1.2.3.4", service_port=443) for i in range(1, 6)]
            + [_flow(src_ip=f"10.0.1.{i}", dst_ip="1.2.3.4", service_port=443) for i in range(1, 3)]
        )
        groups = group_to_subnets(flows)
        src_groups = [g for g in groups if "10.0." in g.cidr]
        assert len(src_groups) >= 2
        assert src_groups[0].member_count >= src_groups[1].member_count
