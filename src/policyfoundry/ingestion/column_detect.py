"""Column auto-detection for Excel traffic exports.

Uses a synonym dictionary to map known header names to semantic fields.
Headers are normalized (lowercase, stripped, collapsed spaces) before matching.
"""

from __future__ import annotations

import re

from policyfoundry.exceptions import ExcelParseError
from policyfoundry.ingestion.excel_schema import ColumnMapping

# Ranked synonyms for each semantic field.
# First match wins — order by most specific/common first.
SYNONYM_MAP: dict[str, list[str]] = {
    "protocol": [
        "protocol",
        "proto",
        "ip protocol",
        "ip_protocol",
        "ipprotocol",
        "l4 protocol",
    ],
    "ip1": [
        "ip1",
        "source ip",
        "srcip",
        "src_ip",
        "source address",
        "srcaddr",
        "src_addr",
        "source_ip",
        "sourceip",
        "src ip",
        "sip",
    ],
    "port1": [
        "port1",
        "source port",
        "srcport",
        "src_port",
        "sport",
        "source_port",
        "sourceport",
        "src port",
    ],
    "interface1": [
        "interface1",
        "source interface",
        "src_interface",
        "srcintf",
        "source_interface",
        "ingress interface",
        "ingress_interface",
        "in_interface",
        "inintf",
    ],
    "hostname1": [
        "hostname1",
        "source hostname",
        "src_hostname",
        "source_hostname",
        "source host",
        "src_host",
        "source_host",
        "srchost",
    ],
    "ip2": [
        "ip2",
        "destination ip",
        "dstip",
        "dst_ip",
        "dest ip",
        "destination address",
        "dstaddr",
        "dst_addr",
        "destination_ip",
        "destinationip",
        "dest_ip",
        "dst ip",
        "dip",
    ],
    "port2": [
        "port2",
        "destination port",
        "dstport",
        "dst_port",
        "dport",
        "destination_port",
        "destinationport",
        "dest_port",
        "dest port",
        "dst port",
    ],
    "interface2": [
        "interface2",
        "destination interface",
        "dst_interface",
        "dstintf",
        "destination_interface",
        "egress interface",
        "egress_interface",
        "out_interface",
        "outintf",
    ],
    "hostname2": [
        "hostname2",
        "destination hostname",
        "dst_hostname",
        "destination_hostname",
        "destination host",
        "dst_host",
        "destination_host",
        "dsthost",
        "dest_hostname",
    ],
    "flag": [
        "flag",
        "flags",
        "tcp flags",
        "tcp_flags",
        "tcpflags",
        "connection flags",
    ],
}

# Pre-compute a flat lookup: normalized_synonym → (semantic_field, priority)
_SYNONYM_LOOKUP: dict[str, tuple[str, int]] = {}
for _field, _synonyms in SYNONYM_MAP.items():
    for _priority, _synonym in enumerate(_synonyms):
        _normalized = _synonym.lower().strip()
        if _normalized not in _SYNONYM_LOOKUP:
            _SYNONYM_LOOKUP[_normalized] = (_field, _priority)


def _normalize_header(header: str) -> str:
    """Normalize a header string for matching: lowercase, strip, collapse spaces."""
    h = header.lower().strip()
    h = re.sub(r"\s+", " ", h)
    return h


def detect_columns(headers: list[str]) -> ColumnMapping:
    """Auto-detect column mapping from Excel header names.

    Normalizes each header (lowercase, stripped, collapsed spaces), then matches
    against the SYNONYM_MAP. Each semantic field claims the first matching header;
    claimed headers cannot be reused.

    Args:
        headers: List of header strings from the Excel sheet's header row.

    Returns:
        ColumnMapping with zero-based column indices for all 10 semantic fields.

    Raises:
        ExcelParseError: If any semantic fields could not be matched to headers.
    """
    normalized = [_normalize_header(h) for h in headers]
    claimed_indices: set[int] = set()
    mapping: dict[str, int] = {}

    for field_name, synonyms in SYNONYM_MAP.items():
        for synonym in synonyms:
            norm_synonym = synonym.lower().strip()
            for idx, norm_header in enumerate(normalized):
                if idx in claimed_indices:
                    continue
                if norm_header == norm_synonym:
                    mapping[field_name] = idx
                    claimed_indices.add(idx)
                    break
            if field_name in mapping:
                break

    unmatched = [f for f in SYNONYM_MAP if f not in mapping]
    if unmatched:
        raise ExcelParseError(
            f"Could not auto-detect columns for: {', '.join(unmatched)}. "
            f"Available headers: {headers}. "
            f"Use ExcelConfig.column_mapping to specify column indices manually.",
            error_code="COLUMN_DETECT_FAILED",
            details={"unmatched_fields": unmatched, "available_headers": headers},
        )

    return ColumnMapping(**mapping)
