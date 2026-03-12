"""Ingestion domain models: NormalizedFlowLog and related enums."""

from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, Field


class ProtocolEnum(StrEnum):
    """Supported network protocols."""

    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"


class ActionEnum(StrEnum):
    """Flow log action types."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    DROP = "DROP"


class FlowDirection(StrEnum):
    """Traffic flow direction."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class NormalizedFlowLog(BaseModel):
    """Unified schema for all traffic flow log sources. 12 fields."""

    timestamp: datetime
    src_ip: IPv4Address | IPv6Address
    dst_ip: IPv4Address | IPv6Address
    src_port: int = Field(ge=0, le=65535)
    dst_port: int = Field(ge=0, le=65535)
    protocol: ProtocolEnum
    action: ActionEnum
    bytes_transferred: int = Field(ge=0, default=0)
    rule_id: str | None = None
    app_name: str | None = None
    flow_direction: FlowDirection
    packets_count: int = Field(ge=0, default=0)
