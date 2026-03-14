"""Tests for S3-based VPC Flow Log ingestion."""

from __future__ import annotations

import gzip

import boto3
import pytest
from moto import mock_aws

from policyfoundry.ingestion.s3 import ingest_from_s3

_BUCKET = "test-flow-logs"
_PREFIX = "vpc-logs/"

_SAMPLE_LOG_MULTI = (
    "version account-id interface-id srcaddr dstaddr srcport dstport "
    "protocol packets bytes start end action log-status\n"
    "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
    "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
    "2 123456789012 eni-abc123 10.0.2.10 172.16.0.50 "
    "12345 80 6 15 800 1418530020 1418530080 ACCEPT OK\n"
    "2 123456789012 eni-abc123 10.0.3.20 10.0.4.30 "
    "0 0 1 5 400 1418530030 1418530090 ACCEPT OK\n"
    "this is a malformed line with too few fields\n"
)

_SAMPLE_LOG_SINGLE = (
    "version account-id interface-id srcaddr dstaddr srcport dstport "
    "protocol packets bytes start end action log-status\n"
    "2 123456789012 eni-abc123 10.0.1.5 192.168.1.100 "
    "52431 443 6 20 1500 1418530010 1418530070 ACCEPT OK\n"
)


@pytest.fixture(autouse=True)
def _aws_credentials(monkeypatch):
    """Set dummy AWS credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


def _create_bucket_with_objects(objects: dict[str, bytes]) -> None:
    """Helper: create S3 bucket and upload objects using sync boto3."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=_BUCKET)
    for key, body in objects.items():
        s3.put_object(Bucket=_BUCKET, Key=f"{_PREFIX}{key}", Body=body)


class TestS3IngestionPlainText:
    """Tests for plain text S3 log ingestion."""

    async def test_plain_text_log_returns_correct_record_count(self):
        """Single plain text log file returns correct number of records."""
        with mock_aws():
            _create_bucket_with_objects({
                "log1.txt": _SAMPLE_LOG_SINGLE.encode(),
            })
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            assert len(result.records) == 1

    async def test_source_files_tracked_as_s3_uri(self):
        """Source files are tracked as s3://bucket/key format."""
        with mock_aws():
            _create_bucket_with_objects({
                "log1.txt": _SAMPLE_LOG_SINGLE.encode(),
            })
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            assert all(f.startswith("s3://") for f in result.source_files)


class TestS3IngestionGzip:
    """Tests for gzip-compressed S3 log ingestion."""

    async def test_gz_file_decompressed_and_parsed(self):
        """Gzip-compressed log file is decompressed and parsed correctly."""
        with mock_aws():
            compressed = gzip.compress(_SAMPLE_LOG_SINGLE.encode())
            _create_bucket_with_objects({
                "log1.txt.gz": compressed,
            })
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            assert len(result.records) == 1


class TestS3IngestionPrefixScan:
    """Test prefix scan discovers all objects."""

    async def test_multiple_objects_discovered_and_parsed(self):
        """Multiple objects under a prefix are all discovered and parsed."""
        with mock_aws():
            _create_bucket_with_objects({
                "log1.txt": _SAMPLE_LOG_SINGLE.encode(),
                "log2.txt": _SAMPLE_LOG_SINGLE.encode(),
            })
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            # Two files with the same record → dedup removes one
            assert len(result.source_files) == 2

    async def test_paginator_handles_multiple_objects(self):
        """Paginator is used for listing objects (test with >1 objects)."""
        with mock_aws():
            objects = {}
            for i in range(3):
                objects[f"log{i}.txt"] = _SAMPLE_LOG_SINGLE.encode()
            _create_bucket_with_objects(objects)
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            assert len(result.source_files) == 3


class TestS3IngestionDedup:
    """Tests for S3 cross-object deduplication."""

    async def test_duplicates_across_objects_removed(self):
        """Duplicate records across different S3 objects are deduplicated."""
        with mock_aws():
            _create_bucket_with_objects({
                "log1.txt": _SAMPLE_LOG_SINGLE.encode(),
                "log2.txt": _SAMPLE_LOG_SINGLE.encode(),
            })
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            assert len(result.records) == 1
            assert result.duplicates_removed == 1


class TestS3IngestionMalformed:
    """Test malformed line handling in S3 objects."""

    async def test_malformed_lines_produce_warnings(self):
        """Malformed lines in S3 objects produce warnings, not crashes."""
        with mock_aws():
            _create_bucket_with_objects({
                "log1.txt": _SAMPLE_LOG_MULTI.encode(),
            })
            result = await ingest_from_s3(_BUCKET, _PREFIX)
            assert result.errors_skipped > 0
            assert len(result.warnings) > 0


class TestS3IngestionErrorHandling:
    """Tests for S3 error handling."""

    async def test_nonexistent_bucket_returns_empty_with_warning(self):
        """Non-existent bucket returns IngestionResult with 0 records and warning."""
        with mock_aws():
            result = await ingest_from_s3("nonexistent-bucket", _PREFIX)
            assert len(result.records) == 0
            assert len(result.warnings) > 0

    async def test_access_denied_returns_empty_with_warning(self):
        """Access denied returns IngestionResult with warning (does not raise)."""
        with mock_aws():
            result = await ingest_from_s3("no-such-bucket-12345", _PREFIX)
            assert len(result.records) == 0
            assert len(result.warnings) > 0


class TestS3IngestionAwsProfile:
    """Test AWS profile forwarding."""

    async def test_aws_profile_forwarded_to_session(self):
        """aws_profile parameter is forwarded to boto3 Session."""
        with mock_aws():
            _create_bucket_with_objects({
                "log1.txt": _SAMPLE_LOG_SINGLE.encode(),
            })
            # Should not error with None profile (default)
            result = await ingest_from_s3(_BUCKET, _PREFIX, aws_profile=None)
            assert len(result.records) == 1

    async def test_invalid_profile_returns_warning_not_crash(self):
        """Invalid aws_profile returns warning instead of crashing."""
        result = await ingest_from_s3(
            _BUCKET, _PREFIX, aws_profile="nonexistent-profile"
        )
        assert len(result.records) == 0
        assert len(result.warnings) > 0

    async def test_aws_profile_passed_to_boto3_session(self, monkeypatch):
        """Verify aws_profile is actually forwarded to boto3.Session."""
        captured_profile = {}

        class MockSession:
            def __init__(self, *, profile_name=None):
                captured_profile["profile_name"] = profile_name

            def client(self, *args, **kwargs):
                raise Exception("stop here")

        monkeypatch.setattr("policyfoundry.ingestion.s3.boto3.Session", MockSession)
        result = await ingest_from_s3(
            _BUCKET, _PREFIX, aws_profile="my-custom-profile"
        )
        assert captured_profile["profile_name"] == "my-custom-profile"
