"""Parquet file writer with cross-run deduplication and purge support.

Writes NormalizedFlowLog records to Parquet files with zstd compression,
embedding ingestion provenance metadata. Cross-run deduplication uses
DuckDB to query existing Parquet files for matching dedup hashes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.storage.models import WriteResult
from policyfoundry.storage.parquet_schema import FLOW_LOG_SCHEMA

if TYPE_CHECKING:
    from pathlib import Path

    from policyfoundry.ingestion.schema import NormalizedFlowLog


def _build_table(
    records_with_hashes: list[tuple[NormalizedFlowLog, str]],
) -> pa.Table:
    """Convert records to a column-oriented PyArrow Table.

    Args:
        records_with_hashes: List of (record, dedup_hash) tuples.

    Returns:
        A PyArrow Table matching FLOW_LOG_SCHEMA.
    """
    columns: dict[str, list] = {field.name: [] for field in FLOW_LOG_SCHEMA}

    for record, hash_val in records_with_hashes:
        columns["timestamp"].append(record.timestamp)
        columns["src_ip"].append(str(record.src_ip))
        columns["dst_ip"].append(str(record.dst_ip))
        columns["src_port"].append(record.src_port)
        columns["dst_port"].append(record.dst_port)
        columns["protocol"].append(record.protocol.value)
        columns["action"].append(record.action.value)
        columns["bytes_transferred"].append(record.bytes_transferred)
        columns["rule_id"].append(record.rule_id)
        columns["app_name"].append(record.app_name)
        columns["flow_direction"].append(record.flow_direction.value)
        columns["packets_count"].append(record.packets_count)
        columns["dedup_hash"].append(hash_val)

    return pa.table(columns, schema=FLOW_LOG_SCHEMA)


def _get_existing_hashes(data_dir: str, new_hashes: set[str]) -> set[str]:
    """Query existing Parquet files for dedup hashes matching new records.

    For large hash sets (>1000), uses a temporary table with JOIN.
    For smaller sets, uses an IN clause.

    Args:
        data_dir: Path to the data directory.
        new_hashes: Set of dedup hashes to check.

    Returns:
        Set of hashes that already exist in stored Parquet files.
    """
    import pathlib

    glob_pattern = f"{data_dir}/*.parquet"

    if not list(pathlib.Path(data_dir).glob("*.parquet")):
        return set()

    con = duckdb.connect()

    try:
        if len(new_hashes) > 1000:
            con.execute(
                "CREATE TEMPORARY TABLE new_hashes (hash VARCHAR)"
            )

            for h in new_hashes:
                con.execute(
                    "INSERT INTO new_hashes VALUES (?)", [h]
                )

            rows = con.execute(
                """
                SELECT DISTINCT p.dedup_hash
                FROM read_parquet(?) p
                INNER JOIN new_hashes n ON p.dedup_hash = n.hash
                """,
                [glob_pattern],
            ).fetchall()
        else:
            hash_list = ", ".join(f"'{h}'" for h in new_hashes)
            rows = con.execute(
                f"""
                SELECT DISTINCT dedup_hash
                FROM read_parquet(?)
                WHERE dedup_hash IN ({hash_list})
                """,
                [glob_pattern],
            ).fetchall()

        return {row[0] for row in rows}
    finally:
        con.close()


async def write_records(
    records: list[NormalizedFlowLog],
    data_dir: Path,
    source_files: list[str],
) -> WriteResult:
    """Write normalized records to a new Parquet file with cross-run dedup.

    Creates the data directory if it doesn't exist. Each record is
    hashed with compute_dedup_key, and existing hashes in previous
    Parquet files are excluded.

    Args:
        records: List of NormalizedFlowLog records to write.
        data_dir: Path to the data directory for Parquet files.
        source_files: List of source file names for provenance metadata.

    Returns:
        WriteResult with records_written count, duplicates removed,
        and output file path.
    """
    if not records:
        return WriteResult(
            records_written=0,
            cross_run_duplicates_removed=0,
            file_path=None,
        )

    data_dir.mkdir(parents=True, exist_ok=True)

    record_hashes = [(r, compute_dedup_key(r)) for r in records]

    new_hashes = {h for _, h in record_hashes}

    existing = await asyncio.to_thread(
        _get_existing_hashes, str(data_dir), new_hashes
    )

    cross_run_dupes = 0
    unique_records = []

    for record, hash_val in record_hashes:
        if hash_val in existing:
            cross_run_dupes += 1
        else:
            unique_records.append((record, hash_val))

    if not unique_records:
        return WriteResult(
            records_written=0,
            cross_run_duplicates_removed=cross_run_dupes,
            file_path=None,
        )

    table = _build_table(unique_records)

    now = datetime.now(tz=UTC)

    metadata = {
        b"policyfoundry_source_files": json.dumps(source_files).encode(),
        b"policyfoundry_ingestion_timestamp": now.isoformat().encode(),
        b"policyfoundry_record_count": str(len(unique_records)).encode(),
    }

    existing_metadata = table.schema.metadata or {}
    table = table.replace_schema_metadata(
        {**existing_metadata, **metadata}
    )

    source_hash = hashlib.sha256(
        "|".join(sorted(source_files)).encode()
    ).hexdigest()[:8]
    ts_str = now.strftime("%Y%m%dT%H%M%S%f")
    file_path = data_dir / f"{ts_str}_{source_hash}.parquet"

    await asyncio.to_thread(
        pq.write_table, table, str(file_path), compression="zstd"
    )

    return WriteResult(
        records_written=len(unique_records),
        cross_run_duplicates_removed=cross_run_dupes,
        file_path=str(file_path),
    )


async def purge_data(data_dir: Path) -> int:
    """Delete all Parquet files from the data directory.

    Args:
        data_dir: Directory containing Parquet files.

    Returns:
        Number of files deleted.
    """
    parquet_files = list(data_dir.glob("*.parquet"))
    for f in parquet_files:
        f.unlink()
    return len(parquet_files)
