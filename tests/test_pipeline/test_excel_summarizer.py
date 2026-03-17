"""Tests for excel_summarizer: pre-summarization of aggregated flow data."""

from __future__ import annotations

import json

import pytest

from policyfoundry.analysis.models import (
    AggregatedFlow,
    DirectionLabel,
    SubnetGroup,
)
from policyfoundry.pipeline.excel_summarizer import (
    format_flow_summary_message,
    summarize_flows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_flow(
    src_ip: str = "10.0.1.1",
    dst_ip: str = "172.16.0.1",
    service_port: int = 443,
    protocol: str = "tcp",
    direction: DirectionLabel = DirectionLabel.INBOUND,
    flow_count: int = 1,
    src_interface: str = "eth0",
    dst_interface: str = "eth1",
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


@pytest.fixture
def realistic_flows() -> list[AggregatedFlow]:
    """25 diverse flows simulating a small corporate network."""
    flows: list[AggregatedFlow] = []
    sources = [f"10.0.1.{i}" for i in range(1, 11)]
    destinations = [f"172.16.0.{i}" for i in range(1, 6)]
    ports = [22, 80, 443, 3306, 8080]
    directions = [DirectionLabel.INBOUND, DirectionLabel.OUTBOUND, DirectionLabel.UNKNOWN]

    idx = 0
    for src in sources[:5]:
        for dst in destinations[:5]:
            flows.append(
                _make_flow(
                    src_ip=src,
                    dst_ip=dst,
                    service_port=ports[idx % len(ports)],
                    direction=directions[idx % len(directions)],
                    flow_count=(idx + 1) * 10,
                )
            )
            idx += 1

    return flows


@pytest.fixture
def sample_subnet_groups() -> list[SubnetGroup]:
    """Two subnet group candidates."""
    return [
        SubnetGroup(
            cidr="10.0.1.0/24",
            member_ips=["10.0.1.1", "10.0.1.2", "10.0.1.3"],
            member_count=3,
            shared_patterns=[
                {"dst_ip": "172.16.0.1", "service_port": 443, "protocol": "tcp"},
            ],
        ),
        SubnetGroup(
            cidr="10.0.2.0/24",
            member_ips=["10.0.2.1", "10.0.2.2"],
            member_count=2,
            shared_patterns=[
                {"dst_ip": "172.16.0.2", "service_port": 80, "protocol": "tcp"},
            ],
        ),
    ]


@pytest.fixture
def large_flow_set() -> list[AggregatedFlow]:
    """~600 flows to test token budget constraint."""
    flows: list[AggregatedFlow] = []
    for i in range(600):
        flows.append(
            _make_flow(
                src_ip=f"10.0.{i // 256}.{i % 256}",
                dst_ip=f"172.16.{i // 256}.{(i + 50) % 256}",
                service_port=(i % 50) + 1,
                direction=[DirectionLabel.INBOUND, DirectionLabel.OUTBOUND, DirectionLabel.UNKNOWN][i % 3],
                flow_count=(i % 100) + 1,
            )
        )
    return flows


# ---------------------------------------------------------------------------
# summarize_flows tests
# ---------------------------------------------------------------------------


class TestSummarizeFlows:
    """Core summarization logic."""

    def test_total_flows(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        expected = sum(f.flow_count for f in realistic_flows)
        assert summary["total_flows"] == expected

    def test_unique_sources(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        expected = len({f.src_ip for f in realistic_flows})
        assert summary["unique_sources"] == expected

    def test_unique_destinations(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        expected = len({f.dst_ip for f in realistic_flows})
        assert summary["unique_destinations"] == expected

    def test_direction_breakdown_keys(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        breakdown = summary["direction_breakdown"]
        assert set(breakdown.keys()) == {"INBOUND", "OUTBOUND", "UNKNOWN"}

    def test_direction_breakdown_sums_to_total(
        self, realistic_flows: list[AggregatedFlow]
    ) -> None:
        summary = summarize_flows(realistic_flows, [])
        breakdown = summary["direction_breakdown"]
        assert sum(breakdown.values()) == summary["total_flows"]

    def test_top_talkers_ordering(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        talkers = summary["top_talkers"]
        counts = [t["flow_count"] for t in talkers]
        assert counts == sorted(counts, reverse=True)

    def test_top_talkers_max_20(self, large_flow_set: list[AggregatedFlow]) -> None:
        summary = summarize_flows(large_flow_set, [])
        assert len(summary["top_talkers"]) <= 20

    def test_port_distribution_ordering(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        ports = summary["port_distribution"]
        counts = [p["flow_count"] for p in ports]
        assert counts == sorted(counts, reverse=True)

    def test_port_distribution_max_20(self, large_flow_set: list[AggregatedFlow]) -> None:
        summary = summarize_flows(large_flow_set, [])
        assert len(summary["port_distribution"]) <= 20

    def test_subnet_candidates_included(
        self,
        realistic_flows: list[AggregatedFlow],
        sample_subnet_groups: list[SubnetGroup],
    ) -> None:
        summary = summarize_flows(realistic_flows, sample_subnet_groups)
        candidates = summary["subnet_candidates"]
        assert len(candidates) == 2
        assert candidates[0]["cidr"] == "10.0.1.0/24"
        assert candidates[0]["member_count"] == 3

    def test_subnet_candidates_contain_shared_patterns(
        self,
        realistic_flows: list[AggregatedFlow],
        sample_subnet_groups: list[SubnetGroup],
    ) -> None:
        summary = summarize_flows(realistic_flows, sample_subnet_groups)
        assert "shared_patterns" in summary["subnet_candidates"][0]


class TestEmptyInput:
    """Edge case: no flows."""

    def test_empty_flows_returns_zeros(self) -> None:
        summary = summarize_flows([], [])
        assert summary["total_flows"] == 0
        assert summary["unique_sources"] == 0
        assert summary["unique_destinations"] == 0
        assert summary["top_talkers"] == []
        assert summary["port_distribution"] == []
        assert summary["subnet_candidates"] == []

    def test_empty_flows_direction_breakdown_all_zero(self) -> None:
        summary = summarize_flows([], [])
        breakdown = summary["direction_breakdown"]
        assert all(v == 0 for v in breakdown.values())


class TestTokenBudget:
    """Output stays within the 3K token budget for 600-flow input."""

    def test_600_flow_summary_under_3k_tokens(
        self,
        large_flow_set: list[AggregatedFlow],
        sample_subnet_groups: list[SubnetGroup],
    ) -> None:
        summary = summarize_flows(large_flow_set, sample_subnet_groups)
        serialized = format_flow_summary_message(summary)
        # Rough token estimate: 1 token ≈ 4 chars
        estimated_tokens = len(serialized) / 4
        assert estimated_tokens < 3000, (
            f"Summary is ~{estimated_tokens:.0f} tokens, exceeds 3K budget"
        )


class TestFormatFlowSummaryMessage:
    """format_flow_summary_message serialization."""

    def test_returns_valid_json(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        message = format_flow_summary_message(summary)
        parsed = json.loads(message)
        assert parsed["total_flows"] == summary["total_flows"]

    def test_compact_format_no_spaces(self, realistic_flows: list[AggregatedFlow]) -> None:
        summary = summarize_flows(realistic_flows, [])
        message = format_flow_summary_message(summary)
        # compact separators: no spaces after : or ,
        assert ": " not in message
        assert ", " not in message
