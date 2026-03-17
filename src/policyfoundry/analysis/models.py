"""Analysis domain models: direction labels, aggregated flows, subnet groups.

These models define the S02 → S03 boundary contract. Direction inference
maps neutral ip1/ip2 records to src/dst flows; aggregation groups them;
subnet grouping identifies /24 candidates for the LLM to evaluate.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DirectionLabel(StrEnum):
    """Traffic direction labels including an UNKNOWN fallback.

    Extends the concept of ``adapters.schema.Direction`` (INBOUND/OUTBOUND)
    with an UNKNOWN variant for records where direction cannot be inferred
    (e.g., both ports are ephemeral and no interface signal resolves it).
    """

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    UNKNOWN = "UNKNOWN"


class DirectionResult(BaseModel):
    """Result of direction inference for a single traffic record.

    Maps the neutral ip1/ip2 naming to src (client) and dst (server),
    identifies the service port vs. ephemeral port, and labels direction.
    """

    direction: DirectionLabel
    src_ip: str
    dst_ip: str
    service_port: int = Field(ge=0, le=65535)
    client_port: int = Field(ge=0, le=65535)


class AggregatedFlow(BaseModel):
    """A deduplicated traffic flow after direction inference and grouping.

    Produced by ``aggregate_flows()``; one instance per unique
    (src_ip, dst_ip, service_port, protocol, direction) tuple.
    """

    src_ip: str
    dst_ip: str
    service_port: int = Field(ge=0, le=65535)
    protocol: str
    direction: DirectionLabel
    flow_count: int = Field(ge=1)
    src_interface: str
    dst_interface: str
    sample_src_ports: list[int] = Field(default_factory=list)


class SubnetGroup(BaseModel):
    """A /N subnet candidate where 2+ IPs share a network and traffic pattern.

    Produced by ``group_to_subnets()``; these are *candidates* for the LLM
    in S03 to evaluate — not final CIDR rules.
    """

    cidr: str
    member_ips: list[str]
    member_count: int = Field(ge=2)
    shared_patterns: list[dict[str, str | int]]
