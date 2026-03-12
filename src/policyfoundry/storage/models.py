"""Pydantic v2 result models for storage layer operations."""

from pydantic import BaseModel


class WriteResult(BaseModel):
    """Result of a Parquet write operation."""

    records_written: int
    cross_run_duplicates_removed: int
    file_path: str | None


class TopTalkerResult(BaseModel):
    """A top talker entry: source IP ranked by bytes transferred."""

    src_ip: str
    total_bytes: int
    flow_count: int


class DeniedFlowResult(BaseModel):
    """A denied flow entry with source, destination, and protocol details."""

    src_ip: str
    dst_ip: str
    dst_port: int
    protocol: str
    deny_count: int


class TrafficByProtocolResult(BaseModel):
    """Traffic breakdown by protocol."""

    protocol: str
    total_bytes: int
    flow_count: int
    percentage: float


class TrafficSummary(BaseModel):
    """Overall traffic summary statistics."""

    total_records: int
    total_bytes: int
    unique_sources: int
    unique_destinations: int
    allowed_count: int
    denied_count: int
    date_range_start: str | None = None
    date_range_end: str | None = None
