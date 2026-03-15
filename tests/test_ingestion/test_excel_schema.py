"""Tests for Excel traffic record models and ingestion result."""

import pytest
from pydantic import ValidationError

from policyfoundry.ingestion.excel_schema import (
    ColumnMapping,
    ExcelIngestionResult,
    ExcelTrafficRecord,
)


class TestExcelTrafficRecord:
    """Tests for ExcelTrafficRecord Pydantic model."""

    def _valid_kwargs(self, **overrides):
        """Return a valid record dict, with optional overrides."""
        base = {
            "protocol": "TCP",
            "ip1": "10.38.73.2",
            "port1": 80,
            "interface1": "inet",
            "hostname1": "hostname1",
            "ip2": "10.194.184.42",
            "port2": 54321,
            "interface2": "zoneA",
            "hostname2": "name42",
            "flag": "UIO",
        }
        base.update(overrides)
        return base

    def test_valid_record_construction(self):
        """A record with all valid fields should construct without error."""
        record = ExcelTrafficRecord(**self._valid_kwargs())
        assert record.protocol == "TCP"
        assert record.ip1 == "10.38.73.2"
        assert record.port1 == 80
        assert record.interface1 == "inet"
        assert record.hostname1 == "hostname1"
        assert record.ip2 == "10.194.184.42"
        assert record.port2 == 54321
        assert record.interface2 == "zoneA"
        assert record.hostname2 == "name42"
        assert record.flag == "UIO"

    def test_whitespace_stripping_all_string_fields(self):
        """Trailing/leading whitespace on all string fields should be stripped."""
        record = ExcelTrafficRecord(
            **self._valid_kwargs(
                protocol="  TCP  ",
                ip1="  10.38.73.2  ",
                interface1="  inet  ",
                hostname1="  hostname1  ",
                ip2="  10.194.184.42  ",
                interface2="  zoneA  ",
                hostname2="  name42  ",
                flag="  UIO  ",
            )
        )
        assert record.protocol == "TCP"
        assert record.ip1 == "10.38.73.2"
        assert record.interface1 == "inet"
        assert record.hostname1 == "hostname1"
        assert record.ip2 == "10.194.184.42"
        assert record.interface2 == "zoneA"
        assert record.hostname2 == "name42"
        assert record.flag == "UIO"

    def test_dns_annotation_cleanup_no_dns_resolution(self):
        """hostname2 with '(no DNS resolution)' annotation should be cleaned."""
        record = ExcelTrafficRecord(
            **self._valid_kwargs(hostname2="10.194.184.42 (no DNS resolution)")
        )
        assert record.hostname2 == "10.194.184.42"

    def test_dns_annotation_cleanup_with_whitespace(self):
        """hostname2 with annotation AND trailing whitespace should be cleaned."""
        record = ExcelTrafficRecord(
            **self._valid_kwargs(hostname2="  10.194.184.42 (no DNS resolution)  ")
        )
        assert record.hostname2 == "10.194.184.42"

    def test_dns_annotation_other_annotation(self):
        """hostname2 with arbitrary parenthetical annotation should be cleaned."""
        record = ExcelTrafficRecord(
            **self._valid_kwargs(hostname2="myhost.local (some note)")
        )
        assert record.hostname2 == "myhost.local"

    def test_dns_annotation_plain_hostname_unchanged(self):
        """hostname2 without annotation should pass through unchanged."""
        record = ExcelTrafficRecord(
            **self._valid_kwargs(hostname2="name42")
        )
        assert record.hostname2 == "name42"

    def test_port_valid_zero(self):
        """Port 0 is valid (ephemeral/unspecified)."""
        record = ExcelTrafficRecord(**self._valid_kwargs(port1=0))
        assert record.port1 == 0

    def test_port_valid_max(self):
        """Port 65535 is the maximum valid port."""
        record = ExcelTrafficRecord(**self._valid_kwargs(port2=65535))
        assert record.port2 == 65535

    def test_port_invalid_negative(self):
        """Negative ports should be rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ExcelTrafficRecord(**self._valid_kwargs(port1=-1))

    def test_port_invalid_too_high(self):
        """Ports above 65535 should be rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            ExcelTrafficRecord(**self._valid_kwargs(port2=65536))

    def test_port_invalid_too_high_large(self):
        """Very large port numbers should be rejected."""
        with pytest.raises(ValidationError):
            ExcelTrafficRecord(**self._valid_kwargs(port1=100000))

    def test_all_ten_fields_present(self):
        """ExcelTrafficRecord must have exactly 10 fields."""
        record = ExcelTrafficRecord(**self._valid_kwargs())
        field_names = set(ExcelTrafficRecord.model_fields.keys())
        expected = {
            "protocol", "ip1", "port1", "interface1", "hostname1",
            "ip2", "port2", "interface2", "hostname2", "flag",
        }
        assert field_names == expected


class TestColumnMapping:
    """Tests for ColumnMapping model."""

    def test_all_ten_indices_required(self):
        """ColumnMapping must have all 10 column indices."""
        mapping = ColumnMapping(
            protocol=0, ip1=3, port1=4, interface1=1, hostname1=2,
            ip2=7, port2=8, interface2=5, hostname2=6, flag=9,
        )
        assert mapping.protocol == 0
        assert mapping.flag == 9

    def test_missing_field_raises(self):
        """Missing a required field should raise ValidationError."""
        with pytest.raises(ValidationError):
            ColumnMapping(
                protocol=0, ip1=3, port1=4, interface1=1, hostname1=2,
                ip2=7, port2=8, interface2=5, hostname2=6,
                # flag missing
            )

    def test_from_headers_delegates(self):
        """from_headers should produce a valid ColumnMapping for known headers."""
        headers = [
            "Protocol", "Interface1", "HostName1", "IP1", "Port1",
            "Interface2", "HostName2", "IP2", "Port2", "Flag",
        ]
        mapping = ColumnMapping.from_headers(headers)
        assert mapping.protocol == 0
        assert mapping.flag == 9


class TestExcelIngestionResult:
    """Tests for ExcelIngestionResult model."""

    def test_defaults(self):
        """ExcelIngestionResult should instantiate with defaults."""
        result = ExcelIngestionResult()
        assert result.records == []
        assert result.column_mapping is None
        assert result.total_rows == 0
        assert result.parsed_rows == 0
        assert result.skipped_rows == 0
        assert result.warnings == []
        assert result.source_file == ""

    def test_with_records(self):
        """Should accept a list of records and stats."""
        record = ExcelTrafficRecord(
            protocol="TCP", ip1="10.0.0.1", port1=80, interface1="inet",
            hostname1="host1", ip2="10.0.0.2", port2=443, interface2="zoneA",
            hostname2="host2", flag="UIO",
        )
        result = ExcelIngestionResult(
            records=[record],
            total_rows=100,
            parsed_rows=99,
            skipped_rows=1,
            source_file="test.xlsx",
        )
        assert len(result.records) == 1
        assert result.total_rows == 100
