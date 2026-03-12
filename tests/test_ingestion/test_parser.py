"""Tests for VPC Flow Log v2 line parser."""

from __future__ import annotations

from datetime import UTC

from policyfoundry.ingestion.parser import parse_vpc_flow_log_line
from policyfoundry.ingestion.schema import ActionEnum


class TestParseValidLine:
    """Tests for parsing valid VPC Flow Log v2 lines."""

    def test_valid_v2_line_returns_normalized_flow_log(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert result is not None

    def test_valid_v2_line_has_correct_ips(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert str(result.src_ip) == "10.0.1.5"
        assert str(result.dst_ip) == "192.168.1.100"

    def test_valid_v2_line_has_correct_ports(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert result.src_port == 52431
        assert result.dst_port == 443

    def test_valid_v2_line_has_correct_bytes_and_packets(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert result.bytes_transferred == 1500
        assert result.packets_count == 20

    def test_valid_v2_line_has_correct_timestamp(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert result.timestamp.tzinfo == UTC

    def test_all_12_fields_populated(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert isinstance(result, object)
        assert result.timestamp is not None
        assert result.src_ip is not None
        assert result.dst_ip is not None
        assert result.src_port is not None
        assert result.dst_port is not None
        assert result.protocol is not None
        assert result.action is not None
        assert result.bytes_transferred is not None
        assert result.flow_direction is not None
        assert result.packets_count is not None


class TestProtocolMapping:
    """Tests for IANA protocol number to ProtocolEnum mapping."""

    def test_protocol_6_maps_to_tcp(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 1024 80 6 10 500 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result.protocol.value == "TCP"

    def test_protocol_17_maps_to_udp(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 1024 53 17 10 500 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result.protocol.value == "UDP"

    def test_protocol_1_maps_to_icmp(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 0 0 1 5 400 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result.protocol.value == "ICMP"

    def test_unknown_protocol_returns_none(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 0 0 47 5 400 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result is None


class TestActionMapping:
    """Tests for VPC action to ActionEnum mapping."""

    def test_accept_maps_to_allow(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert result.action == ActionEnum.ALLOW

    def test_reject_maps_to_deny(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 1024 80 6 10 500 1418530010 1418530070 REJECT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result.action == ActionEnum.DENY


class TestSentinelHandling:
    """Tests for AWS sentinel value handling ('-', 'NODATA')."""

    def test_sentinel_dash_for_ports_maps_to_zero(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 - - 1 5 400 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result.src_port == 0
        assert result.dst_port == 0

    def test_sentinel_dash_for_bytes_maps_to_zero(self):
        line = "2 123456789012 eni-abc123 10.0.1.5 10.0.1.6 1024 80 6 - - 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result.packets_count == 0
        assert result.bytes_transferred == 0


class TestSkippedLines:
    """Tests for lines that should be skipped (return None)."""

    def test_header_line_returns_none(self, header_line):
        result = parse_vpc_flow_log_line(
            header_line, line_number=1, file_path="test.log"
        )
        assert result is None

    def test_nodata_line_returns_none(self, nodata_line):
        result = parse_vpc_flow_log_line(
            nodata_line, line_number=1, file_path="test.log"
        )
        assert result is None

    def test_skipdata_line_returns_none(self, skipdata_line):
        result = parse_vpc_flow_log_line(
            skipdata_line, line_number=1, file_path="test.log"
        )
        assert result is None

    def test_malformed_line_returns_none(self, malformed_line):
        result = parse_vpc_flow_log_line(
            malformed_line, line_number=1, file_path="test.log"
        )
        assert result is None

    def test_malformed_line_does_not_raise(self, malformed_line):
        # Should never raise — returns None per D008
        result = parse_vpc_flow_log_line(
            malformed_line, line_number=1, file_path="test.log"
        )
        assert result is None


class TestFlowDirection:
    """Tests for flow direction defaults."""

    def test_v2_defaults_to_inbound(self, valid_vpc_v2_line):
        result = parse_vpc_flow_log_line(
            valid_vpc_v2_line, line_number=1, file_path="test.log"
        )
        assert result.flow_direction.value == "INBOUND"


class TestVersionHandling:
    """Tests for version field handling."""

    def test_non_version_2_still_attempts_parse(self):
        line = "3 123456789012 eni-abc123 10.0.1.5 10.0.1.6 1024 80 6 10 500 1418530010 1418530070 ACCEPT OK"
        result = parse_vpc_flow_log_line(line, line_number=1, file_path="test.log")
        assert result is not None
