"""Traffic analysis: direction inference, flow aggregation, subnet grouping.

This package transforms raw ``ExcelTrafficRecord`` rows into normalized,
aggregated flows and subnet-group candidates for downstream policy generation.
"""

from policyfoundry.analysis.aggregator import aggregate_flows
from policyfoundry.analysis.direction import infer_direction
from policyfoundry.analysis.models import (
    AggregatedFlow,
    DirectionLabel,
    DirectionResult,
    SubnetGroup,
)
from policyfoundry.analysis.subnet import group_to_subnets

__all__ = [
    "AggregatedFlow",
    "DirectionLabel",
    "DirectionResult",
    "SubnetGroup",
    "aggregate_flows",
    "group_to_subnets",
    "infer_direction",
]
