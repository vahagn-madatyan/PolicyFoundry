"""Flow aggregation: direction-aware grouping of raw traffic records.

Groups ``ExcelTrafficRecord`` rows by the normalized
(src_ip, dst_ip, service_port, protocol, direction) tuple, producing one
``AggregatedFlow`` per unique group with a flow count and sample metadata.
"""

from __future__ import annotations

from policyfoundry.analysis.direction import infer_direction
from policyfoundry.analysis.models import AggregatedFlow, DirectionLabel
from policyfoundry.ingestion.excel_schema import ExcelTrafficRecord

# Maximum number of sample client/source ports to keep per aggregated flow.
_MAX_SAMPLE_PORTS: int = 5

# Type alias for the grouping key.
type _FlowKey = tuple[str, str, int, str, DirectionLabel]


def aggregate_flows(records: list[ExcelTrafficRecord]) -> list[AggregatedFlow]:
    """Aggregate raw records into deduplicated flows.

    For each record:
    1. Run ``infer_direction()`` to get normalized src/dst/service_port.
    2. Group by ``(src_ip, dst_ip, service_port, protocol, direction)``.
    3. Produce one ``AggregatedFlow`` per group.

    Returns the list sorted by flow_count descending.
    """
    groups: dict[_FlowKey, _GroupAccumulator] = {}

    for record in records:
        dr = infer_direction(record)
        key: _FlowKey = (
            dr.src_ip,
            dr.dst_ip,
            dr.service_port,
            record.protocol,
            dr.direction,
        )

        if key not in groups:
            # Determine interface mapping based on direction result.
            # src_ip is the client → its interface is the source interface.
            if dr.src_ip == record.ip2:
                src_iface = record.interface2
                dst_iface = record.interface1
            else:
                src_iface = record.interface1
                dst_iface = record.interface2

            groups[key] = _GroupAccumulator(
                src_interface=src_iface,
                dst_interface=dst_iface,
            )

        acc = groups[key]
        acc.count += 1
        if len(acc.sample_ports) < _MAX_SAMPLE_PORTS:
            acc.sample_ports.append(dr.client_port)

    flows: list[AggregatedFlow] = []
    for (src_ip, dst_ip, service_port, protocol, direction), acc in groups.items():
        flows.append(
            AggregatedFlow(
                src_ip=src_ip,
                dst_ip=dst_ip,
                service_port=service_port,
                protocol=protocol,
                direction=direction,
                flow_count=acc.count,
                src_interface=acc.src_interface,
                dst_interface=acc.dst_interface,
                sample_src_ports=acc.sample_ports,
            )
        )

    flows.sort(key=lambda f: f.flow_count, reverse=True)
    return flows


class _GroupAccumulator:
    """Mutable accumulator for one flow group during aggregation."""

    __slots__ = ("count", "sample_ports", "src_interface", "dst_interface")

    def __init__(self, *, src_interface: str, dst_interface: str) -> None:
        self.count: int = 0
        self.sample_ports: list[int] = []
        self.src_interface: str = src_interface
        self.dst_interface: str = dst_interface
