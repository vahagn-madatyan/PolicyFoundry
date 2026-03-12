"""Storage layer: Parquet persistence and DuckDB analytics queries.

Public API for writing normalized flow logs to Parquet files and
querying them with named analytics functions.
"""

from policyfoundry.storage.models import (
    DeniedFlowResult,
    TopTalkerResult,
    TrafficByProtocolResult,
    TrafficSummary,
    WriteResult,
)
from policyfoundry.storage.queries import (
    denied_flows,
    top_talkers,
    traffic_by_protocol,
    traffic_summary,
)
from policyfoundry.storage.writer import purge_data, write_records

__all__ = [
    "DeniedFlowResult",
    "TopTalkerResult",
    "TrafficByProtocolResult",
    "TrafficSummary",
    "WriteResult",
    "denied_flows",
    "purge_data",
    "top_talkers",
    "traffic_by_protocol",
    "traffic_summary",
    "write_records",
]
