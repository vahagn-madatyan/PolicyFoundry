"""VPC Flow Log v2 line parser.

Parses individual lines from AWS VPC Flow Log files (default v2 format)
into NormalizedFlowLog records. Pure function -- never raises exceptions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from policyfoundry.ingestion.schema import (
    ActionEnum,
    FlowDirection,
    NormalizedFlowLog,
    ProtocolEnum,
)

logger = logging.getLogger(__name__)

_EXPECTED_FIELD_COUNT = 14

PROTOCOL_MAP: dict[int, ProtocolEnum] = {
    1: ProtocolEnum.ICMP,
    6: ProtocolEnum.TCP,
    17: ProtocolEnum.UDP,
}

ACTION_MAP: dict[str, ActionEnum] = {
    "ACCEPT": ActionEnum.ALLOW,
    "REJECT": ActionEnum.DENY,
}

_METADATA_STATUSES = frozenset({"NODATA", "SKIPDATA"})

_SENTINEL = "-"


def is_header_line(line: str) -> bool:
    """Check if a line is the VPC Flow Log header row."""
    return line.startswith("version ")


def is_metadata_line(fields: list[str]) -> bool:
    """Check if a parsed line is a metadata line (NODATA/SKIPDATA)."""
    return len(fields) >= _EXPECTED_FIELD_COUNT and fields[13] in _METADATA_STATUSES


def _parse_int_or_sentinel(value: str, default: int = 0) -> int:
    """Parse an integer field, treating sentinel '-' as the default value."""
    if value == _SENTINEL:
        return default
    return int(value)


def parse_vpc_flow_log_line(
    line: str,
    *,
    line_number: int,
    file_path: str,
) -> NormalizedFlowLog | None:
    """Parse a single VPC Flow Log v2 line into a NormalizedFlowLog.

    Returns None for header lines, metadata lines (NODATA/SKIPDATA),
    malformed lines, and lines with unsupported protocol numbers.
    Never raises exceptions.

    Args:
        line: Raw log line text.
        line_number: 1-based line number for error reporting.
        file_path: Source file path for error reporting.

    Returns:
        NormalizedFlowLog if successfully parsed, None otherwise.
    """
    try:
        stripped = line.strip()

        if not stripped:
            return None

        if is_header_line(stripped):
            return None

        fields = stripped.split()

        if len(fields) != _EXPECTED_FIELD_COUNT:
            logger.warning(
                "Line %d in %s: expected %d fields, got %d: %.80s",
                line_number,
                file_path,
                _EXPECTED_FIELD_COUNT,
                len(fields),
                stripped,
            )
            return None

        if is_metadata_line(fields):
            return None

        version = fields[0]

        if version != "2":
            logger.warning(
                "Line %d in %s: unexpected version '%s', attempting parse",
                line_number,
                file_path,
                version,
            )

        # fields[7] = protocol number
        protocol_num = int(fields[7]) if fields[7] != _SENTINEL else None

        if protocol_num is None or protocol_num not in PROTOCOL_MAP:
            logger.warning(
                "Line %d in %s: unsupported protocol number %s",
                line_number,
                file_path,
                fields[7],
            )
            return None

        protocol = PROTOCOL_MAP[protocol_num]

        # fields[12] = action
        action_str = fields[12]

        if action_str == _SENTINEL or action_str not in ACTION_MAP:
            logger.warning(
                "Line %d in %s: unknown action '%s'",
                line_number,
                file_path,
                action_str,
            )
            return None

        action = ACTION_MAP[action_str]

        src_port = _parse_int_or_sentinel(fields[5])
        dst_port = _parse_int_or_sentinel(fields[6])
        packets = _parse_int_or_sentinel(fields[8])
        bytes_transferred = _parse_int_or_sentinel(fields[9])

        # fields[10] = start epoch
        start_epoch = int(fields[10]) if fields[10] != _SENTINEL else 0
        timestamp = datetime.fromtimestamp(start_epoch, tz=UTC)

        # fields[3] = src_ip, fields[4] = dst_ip
        src_ip = fields[3]
        dst_ip = fields[4]

        return NormalizedFlowLog(
            timestamp=timestamp,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            action=action,
            bytes_transferred=bytes_transferred,
            rule_id=None,
            app_name=None,
            flow_direction=FlowDirection.INBOUND,
            packets_count=packets,
        )
    except Exception:
        logger.warning(
            "Line %d in %s: parse error: %.80s",
            line_number,
            file_path,
            line.strip(),
        )
        return None
