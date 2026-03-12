"""Shared test fixtures for PolicyFoundry test suite."""

from datetime import UTC, datetime
from typing import Any

import pytest


@pytest.fixture
def valid_flow_log_data() -> dict[str, Any]:
    """Return a dict with all 12 valid NormalizedFlowLog fields."""
    return {
        "timestamp": datetime.now(tz=UTC),
        "src_ip": "10.0.1.5",
        "dst_ip": "192.168.1.100",
        "src_port": 52431,
        "dst_port": 443,
        "protocol": "TCP",
        "action": "ALLOW",
        "bytes_transferred": 1500,
        "rule_id": "sgr-abc123",
        "app_name": "web-server",
        "flow_direction": "INBOUND",
        "packets_count": 10,
    }


@pytest.fixture
def valid_universal_rule_data() -> dict[str, Any]:
    """Return a dict with valid UniversalRule fields."""
    return {
        "name": "Allow HTTPS inbound",
        "description": "Allow inbound HTTPS traffic from trusted CIDRs",
        "action": "ALLOW",
        "direction": "INBOUND",
        "protocol": "TCP",
        "source": [{"cidr": "10.0.0.0/8"}],
        "destination": [{"cidr": "192.168.1.0/24"}],
        "port_range": {"from_port": 443, "to_port": 443},
        "priority": 100,
    }
