"""S3-based VPC Flow Log ingestion with prefix scanning and gzip support.

Discovers all objects under an S3 prefix, reads each one, transparently
decompresses gzip-compressed files (.gz extension), and pipes lines through
the same parse/dedup pipeline used by local ingestion.

Uses boto3 with asyncio.to_thread for non-blocking S3 I/O, ensuring
compatibility with moto for testing while maintaining an async public API.
"""

from __future__ import annotations

import asyncio
import gzip
import logging
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError

from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.ingestion.parser import is_header_line, parse_vpc_flow_log_line
from policyfoundry.ingestion.result import IngestionResult

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

    from policyfoundry.ingestion.schema import NormalizedFlowLog

logger = logging.getLogger(__name__)


async def ingest_from_s3(
    bucket: str,
    prefix: str,
    *,
    aws_profile: str | None = None,
) -> IngestionResult:
    """Ingest VPC Flow Log files from an S3 bucket.

    Scans all objects under the given prefix, reads each one, transparently
    decompresses gzip files (.gz extension), and parses lines through the
    standard VPC Flow Log parser with deduplication.

    S3 access errors (bucket not found, permission denied) are handled
    gracefully -- a warning is added and processing continues with
    remaining objects.

    Args:
        bucket: S3 bucket name.
        prefix: S3 key prefix to scan for log objects.
        aws_profile: Optional AWS profile name for credential chain.

    Returns:
        IngestionResult with parsed records and ingestion statistics.
    """
    records: list[NormalizedFlowLog] = []
    total_lines = 0
    duplicates_removed = 0
    errors_skipped = 0
    source_files: list[str] = []
    warnings: list[str] = []
    seen_hashes: set[str] = set()

    try:
        session = boto3.Session(profile_name=aws_profile)
        client = session.client("s3")

        object_keys = await asyncio.to_thread(
            _list_object_keys, client, bucket, prefix, warnings
        )

        for key in object_keys:
            s3_uri = f"s3://{bucket}/{key}"
            try:
                data = await asyncio.to_thread(
                    _get_object_bytes, client, bucket, key
                )

                # Handle gzip-compressed files
                if key.endswith(".gz"):
                    try:
                        data = gzip.decompress(data)
                    except gzip.BadGzipFile:
                        warnings.append(
                            f"Bad gzip file: {s3_uri} -- skipped"
                        )
                        continue

                text = data.decode("utf-8")
                lines = text.splitlines()
                source_files.append(s3_uri)

                for line_number, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue

                    total_lines += 1

                    # Skip header lines
                    if is_header_line(stripped):
                        total_lines -= 1
                        continue

                    record = parse_vpc_flow_log_line(
                        stripped,
                        line_number=line_number,
                        file_path=s3_uri,
                    )

                    if record is None:
                        # Check if it's NODATA/SKIPDATA metadata
                        fields = stripped.split()

                        if len(fields) >= 14 and fields[13] in ("NODATA", "SKIPDATA"):
                            total_lines -= 1
                            continue

                        errors_skipped += 1
                        snippet = stripped[:80]
                        warnings.append(
                            f"Line {line_number} in {s3_uri}"
                            f": skipped malformed line: "
                            f"{snippet}"
                        )
                        continue

                    # Deduplication
                    dedup_key = compute_dedup_key(record)
                    if dedup_key in seen_hashes:
                        duplicates_removed += 1
                        continue
                    seen_hashes.add(dedup_key)
                    records.append(record)

            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code", "")
                warnings.append(
                    f"Error reading {s3_uri} ({error_code}): {exc} -- skipped"
                )
            except Exception as exc:
                warnings.append(
                    f"Error reading {s3_uri}: {exc} -- skipped"
                )

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        warnings.append(
            f"S3 access error for bucket '{bucket}' ({error_code}): {exc}"
        )
    except Exception as exc:
        warnings.append(
            f"S3 access error for bucket '{bucket}': {exc}"
        )

    return IngestionResult(
        records=records,
        total_lines=total_lines,
        duplicates_removed=duplicates_removed,
        errors_skipped=errors_skipped,
        source_files=source_files,
        warnings=warnings,
    )


def _list_object_keys(
    client: S3Client,
    bucket: str,
    prefix: str,
    warnings: list[str],
) -> list[str]:
    """List all object keys under a prefix using pagination.

    Args:
        client: boto3 S3 client.
        bucket: S3 bucket name.
        prefix: S3 key prefix.
        warnings: List to append warnings to.

    Returns:
        List of S3 object keys.
    """
    keys: list[str] = []
    try:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if key is None:
                    continue
                keys.append(key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        warnings.append(
            f"S3 access error listing '{bucket}/{prefix}' ({error_code}): {exc}"
        )

    return keys


def _get_object_bytes(
    client: S3Client,
    bucket: str,
    key: str,
) -> bytes:
    """Read an S3 object and return its bytes.

    Args:
        client: boto3 S3 client.
        bucket: S3 bucket name.
        key: S3 object key.

    Returns:
        Raw bytes of the S3 object.
    """
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
