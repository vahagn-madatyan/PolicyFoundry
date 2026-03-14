"""Tests for local file ingestion with async I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from policyfoundry.ingestion.local import ingest_local_files
from policyfoundry.ingestion.schema import ActionEnum

if TYPE_CHECKING:
    from pathlib import Path


class TestIngestSingleFile:
    """Tests for single file ingestion."""

    async def test_returns_ingestion_result_with_records(self, tmp_log_file):
        result = await ingest_local_files([str(tmp_log_file)])
        assert len(result.records) == 3

    async def test_all_12_fields_populated(self, tmp_log_file):
        result = await ingest_local_files([str(tmp_log_file)])
        record = result.records[0]
        assert record.timestamp is not None
        assert record.src_ip is not None
        assert record.dst_ip is not None
        assert record.src_port is not None
        assert record.dst_port is not None
        assert record.protocol is not None
        assert record.action is not None
        assert record.bytes_transferred is not None
        assert record.flow_direction is not None
        assert record.packets_count is not None

    async def test_source_files_tracked(self, tmp_log_file):
        result = await ingest_local_files([str(tmp_log_file)])
        assert len(result.source_files) == 1


class TestIngestMultipleFiles:
    """Tests for multi-file ingestion."""

    async def test_merges_records_from_multiple_files(self, tmp_path):
        f1 = tmp_path / "flow1.log"
        f1.write_text(
            "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
            "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
        )
        f2 = tmp_path / "flow2.log"
        f2.write_text(
            "2 123456789012 eni-abc123 10.0.2.10 172.16.0.50 "
            "12345 80 6 15 800 1418530020 1418530080 ACCEPT OK\n"
        )
        result = await ingest_local_files([str(f1), str(f2)])
        assert len(result.records) == 2


class TestMalformedLines:
    """Tests for malformed line handling."""

    async def test_malformed_lines_skipped_with_count(self, tmp_log_file):
        result = await ingest_local_files([str(tmp_log_file)])
        assert result.errors_skipped == 1

    async def test_malformed_lines_produce_warnings(self, tmp_log_file):
        result = await ingest_local_files([str(tmp_log_file)])
        assert any("malformed" in w for w in result.warnings)


class TestDeduplication:
    """Tests for deduplication during ingestion."""

    async def test_duplicate_lines_deduplicated(self, tmp_path):
        f = tmp_path / "dup.log"
        f.write_text(
            "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
            "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
            "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
            "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
        )
        result = await ingest_local_files([str(f)])
        assert len(result.records) == 1
        assert result.duplicates_removed == 1


class TestMissingFiles:
    """Tests for missing file handling."""

    async def test_missing_file_skipped_with_warning(self, tmp_path):
        result = await ingest_local_files([str(tmp_path / "nonexistent.log")])
        assert len(result.records) == 0
        assert len(result.warnings) > 0

    async def test_missing_file_continues_with_others(self, tmp_path):
        f = tmp_path / "valid.log"
        f.write_text(
            "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
            "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
        )
        result = await ingest_local_files([
            str(tmp_path / "nonexistent.log"),
            str(f),
        ])
        assert len(result.records) == 1


class TestGlobPatterns:
    """Tests for glob pattern expansion."""

    async def test_glob_expands_to_matching_files(self, tmp_path):
        f1 = tmp_path / "flow1.log"
        f1.write_text(
            "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
            "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
        )
        f2 = tmp_path / "flow2.log"
        f2.write_text(
            "2 123456789012 eni-abc123 10.0.2.10 172.16.0.50 "
            "12345 80 6 15 800 1418530020 1418530080 ACCEPT OK\n"
        )
        result = await ingest_local_files([str(tmp_path / "*.log")])
        assert len(result.records) == 2


class TestEmptyFile:
    """Tests for empty file handling."""

    async def test_empty_file_produces_zero_records(self, tmp_path):
        f = tmp_path / "empty.log"
        f.write_text("")
        result = await ingest_local_files([str(f)])
        assert len(result.records) == 0


class TestNodataSkipdata:
    """Tests for NODATA/SKIPDATA line handling."""

    async def test_nodata_lines_not_counted_as_errors(self, tmp_path):
        f = tmp_path / "nodata.log"
        f.write_text(
            "2 123456789012 eni-abc123 - - - - - - - "
            "1418530010 1418530070 - NODATA\n"
            "2 123456789012 eni-abc123 - - - - - - - "
            "1418530010 1418530070 - SKIPDATA\n"
        )
        result = await ingest_local_files([str(f)])
        assert result.errors_skipped == 0
