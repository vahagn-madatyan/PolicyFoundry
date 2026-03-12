"""Named DuckDB analytics functions for querying stored Parquet flow logs.

Each function opens a per-query DuckDB in-memory connection, runs the
analytics query against all Parquet files in the data directory, and
returns Pydantic result models. All I/O is wrapped with asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib

import duckdb

from policyfoundry.storage.models import (
    DeniedFlowResult,
    TopTalkerResult,
    TrafficByProtocolResult,
    TrafficSummary,
)

logger = logging.getLogger(__name__)


def _has_parquet_files(data_dir: str) -> bool:
    """Check whether the data directory contains any Parquet files."""
    return bool(list(pathlib.Path(data_dir).glob("*.parquet")))


async def top_talkers(n: int, data_dir: str) -> list[TopTalkerResult]:
    """Return top N source IPs by total bytes transferred.

    Args:
        n: Number of top talkers to return.
        data_dir: Path to the data directory containing Parquet files.

    Returns:
        List of TopTalkerResult ordered by total_bytes descending.
    """

    def _query() -> list[TopTalkerResult]:
        if not _has_parquet_files(data_dir):
            return []

        glob_pattern = f"{data_dir}/*.parquet"
        con = duckdb.connect()

        try:
            rows = con.execute(
                """
                SELECT
                    src_ip,
                    SUM(bytes_transferred) AS total_bytes,
                    COUNT(*) AS flow_count
                FROM read_parquet(?)
                GROUP BY src_ip
                ORDER BY total_bytes DESC
                LIMIT ?
                """,
                [glob_pattern, n],
            ).fetchall()

            return [
                TopTalkerResult(
                    src_ip=row[0],
                    total_bytes=row[1],
                    flow_count=row[2],
                )
                for row in rows
            ]
        except (duckdb.IOException, duckdb.InvalidInputException):
            logger.warning(
                "Failed to read Parquet files in %s, returning empty results",
                data_dir,
            )
            return []
        finally:
            con.close()

    return await asyncio.to_thread(_query)


async def denied_flows(data_dir: str) -> list[DeniedFlowResult]:
    """Return denied flow records grouped by src/dst/port/protocol.

    Args:
        data_dir: Path to the data directory containing Parquet files.

    Returns:
        List of DeniedFlowResult ordered by deny_count descending.
    """

    def _query() -> list[DeniedFlowResult]:
        if not _has_parquet_files(data_dir):
            return []

        glob_pattern = f"{data_dir}/*.parquet"
        con = duckdb.connect()

        try:
            rows = con.execute(
                """
                SELECT
                    src_ip,
                    dst_ip,
                    dst_port,
                    protocol,
                    COUNT(*) AS deny_count
                FROM read_parquet(?)
                WHERE action IN ('DENY', 'DROP')
                GROUP BY src_ip, dst_ip, dst_port, protocol
                ORDER BY deny_count DESC
                """,
                [glob_pattern],
            ).fetchall()

            return [
                DeniedFlowResult(
                    src_ip=row[0],
                    dst_ip=row[1],
                    dst_port=row[2],
                    protocol=row[3],
                    deny_count=row[4],
                )
                for row in rows
            ]
        except (duckdb.IOException, duckdb.InvalidInputException):
            logger.warning(
                "Failed to read Parquet files in %s, returning empty results",
                data_dir,
            )
            return []
        finally:
            con.close()

    return await asyncio.to_thread(_query)


async def traffic_by_protocol(
    data_dir: str,
) -> list[TrafficByProtocolResult]:
    """Return traffic breakdown by protocol with percentages.

    Args:
        data_dir: Path to the data directory containing Parquet files.

    Returns:
        List of TrafficByProtocolResult ordered by total_bytes descending.
    """

    def _query() -> list[TrafficByProtocolResult]:
        if not _has_parquet_files(data_dir):
            return []

        glob_pattern = f"{data_dir}/*.parquet"
        con = duckdb.connect()

        try:
            rows = con.execute(
                """
                SELECT
                    protocol,
                    SUM(bytes_transferred) AS total_bytes,
                    COUNT(*) AS flow_count,
                    (COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ())
                        AS percentage
                FROM read_parquet(?)
                GROUP BY protocol
                ORDER BY total_bytes DESC
                """,
                [glob_pattern],
            ).fetchall()

            return [
                TrafficByProtocolResult(
                    protocol=row[0],
                    total_bytes=row[1],
                    flow_count=row[2],
                    percentage=float(row[3]),
                )
                for row in rows
            ]
        except (duckdb.IOException, duckdb.InvalidInputException):
            logger.warning(
                "Failed to read Parquet files in %s, returning empty results",
                data_dir,
            )
            return []
        finally:
            con.close()

    return await asyncio.to_thread(_query)


async def traffic_summary(data_dir: str) -> TrafficSummary:
    """Return overall traffic summary statistics.

    Args:
        data_dir: Path to the data directory containing Parquet files.

    Returns:
        TrafficSummary with aggregate statistics.
    """
    empty = TrafficSummary(
        total_records=0,
        total_bytes=0,
        unique_sources=0,
        unique_destinations=0,
        allowed_count=0,
        denied_count=0,
        date_range_start=None,
        date_range_end=None,
    )

    def _query() -> TrafficSummary:
        if not _has_parquet_files(data_dir):
            return empty

        glob_pattern = f"{data_dir}/*.parquet"
        con = duckdb.connect()

        try:
            rows = con.execute(
                """
                SELECT
                    COUNT(*) AS total_records,
                    COALESCE(SUM(bytes_transferred), 0)
                        AS total_bytes,
                    COUNT(DISTINCT src_ip) AS unique_sources,
                    COUNT(DISTINCT dst_ip) AS unique_destinations,
                    COALESCE(SUM(
                        CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END
                    ), 0) AS allowed_count,
                    COALESCE(SUM(
                        CASE WHEN action IN ('DENY', 'DROP')
                        THEN 1 ELSE 0 END
                    ), 0) AS denied_count,
                    MIN(timestamp) AS date_range_start,
                    MAX(timestamp) AS date_range_end
                FROM read_parquet(?)
                """,
                [glob_pattern],
            ).fetchall()

            if not rows or rows[0][0] == 0:
                return empty

            row = rows[0]
            return TrafficSummary(
                total_records=row[0],
                total_bytes=row[1],
                unique_sources=row[2],
                unique_destinations=row[3],
                allowed_count=row[4],
                denied_count=row[5],
                date_range_start=(
                    row[6].isoformat() if row[6] else None
                ),
                date_range_end=(
                    row[7].isoformat() if row[7] else None
                ),
            )
        except (duckdb.IOException, duckdb.InvalidInputException):
            logger.warning(
                "Failed to read Parquet files in %s, returning empty results",
                data_dir,
            )
            return empty
        finally:
            con.close()

    return await asyncio.to_thread(_query)
