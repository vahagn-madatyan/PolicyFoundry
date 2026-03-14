"""Deduplication logic for normalized flow log records.

Uses a 7-field composite key (excluding bytes_transferred and packets_count)
to identify duplicate records within an ingestion run.
"""

import hashlib

from policyfoundry.ingestion.schema import NormalizedFlowLog


def compute_dedup_key(record: NormalizedFlowLog) -> str:
    """Compute a SHA-256 hash key for deduplication.

    The key is based on 7 fields: src_ip, dst_ip, src_port, dst_port,
    protocol, timestamp, and action. Fields like bytes_transferred
    and packets_count are excluded so that records differing only
    in traffic volume are treated as duplicates.

    Args:
        record: The normalized flow log record.

    Returns:
        64-character hex string (SHA-256 digest).
    """
    key_parts = (
        str(record.src_ip),
        str(record.dst_ip),
        str(record.src_port),
        str(record.dst_port),
        record.protocol.value,
        record.timestamp.isoformat(),
        record.action.value,
    )
    composite = "|".join(key_parts)
    return hashlib.sha256(composite.encode()).hexdigest()
