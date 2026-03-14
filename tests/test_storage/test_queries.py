"""Tests for DuckDB analytics query functions."""

import os
from pathlib import Path

from policyfoundry.storage.models import (
    DeniedFlowResult,
    TopTalkerResult,
    TrafficByProtocolResult,
    TrafficSummary,
)
from policyfoundry.storage.queries import (
    denied_flows,
    top_talkers,
    traffic_by_protocol,
    traffic_summary,
)


class TestTopTalkers:
    """Tests for top_talkers query function."""

    async def test_returns_top_n_by_bytes(self, pre_written_parquet):
        results = await top_talkers(10, str(pre_written_parquet))
        assert len(results) > 0
        assert all(isinstance(r, TopTalkerResult) for r in results)

    async def test_correct_ranking_order(self, pre_written_parquet):
        results = await top_talkers(10, str(pre_written_parquet))
        bytes_values = [r.total_bytes for r in results]
        assert bytes_values == sorted(bytes_values, reverse=True)

    async def test_respects_n_limit(self, pre_written_parquet):
        results = await top_talkers(2, str(pre_written_parquet))
        assert len(results) <= 2

    async def test_correct_total_bytes(self, pre_written_parquet):
        results = await top_talkers(10, str(pre_written_parquet))
        # 10.0.0.1 has records with 1500 + 64 = 1564 bytes
        ip_001 = next((r for r in results if r.src_ip == "10.0.0.1"), None)
        assert ip_001 is not None
        assert ip_001.total_bytes == 1564


class TestDeniedFlows:
    """Tests for denied_flows query function."""

    async def test_only_deny_actions(self, pre_written_parquet):
        results = await denied_flows(str(pre_written_parquet))
        assert all(isinstance(r, DeniedFlowResult) for r in results)
        # Only 1 DENY record in sample data
        assert len(results) == 1

    async def test_correct_grouping(self, pre_written_parquet):
        results = await denied_flows(str(pre_written_parquet))
        assert len(results) > 0
        r = results[0]
        assert r.src_ip == "192.168.1.1"
        assert r.dst_ip == "10.0.0.1"
        assert r.dst_port == 22
        assert r.deny_count == 1


class TestTrafficByProtocol:
    """Tests for traffic_by_protocol query function."""

    async def test_returns_all_protocols(self, pre_written_parquet):
        results = await traffic_by_protocol(str(pre_written_parquet))
        protocols = {r.protocol for r in results}
        assert "TCP" in protocols
        assert "UDP" in protocols
        assert "ICMP" in protocols

    async def test_percentages_sum_to_100(self, pre_written_parquet):
        results = await traffic_by_protocol(str(pre_written_parquet))
        total = sum(r.percentage for r in results)
        assert abs(total - 100.0) < 0.01

    async def test_correct_per_protocol_bytes(self, pre_written_parquet):
        results = await traffic_by_protocol(str(pre_written_parquet))
        tcp = next(r for r in results if r.protocol == "TCP")
        # TCP records: 1500 + 2500 + 0 = 4000 bytes
        assert tcp.total_bytes == 4000


class TestTrafficSummary:
    """Tests for traffic_summary query function."""

    async def test_correct_totals(self, pre_written_parquet):
        result = await traffic_summary(str(pre_written_parquet))
        assert isinstance(result, TrafficSummary)
        assert result.total_records == 5
        assert result.total_bytes == 1500 + 2500 + 500 + 0 + 64

    async def test_unique_counts(self, pre_written_parquet):
        result = await traffic_summary(str(pre_written_parquet))
        # Unique source IPs: 10.0.0.1, 10.0.0.2, 10.0.0.3, 192.168.1.1 = 4
        assert result.unique_sources == 4
        # Unique dst IPs: 172.16.0.1, 172.16.0.2, 172.16.0.3, 10.0.0.1, 8.8.8.8 = 5
        assert result.unique_destinations == 5

    async def test_allowed_denied_counts(self, pre_written_parquet):
        result = await traffic_summary(str(pre_written_parquet))
        assert result.allowed_count == 4
        assert result.denied_count == 1

    async def test_date_range(self, pre_written_parquet):
        result = await traffic_summary(str(pre_written_parquet))
        assert result.date_range_start is not None
        assert result.date_range_end is not None


class TestEmptyDataDir:
    """Tests for queries on empty data directories."""

    async def test_top_talkers_empty(self, data_dir):
        results = await top_talkers(10, str(data_dir))
        assert results == []

    async def test_denied_flows_empty(self, data_dir):
        results = await denied_flows(str(data_dir))
        assert results == []

    async def test_traffic_by_protocol_empty(self, data_dir):
        results = await traffic_by_protocol(str(data_dir))
        assert results == []

    async def test_traffic_summary_empty(self, data_dir):
        result = await traffic_summary(str(data_dir))
        assert result.total_records == 0
        assert result.total_bytes == 0


class TestCorruptFiles:
    """Tests for corrupt Parquet file handling."""

    async def test_corrupt_file_top_talkers(self, data_dir):
        (data_dir / "corrupt.parquet").write_bytes(b"not a parquet file")
        results = await top_talkers(10, str(data_dir))
        assert results == []

    async def test_corrupt_file_denied_flows(self, data_dir):
        (data_dir / "corrupt.parquet").write_bytes(b"not a parquet file")
        results = await denied_flows(str(data_dir))
        assert results == []

    async def test_corrupt_file_traffic_by_protocol(self, data_dir):
        (data_dir / "corrupt.parquet").write_bytes(b"not a parquet file")
        results = await traffic_by_protocol(str(data_dir))
        assert results == []

    async def test_corrupt_file_traffic_summary(self, data_dir):
        (data_dir / "corrupt.parquet").write_bytes(b"not a parquet file")
        result = await traffic_summary(str(data_dir))
        assert result.total_records == 0
