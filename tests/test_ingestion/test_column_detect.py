"""Tests for column auto-detection logic."""

import pytest

from policyfoundry.exceptions import ExcelParseError
from policyfoundry.ingestion.column_detect import detect_columns
from policyfoundry.ingestion.excel_schema import ColumnMapping


class TestDetectColumns:
    """Tests for detect_columns synonym-based auto-detection."""

    def test_sample_file_exact_headers(self):
        """Sample file headers should map all 10 fields correctly."""
        headers = [
            "Protocol", "Interface1", "HostName1", "IP1", "Port1",
            "Interface2", "HostName2", "IP2", "Port2", "Flag",
        ]
        mapping = detect_columns(headers)
        assert isinstance(mapping, ColumnMapping)
        assert mapping.protocol == 0
        assert mapping.interface1 == 1
        assert mapping.hostname1 == 2
        assert mapping.ip1 == 3
        assert mapping.port1 == 4
        assert mapping.interface2 == 5
        assert mapping.hostname2 == 6
        assert mapping.ip2 == 7
        assert mapping.port2 == 8
        assert mapping.flag == 9

    def test_case_insensitive_matching(self):
        """Headers should match regardless of case."""
        headers = [
            "PROTOCOL", "interface1", "HostName1", "ip1", "PORT1",
            "Interface2", "hostname2", "IP2", "port2", "FLAG",
        ]
        mapping = detect_columns(headers)
        assert mapping.protocol == 0
        assert mapping.flag == 9

    def test_common_synonym_source_destination(self):
        """Common Source/Destination naming should auto-detect."""
        headers = [
            "Protocol", "Source Interface", "Source Hostname",
            "Source IP", "Source Port", "Destination Interface",
            "Destination Hostname", "Destination IP",
            "Destination Port", "Flags",
        ]
        mapping = detect_columns(headers)
        assert mapping.protocol == 0
        assert mapping.ip1 == 3
        assert mapping.port1 == 4
        assert mapping.ip2 == 7
        assert mapping.port2 == 8
        assert mapping.flag == 9

    def test_common_synonym_src_dst_abbreviated(self):
        """Abbreviated SrcIP/DstPort style should auto-detect."""
        headers = [
            "Proto", "SrcIntf", "SrcHost", "SrcIP", "SrcPort",
            "DstIntf", "DstHost", "DstIP", "DstPort", "TCP Flags",
        ]
        mapping = detect_columns(headers)
        assert mapping.protocol == 0
        assert mapping.ip1 == 3
        assert mapping.port1 == 4
        assert mapping.ip2 == 7
        assert mapping.port2 == 8

    def test_underscore_variants(self):
        """Underscore-separated variants (src_ip, dst_port) should match."""
        headers = [
            "protocol", "src_interface", "src_hostname",
            "src_ip", "src_port", "dst_interface",
            "dst_hostname", "dst_ip", "dst_port", "tcp_flags",
        ]
        mapping = detect_columns(headers)
        assert mapping.ip1 == 3
        assert mapping.port2 == 8

    def test_whitespace_in_headers(self):
        """Headers with extra whitespace should still match."""
        headers = [
            "  Protocol  ", " Interface1 ", "  HostName1  ",
            " IP1 ", " Port1 ", " Interface2 ",
            " HostName2 ", " IP2 ", " Port2 ", " Flag ",
        ]
        mapping = detect_columns(headers)
        assert mapping.protocol == 0
        assert mapping.flag == 9

    def test_missing_single_column_raises(self):
        """Missing one column should raise ExcelParseError listing the field."""
        headers = [
            "Protocol", "Interface1", "HostName1", "IP1", "Port1",
            "Interface2", "HostName2", "IP2", "Port2",
            # Flag missing — replaced with unknown
            "UnknownCol",
        ]
        with pytest.raises(ExcelParseError, match="flag") as exc_info:
            detect_columns(headers)
        assert "COLUMN_DETECT_FAILED" == exc_info.value.error_code
        assert "flag" in exc_info.value.details["unmatched_fields"]

    def test_missing_multiple_columns_raises(self):
        """Missing multiple columns should list all unmatched fields."""
        headers = [
            "Protocol", "Col1", "Col2", "Col3", "Col4",
            "Col5", "Col6", "Col7", "Col8", "Flag",
        ]
        with pytest.raises(ExcelParseError) as exc_info:
            detect_columns(headers)
        unmatched = exc_info.value.details["unmatched_fields"]
        # ip1, port1, interface1, hostname1, ip2, port2, interface2, hostname2 missing
        assert len(unmatched) == 8

    def test_actionable_error_message(self):
        """Error message should suggest using ExcelConfig.column_mapping."""
        headers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
        with pytest.raises(ExcelParseError, match="ExcelConfig.column_mapping"):
            detect_columns(headers)

    def test_empty_headers_raises(self):
        """Empty header list should raise ExcelParseError."""
        with pytest.raises(ExcelParseError):
            detect_columns([])

    def test_duplicate_header_names_first_wins(self):
        """When duplicate headers exist, the first match is claimed."""
        headers = [
            "Protocol", "Interface1", "HostName1", "IP1", "Port1",
            "Interface2", "HostName2", "IP2", "Port2", "Flag",
            "Protocol",  # duplicate — should not interfere
        ]
        mapping = detect_columns(headers)
        assert mapping.protocol == 0  # first one wins


class TestExcelConfigIntegration:
    """Test ExcelConfig nesting in PolicyFoundryConfig."""

    def test_excel_config_defaults(self):
        """ExcelConfig should instantiate with expected defaults."""
        from policyfoundry.config.models import ExcelConfig

        config = ExcelConfig()
        assert config.sheet_name is None
        assert config.header_row == 1
        assert config.column_mapping is None

    def test_excel_config_in_policy_foundry_config(self):
        """ExcelConfig should be nested in PolicyFoundryConfig."""
        from policyfoundry.config.models import PolicyFoundryConfig

        config = PolicyFoundryConfig()
        assert hasattr(config, "excel")
        assert config.excel.sheet_name is None
        assert config.excel.header_row == 1
        assert config.excel.column_mapping is None
