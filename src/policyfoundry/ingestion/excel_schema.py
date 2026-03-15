"""Excel traffic record models: ExcelTrafficRecord, ColumnMapping, ExcelIngestionResult.

Defines the data contracts for Excel-based traffic ingestion. Uses neutral naming
(ip1/ip2, port1/port2) since direction inference is handled downstream.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


def _strip_whitespace(v: str) -> str:
    """Strip leading/trailing whitespace from a string value."""
    if isinstance(v, str):
        return v.strip()
    return v


# Pattern for DNS annotations like "10.194.184.42 (no DNS resolution)"
_DNS_ANNOTATION_RE = re.compile(r"^(.+?)\s*\(.*\)\s*$")


def _clean_dns_annotation(v: str) -> str:
    """Extract the hostname/IP from DNS annotation strings.

    Transforms "10.194.184.42 (no DNS resolution)" → "10.194.184.42"
    and "name42 (some note)" → "name42". Plain values pass through unchanged.
    """
    if isinstance(v, str):
        v = v.strip()
        match = _DNS_ANNOTATION_RE.match(v)
        if match:
            return match.group(1).strip()
    return v


class ExcelTrafficRecord(BaseModel):
    """Normalized record from an Excel traffic export.

    10 fields using neutral naming — direction inference is downstream (S02).
    All string fields are stripped of whitespace. hostname2 additionally has
    DNS annotations cleaned (e.g. "10.x.x.x (no DNS resolution)" → "10.x.x.x").
    """

    protocol: str
    ip1: str
    port1: int = Field(ge=0, le=65535)
    interface1: str
    hostname1: str
    ip2: str
    port2: int = Field(ge=0, le=65535)
    interface2: str
    hostname2: str
    flag: str

    @field_validator("protocol", "ip1", "interface1", "hostname1", "ip2", "interface2", "flag", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> object:
        """Strip leading/trailing whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("hostname2", mode="before")
    @classmethod
    def clean_hostname2(cls, v: object) -> object:
        """Strip whitespace and clean DNS annotations from hostname2.

        "10.194.184.42 (no DNS resolution)" → "10.194.184.42"
        """
        if isinstance(v, str):
            return _clean_dns_annotation(v)
        return v


class ColumnMapping(BaseModel):
    """Maps semantic field names to zero-based column indices in an Excel sheet.

    All 10 fields are required — auto-detection must find every column.
    """

    protocol: int
    ip1: int
    port1: int
    interface1: int
    hostname1: int
    ip2: int
    port2: int
    interface2: int
    hostname2: int
    flag: int

    @classmethod
    def from_headers(cls, headers: list[str]) -> ColumnMapping:
        """Create a ColumnMapping by auto-detecting columns from header names.

        Delegates to detect_columns() in column_detect module.
        """
        from policyfoundry.ingestion.column_detect import detect_columns

        return detect_columns(headers)


class ExcelIngestionResult(BaseModel):
    """Tracks the outcome of an Excel ingestion run.

    Follows the IngestionResult pattern: records list + stats + warnings.
    """

    records: list[ExcelTrafficRecord] = Field(default_factory=list)
    column_mapping: ColumnMapping | None = None
    total_rows: int = 0
    parsed_rows: int = 0
    skipped_rows: int = 0
    warnings: list[str] = Field(default_factory=list)
    source_file: str = ""
