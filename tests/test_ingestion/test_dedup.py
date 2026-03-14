"""Tests for deduplication logic."""

from __future__ import annotations

from datetime import UTC, datetime

from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.ingestion.schema import (
    ActionEnum,
    FlowDirection,
    NormalizedFlowLog,
    ProtocolEnum,
)


def _make_record(
    *,
    src_ip: str = "10.0.1.5",
    dst_ip: str = "192.168.1.100",
    src_port: int = 52431,
    dst_port: int = 443,
    protocol: ProtocolEnum = ProtocolEnum.TCP,
    action: ActionEnum = ActionEnum.ALLOW,
    timestamp: datetime | None = None,
    bytes_transferred: int = 1500,
    packets_count: int = 20,
) -> NormalizedFlowLog:
    """Create a NormalizedFlowLog for testing."""
    if timestamp is None:
        timestamp = datetime.fromtimestamp(1418530010, tz=UTC)
    return NormalizedFlowLog(
        timestamp=timestamp,
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        protocol=protocol,
        action=action,
        bytes_transferred=bytes_transferred,
        rule_id=None,
        app_name=None,
        flow_direction=FlowDirection.INBOUND,
        packets_count=packets_count,
    )


class TestComputeDedupKey:
    """Tests for compute_dedup_key."""

    def test_consistent_hash_for_same_record(self):
        record = _make_record()
        key1 = compute_dedup_key(record)
        key2 = compute_dedup_key(record)
        assert key1 == key2

    def test_different_records_produce_different_hashes(self):
        record1 = _make_record(src_ip="10.0.1.5")
        record2 = _make_record(src_ip="10.0.1.6")
        assert compute_dedup_key(record1) != compute_dedup_key(record2)

    def test_same_hash_when_only_bytes_differ(self):
        record1 = _make_record(bytes_transferred=1500)
        record2 = _make_record(bytes_transferred=3000)
        assert compute_dedup_key(record1) == compute_dedup_key(record2)

    def test_same_hash_when_only_packets_differ(self):
        record1 = _make_record(packets_count=20)
        record2 = _make_record(packets_count=50)
        assert compute_dedup_key(record1) == compute_dedup_key(record2)

    def test_different_hash_for_different_src_port(self):
        record1 = _make_record(src_port=52431)
        record2 = _make_record(src_port=52432)
        assert compute_dedup_key(record1) != compute_dedup_key(record2)

    def test_different_hash_for_different_dst_port(self):
        record1 = _make_record(dst_port=443)
        record2 = _make_record(dst_port=80)
        assert compute_dedup_key(record1) != compute_dedup_key(record2)

    def test_different_hash_for_different_protocol(self):
        record1 = _make_record(protocol=ProtocolEnum.TCP)
        record2 = _make_record(protocol=ProtocolEnum.UDP)
        assert compute_dedup_key(record1) != compute_dedup_key(record2)

    def test_different_hash_for_different_action(self):
        record1 = _make_record(action=ActionEnum.ALLOW)
        record2 = _make_record(action=ActionEnum.DENY)
        assert compute_dedup_key(record1) != compute_dedup_key(record2)

    def test_different_hash_for_different_timestamp(self):
        record1 = _make_record(
            timestamp=datetime.fromtimestamp(1418530010, tz=UTC)
        )
        record2 = _make_record(
            timestamp=datetime.fromtimestamp(1418530020, tz=UTC)
        )
        assert compute_dedup_key(record1) != compute_dedup_key(record2)

    def test_hash_is_hex_string(self):
        record = _make_record()
        key = compute_dedup_key(record)
        assert isinstance(key, str)
        assert len(key) == 64
