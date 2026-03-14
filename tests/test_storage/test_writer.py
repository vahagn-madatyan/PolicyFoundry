"""Tests for storage writer: Parquet writing, schema, metadata, dedup, and purge."""

import re
from pathlib import Path

import pyarrow.parquet as pq

from policyfoundry.ingestion.schema import NormalizedFlowLog
from policyfoundry.storage.models import WriteResult
from policyfoundry.storage.writer import purge_data, write_records


class TestWriteRecords:
    """Tests for basic write functionality."""

    async def test_write_produces_parquet_file(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        assert len(parquet_files) == 1

    async def test_write_returns_write_result(self, sample_records, data_dir):
        result = await write_records(sample_records, data_dir, ["test.log"])
        assert isinstance(result, WriteResult)
        assert result.records_written == 5

    async def test_written_file_has_zstd_compression(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        meta = pq.read_metadata(str(parquet_files[0]))
        # Check that at least one row group uses zstd
        rg = meta.row_group(0)
        col = rg.column(0)
        assert col.compression == "ZSTD"


class TestParquetSchema:
    """Tests for Parquet file schema correctness."""

    async def test_has_13_columns(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        table = pq.read_table(str(parquet_files[0]))
        assert len(table.schema) == 13

    async def test_column_names(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        table = pq.read_table(str(parquet_files[0]))
        names = [field.name for field in table.schema]
        assert "timestamp" in names
        assert "src_ip" in names
        assert "dst_ip" in names
        assert "dedup_hash" in names

    async def test_ip_stored_as_string(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        table = pq.read_table(str(parquet_files[0]))
        src_ip_col = table.column("src_ip")
        assert src_ip_col[0].as_py() == "10.0.0.1"

    async def test_enum_stored_as_string_value(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        table = pq.read_table(str(parquet_files[0]))
        protocol_col = table.column("protocol")
        assert protocol_col[0].as_py() == "TCP"


class TestFileMetadata:
    """Tests for Parquet file custom metadata."""

    async def test_has_source_files_key(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        meta = pq.read_metadata(str(parquet_files[0]))
        metadata = meta.schema.to_arrow_schema().metadata
        assert b"policyfoundry_source_files" in metadata

    async def test_has_ingestion_timestamp_key(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        meta = pq.read_metadata(str(parquet_files[0]))
        metadata = meta.schema.to_arrow_schema().metadata
        assert b"policyfoundry_ingestion_timestamp" in metadata

    async def test_has_record_count_key(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        meta = pq.read_metadata(str(parquet_files[0]))
        metadata = meta.schema.to_arrow_schema().metadata
        assert b"policyfoundry_record_count" in metadata

    async def test_source_files_value(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        meta = pq.read_metadata(str(parquet_files[0]))
        metadata = meta.schema.to_arrow_schema().metadata
        value = metadata[b"policyfoundry_source_files"]
        assert b"test.log" in value


class TestCrossRunDedup:
    """Tests for cross-run deduplication."""

    async def test_duplicate_records_filtered(
        self, sample_records, pre_written_parquet
    ):
        """Writing same records again should detect them as duplicates."""
        result = await write_records(
            sample_records, pre_written_parquet, ["test2.log"]
        )
        assert result.records_written == 0
        assert result.cross_run_duplicates_removed == 5

    async def test_partial_duplicates(self, sample_records, pre_written_parquet):
        """Mix of old and new records: old filtered, new written."""
        from datetime import UTC, datetime
        from ipaddress import IPv4Address

        from policyfoundry.ingestion.schema import FlowDirection, ProtocolEnum

        new_record = NormalizedFlowLog(
            timestamp=datetime(2025, 1, 15, 11, 0, 0, tzinfo=UTC),
            src_ip=IPv4Address("10.0.0.99"),
            dst_ip=IPv4Address("172.16.0.99"),
            src_port=55555,
            dst_port=8080,
            protocol=ProtocolEnum.TCP,
            action=sample_records[0].action,
            bytes_transferred=999,
            rule_id=None,
            app_name=None,
            flow_direction=FlowDirection.INBOUND,
            packets_count=1,
        )
        combined = sample_records + [new_record]
        result = await write_records(
            combined, pre_written_parquet, ["test3.log"]
        )
        assert result.records_written == 1
        assert result.cross_run_duplicates_removed == 5


class TestPurgeData:
    """Tests for purge_data function."""

    async def test_deletes_parquet_files(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        count = await purge_data(data_dir)
        assert count == 1
        assert len(list(data_dir.glob("*.parquet"))) == 0

    async def test_returns_count(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test1.log"])
        await write_records(sample_records, data_dir, ["test2.log"])
        count = await purge_data(data_dir)
        # First write creates 1 file, second write may create 0 (all dupes)
        assert count >= 1

    async def test_empty_directory_succeeds(self, data_dir):
        count = await purge_data(data_dir)
        assert count == 0


class TestEmptyInput:
    """Tests for empty input handling."""

    async def test_empty_list_returns_zero(self, data_dir):
        result = await write_records([], data_dir, [])
        assert result.records_written == 0


class TestFileNaming:
    """Tests for output file naming convention."""

    async def test_filename_pattern(self, sample_records, data_dir):
        await write_records(sample_records, data_dir, ["test.log"])
        parquet_files = list(data_dir.glob("*.parquet"))
        assert len(parquet_files) == 1
        name = parquet_files[0].name
        # D014: YYYYMMDDTHHMMSSffffff_{8charhash}.parquet
        assert re.match(r"\d{8}T\d{12}_[a-f0-9]{8}\.parquet", name)
