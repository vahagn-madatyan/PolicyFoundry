"""Tests for direction inference — parametrized over all signal combinations."""

from __future__ import annotations

import pytest

from policyfoundry.analysis.direction import infer_direction
from policyfoundry.analysis.models import DirectionLabel
from policyfoundry.ingestion.excel_schema import ExcelTrafficRecord


def _record(
    *,
    ip1: str = "1.2.3.4",
    port1: int = 443,
    interface1: str = "inet",
    ip2: str = "10.0.0.1",
    port2: int = 50000,
    interface2: str = "zoneA",
    flag: str = "UIO",
    protocol: str = "TCP",
    hostname1: str = "server.example.com",
    hostname2: str = "client.internal",
) -> ExcelTrafficRecord:
    return ExcelTrafficRecord(
        protocol=protocol,
        ip1=ip1,
        port1=port1,
        interface1=interface1,
        hostname1=hostname1,
        ip2=ip2,
        port2=port2,
        interface2=interface2,
        hostname2=hostname2,
        flag=flag,
    )


# ---------------------------------------------------------------------------
# Signal 1: Well-known port detection
# ---------------------------------------------------------------------------

class TestWellKnownPort:
    """port < 1024 or in KNOWN_SERVICE_PORTS → that side is the server."""

    @pytest.mark.parametrize("service_port", [80, 443, 22, 53, 25, 110, 993])
    def test_ip1_has_well_known_port(self, service_port: int) -> None:
        """IP1 has service port → IP1 is server (dst), direction OUTBOUND."""
        rec = _record(port1=service_port, port2=50000)
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.dst_ip == rec.ip1
        assert result.src_ip == rec.ip2
        assert result.service_port == service_port
        assert result.client_port == 50000

    @pytest.mark.parametrize("service_port", [80, 443, 22])
    def test_ip2_has_well_known_port(self, service_port: int) -> None:
        """IP2 has service port → IP2 is server (dst), direction INBOUND."""
        rec = _record(port1=50000, port2=service_port, interface1="zoneA", interface2="inet")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.INBOUND
        assert result.dst_ip == rec.ip2
        assert result.src_ip == rec.ip1
        assert result.service_port == service_port
        assert result.client_port == 50000

    def test_known_service_port_5274(self) -> None:
        """5274 is a known service port → treated as service port."""
        rec = _record(port1=5274, port2=40000)
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.service_port == 5274
        assert result.dst_ip == rec.ip1

    def test_both_well_known_ports_falls_through(self) -> None:
        """Both sides have well-known ports → port signal is ambiguous, use next signal."""
        rec = _record(port1=80, port2=443, interface1="inet", interface2="zoneA")
        result = infer_direction(rec)
        # Falls to interface signal: inet side (ip1) is external → server
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.dst_ip == rec.ip1


# ---------------------------------------------------------------------------
# Signal 2: Interface zone
# ---------------------------------------------------------------------------

class TestInterfaceZone:
    """inet = external zone → that side is the server."""

    def test_ip1_on_inet_both_ephemeral(self) -> None:
        """Both ports ephemeral, but ip1 on inet → IP1 is server."""
        rec = _record(port1=40000, port2=50000, interface1="inet", interface2="zoneA")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.dst_ip == rec.ip1

    def test_ip2_on_inet_both_ephemeral(self) -> None:
        """Both ports ephemeral, but ip2 on inet → IP2 is server."""
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="inet")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.INBOUND
        assert result.dst_ip == rec.ip2

    def test_both_inet_falls_through(self) -> None:
        """Both on inet → interface signal is ambiguous."""
        rec = _record(port1=40000, port2=50000, interface1="inet", interface2="inet", flag="UIO")
        result = infer_direction(rec)
        # Falls to flag signal: 'O' → OUTBOUND, ip1 is server
        assert result.direction == DirectionLabel.OUTBOUND

    def test_neither_inet_falls_through(self) -> None:
        """Neither interface is inet → interface signal fails."""
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="zoneB", flag="UIO")
        result = infer_direction(rec)
        # Falls to flag signal: 'O' → OUTBOUND
        assert result.direction == DirectionLabel.OUTBOUND

    def test_inet_case_insensitive(self) -> None:
        """Interface matching is case-insensitive."""
        rec = _record(port1=40000, port2=50000, interface1="INET", interface2="zoneA")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND


# ---------------------------------------------------------------------------
# Signal 3: Flag 'O'
# ---------------------------------------------------------------------------

class TestFlagSignal:
    """'O' in flag → outbound from FW perspective → ip1 is server."""

    def test_uio_flag(self) -> None:
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="zoneB", flag="UIO")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND

    def test_o_only_flag(self) -> None:
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="zoneB", flag="O")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND

    def test_ui_flag_no_o(self) -> None:
        """UI flag (no O) → flag signal doesn't resolve, falls to UNKNOWN."""
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="zoneB", flag="UI")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.UNKNOWN

    def test_u_flag_no_o(self) -> None:
        """U flag (no O) → UNKNOWN."""
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="zoneB", flag="U")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.UNKNOWN


# ---------------------------------------------------------------------------
# Signal 4: Fallback UNKNOWN
# ---------------------------------------------------------------------------

class TestUnknownFallback:
    """Both ports ephemeral + no interface/flag resolution → UNKNOWN."""

    def test_both_ephemeral_no_signals(self) -> None:
        rec = _record(port1=40000, port2=50000, interface1="zoneA", interface2="zoneB", flag="U")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.UNKNOWN
        # Fallback keeps ip1 as src, ip2 as dst
        assert result.src_ip == rec.ip1
        assert result.dst_ip == rec.ip2
        assert result.service_port == rec.port1
        assert result.client_port == rec.port2

    def test_both_ephemeral_ui_flag(self) -> None:
        rec = _record(port1=32810, port2=45000, interface1="zoneA", interface2="zoneB", flag="UI")
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.UNKNOWN


# ---------------------------------------------------------------------------
# Realistic sample-data scenarios
# ---------------------------------------------------------------------------

class TestRealisticScenarios:
    """Scenarios matching the sample data profile."""

    def test_typical_outbound_web(self) -> None:
        """Typical record: port1=443 on inet, port2=50000 on zoneA, flag UIO."""
        rec = _record(
            ip1="93.184.216.34",
            port1=443,
            interface1="inet",
            hostname1="example.com",
            ip2="10.195.231.5",
            port2=50123,
            interface2="zoneA",
            hostname2="workstation5",
            flag="UIO",
        )
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.src_ip == "10.195.231.5"
        assert result.dst_ip == "93.184.216.34"
        assert result.service_port == 443
        assert result.client_port == 50123

    def test_typical_outbound_port_5274(self) -> None:
        """Known service port 5274 on inet side."""
        rec = _record(
            ip1="192.0.2.100",
            port1=5274,
            interface1="inet",
            ip2="10.195.231.10",
            port2=40500,
            interface2="zoneA",
            flag="UIO",
        )
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.service_port == 5274
        assert result.src_ip == "10.195.231.10"

    def test_ambiguous_both_ephemeral(self) -> None:
        """Both ports ephemeral, inet interface but both IPs are private-ish."""
        rec = _record(
            ip1="10.166.87.98",
            port1=32810,
            interface1="inet",
            ip2="10.38.235.22",
            port2=45000,
            interface2="zoneA",
            flag="UI",
        )
        result = infer_direction(rec)
        # inet on ip1 side → interface signal resolves it
        assert result.direction == DirectionLabel.OUTBOUND
        assert result.dst_ip == "10.166.87.98"

    def test_truly_ambiguous(self) -> None:
        """Both ephemeral, unknown interfaces, no O flag → UNKNOWN."""
        rec = _record(
            ip1="10.166.87.98",
            port1=32810,
            interface1="dmz",
            ip2="10.38.235.22",
            port2=45000,
            interface2="internal",
            flag="UI",
        )
        result = infer_direction(rec)
        assert result.direction == DirectionLabel.UNKNOWN
