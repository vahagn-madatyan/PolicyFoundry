"""Shared fixtures for storage layer tests."""

from datetime import UTC, datetime
from ipaddress import IPv4Address
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.ingestion.schema import (
    ActionEnum,
    FlowDirection,
    NormalizedFlowLog,
    ProtocolEnum,
)


@pytest.fixture
def sample_records() -> list[NormalizedFlowLog]:
    """Five sample flow log records with mixed protocols, actions, and IPs."""
    return [
        NormalizedFlowLog(
            timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            src_ip=IPv4Address("10.0.0.1"),
            dst_ip=IPv4Address("172.16.0.1"),
            src_port=12345,
            dst_port=443,
            protocol=ProtocolEnum.TCP,
            action=ActionEnum.ALLOW,
            bytes_transferred=1500,
            rule_id="sgr-abc123",
            app_name="web-server",
            flow_direction=FlowDirection.INBOUND,
            packets_count=10,
        ),
        NormalizedFlowLog(
            timestamp=datetime(2025, 1, 15, 10, 1, 0, tzinfo=UTC),
            src_ip=IPv4Address("10.0.0.2"),
            dst_ip=IPv4Address("172.16.0.2"),
            src_port=54321,
            dst_port=80,
            protocol=ProtocolEnum.TCP,
            action=ActionEnum.ALLOW,
            bytes_transferred=2500,
            rule_id="sgr-abc123",
            app_name=None,
            flow_direction=FlowDirection.INBOUND,
            packets_count=20,
        ),
        NormalizedFlowLog(
            timestamp=datetime(2025, 1, 15, 10, 2, 0, tzinfo=UTC),
            src_ip=IPv4Address("10.0.0.3"),
            dst_ip=IPv4Address("172.16.0.3"),
            src_port=11111,
            dst_port=53,
            protocol=ProtocolEnum.UDP,
            action=ActionEnum.ALLOW,
            bytes_transferred=500,
            rule_id=None,
            app_name=None,
            flow_direction=FlowDirection.OUTBOUND,
            packets_count=5,
        ),
        NormalizedFlowLog(
            timestamp=datetime(2025, 1, 15, 10, 3, 0, tzinfo=UTC),
            src_ip=IPv4Address("192.168.1.1"),
            dst_ip=IPv4Address("10.0.0.1"),
            src_port=22222,
            dst_port=22,
            protocol=ProtocolEnum.TCP,
            action=ActionEnum.DENY,
            bytes_transferred=0,
            rule_id="sgr-deny-all",
            app_name=None,
            flow_direction=FlowDirection.INBOUND,
            packets_count=1,
        ),
        NormalizedFlowLog(
            timestamp=datetime(2025, 1, 15, 10, 4, 0, tzinfo=UTC),
            src_ip=IPv4Address("10.0.0.1"),
            dst_ip=IPv4Address("8.8.8.8"),
            src_port=33333,
            dst_port=0,
            protocol=ProtocolEnum.ICMP,
            action=ActionEnum.ALLOW,
            bytes_transferred=64,
            rule_id=None,
            app_name="ping",
            flow_direction=FlowDirection.OUTBOUND,
            packets_count=1,
        ),
    ]


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Temporary data directory for Parquet files."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def pre_written_parquet(
    data_dir: Path,
    sample_records: list[NormalizedFlowLog],
) -> Path:
    """Write sample records to a Parquet file using PyArrow directly.

    Returns the data directory containing the Parquet file.
    """
    from policyfoundry.storage.parquet_schema import FLOW_LOG_SCHEMA

    columns = {field.name: [] for field in FLOW_LOG_SCHEMA}

    for record in sample_records:
        columns["timestamp"].append(record.timestamp)
        columns["src_ip"].append(str(record.src_ip))
        columns["dst_ip"].append(str(record.dst_ip))
        columns["src_port"].append(record.src_port)
        columns["dst_port"].append(record.dst_port)
        columns["protocol"].append(record.protocol.value)
        columns["action"].append(record.action.value)
        columns["bytes_transferred"].append(record.bytes_transferred)
        columns["rule_id"].append(record.rule_id)
        columns["app_name"].append(record.app_name)
        columns["flow_direction"].append(record.flow_direction.value)
        columns["packets_count"].append(record.packets_count)
        columns["dedup_hash"].append(compute_dedup_key(record))

    table = pa.table(columns, schema=FLOW_LOG_SCHEMA)
    file_path = data_dir / "20250115T100000000000_prewritten.parquet"
    pq.write_table(table, str(file_path), compression="zstd")
    return data_dir
