"""Local file ingestion with async I/O and glob expansion.

Reads VPC Flow Log files from disk, parses each line, deduplicates
records, and returns an IngestionResult with full statistics.
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.ingestion.parser import is_header_line, parse_vpc_flow_log_line
from policyfoundry.ingestion.result import IngestionResult

if TYPE_CHECKING:
    from policyfoundry.ingestion.schema import NormalizedFlowLog

logger = logging.getLogger(__name__)


def _expand_paths(paths: list[str]) -> list[Path]:
    """Expand glob patterns and resolve to unique file paths."""
    resolved: list[Path] = []
    seen: set[Path] = set()
    for entry in paths:
        expanded = glob.glob(entry)
        if not expanded:
            # No glob match — treat as literal path
            p = Path(entry)
            if p not in seen:
                seen.add(p)
                resolved.append(p)
        else:
            for match in sorted(expanded):
                p = Path(match)
                if p not in seen:
                    seen.add(p)
                    resolved.append(p)
    return resolved


async def ingest_local_files(paths: list[str]) -> IngestionResult:
    """Ingest VPC Flow Log files from local filesystem.

    Reads each file asynchronously, parses lines, deduplicates records,
    and returns an IngestionResult with accumulated statistics.

    Handles:
    - Glob pattern expansion (e.g., "*.log")
    - Missing/inaccessible files (skipped with warning)
    - Malformed lines (skipped with warning and error count)
    - NODATA/SKIPDATA metadata lines (silently skipped)
    - Duplicate records within the run (deduplicated)

    Args:
        paths: List of file paths or glob patterns.

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

    resolved_paths = _expand_paths(paths)

    for file_path in resolved_paths:
        try:
            async with aiofiles.open(file_path) as f:
                source_files.append(str(file_path))
                line_number = 0
                async for line in f:
                    line_number += 1
                    stripped = line.strip()
                    if not stripped:
                        continue

                    total_lines += 1

                    # Skip header lines (don't count as data lines)
                    if is_header_line(stripped):
                        total_lines -= 1
                        continue

                    record = parse_vpc_flow_log_line(
                        stripped,
                        line_number=line_number,
                        file_path=str(file_path),
                    )

                    if record is None:
                        # Check if it's NODATA/SKIPDATA metadata
                        fields = stripped.split()

                        if len(fields) >= 14 and fields[13] in ("NODATA", "SKIPDATA"):
                            # Don't count metadata as data lines
                            total_lines -= 1
                            continue

                        errors_skipped += 1
                        snippet = stripped[:80]
                        warnings.append(
                            f"Line {line_number} in {file_path}"
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

        except FileNotFoundError:
            warnings.append(
                f"File not found: {file_path} -- skipped"
            )
        except PermissionError:
            warnings.append(
                f"Permission denied: {file_path} -- skipped"
            )

    return IngestionResult(
        records=records,
        total_lines=total_lines,
        duplicates_removed=duplicates_removed,
        errors_skipped=errors_skipped,
        source_files=source_files,
        warnings=warnings,
    )
