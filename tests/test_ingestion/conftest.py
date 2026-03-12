"""Shared test fixtures for ingestion tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def valid_vpc_v2_line() -> str:
    """Return a valid VPC Flow Log v2 line with all 14 fields."""
    return (
        "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
        "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK"
    )


@pytest.fixture
def header_line() -> str:
    """Return a VPC Flow Log header line."""
    return (
        "version account-id interface-id srcaddr dstaddr "
        "srcport dstport protocol packets bytes start end action log-status"
    )


@pytest.fixture
def nodata_line() -> str:
    """Return a VPC Flow Log NODATA line."""
    return (
        "2 123456789012 eni-abc123 - - - - - - - "
        "1418530010 1418530070 - NODATA"
    )


@pytest.fixture
def skipdata_line() -> str:
    """Return a VPC Flow Log SKIPDATA line."""
    return (
        "2 123456789012 eni-abc123 - - - - - - - "
        "1418530010 1418530070 - SKIPDATA"
    )


@pytest.fixture
def malformed_line() -> str:
    """Return a line that cannot be parsed as VPC Flow Log."""
    return "this is not a valid log line"


@pytest.fixture
def sample_vpc_log_content() -> str:
    """Return multi-line VPC Flow Log content.

    Includes header, valid, malformed, and NODATA lines.
    """
    return (
        "version account-id interface-id srcaddr dstaddr srcport dstport "
        "protocol packets bytes start end action log-status\n"
        "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
        "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
        "2 123456789012 eni-abc123 10.0.2.10 172.16.0.50 "
        "12345 80 6 15 800 1418530020 1418530080 ACCEPT OK\n"
        "2 123456789012 eni-abc123 10.0.3.20 10.0.4.30 "
        "0 0 1 5 400 1418530030 1418530090 ACCEPT OK\n"
        "this is a malformed line with too few fields\n"
        "2 123456789012 eni-abc123 - - - - - - - "
        "1418530010 1418530070 - NODATA\n"
    )


@pytest.fixture
def tmp_log_file(tmp_path: Path, sample_vpc_log_content: str) -> Path:
    """Write sample VPC log content to a temporary file and return its path."""
    log_file = tmp_path / "test-flow-log.log"
    log_file.write_text(sample_vpc_log_content)
    return log_file
