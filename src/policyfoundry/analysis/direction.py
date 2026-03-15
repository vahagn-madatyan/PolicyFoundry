"""Direction inference for neutral ip1/ip2 traffic records.

Maps ``ExcelTrafficRecord`` fields to normalized src (client) / dst (server)
using a multi-signal heuristic:

1. **Well-known port** — if exactly one side has port < 1024 or a known
   service port (e.g. 5274), that side is the server.
2. **Interface zone** — ``inet`` = external; presence indicates the internet-
   facing side.
3. **Flag signal** — ``'O'`` in the flag string (e.g. UIO) suggests outbound
   from the firewall perspective.
4. **Fallback** — ``UNKNOWN`` when signals are insufficient.
"""

from __future__ import annotations

from policyfoundry.analysis.models import DirectionLabel, DirectionResult
from policyfoundry.ingestion.excel_schema import ExcelTrafficRecord

# Well-known port threshold (IANA assigned ports 0–1023)
_WELL_KNOWN_THRESHOLD: int = 1024

# Additional service ports not in the well-known range but observed
# in real traffic data (e.g. Juniper SRX management, etc.)
KNOWN_SERVICE_PORTS: frozenset[int] = frozenset({5274})

# Interface name substrings that indicate the external / internet zone
_EXTERNAL_ZONE_MARKERS: frozenset[str] = frozenset({"inet"})


def _is_service_port(port: int) -> bool:
    """Return True if *port* looks like a service / server port."""
    return port < _WELL_KNOWN_THRESHOLD or port in KNOWN_SERVICE_PORTS


def _is_external_interface(interface: str) -> bool:
    """Return True if *interface* matches an external zone marker."""
    lower = interface.lower()
    return any(marker in lower for marker in _EXTERNAL_ZONE_MARKERS)


def infer_direction(record: ExcelTrafficRecord) -> DirectionResult:
    """Infer traffic direction and normalize src/dst from a neutral record.

    Returns a :class:`DirectionResult` with the client mapped to ``src_ip``
    and the server mapped to ``dst_ip``.

    Signal priority:
        1. Well-known / known-service port (strongest).
        2. Interface zone (inet = external side → server).
        3. Flag 'O' (outbound from FW perspective).
        4. Fallback to UNKNOWN — ip1 kept as src, ip2 as dst.
    """
    port1_is_service = _is_service_port(record.port1)
    port2_is_service = _is_service_port(record.port2)

    # --- Signal 1: well-known / known-service port ---
    if port1_is_service and not port2_is_service:
        # IP1 is the server (has the service port)
        return _result_ip1_server(record)
    if port2_is_service and not port1_is_service:
        # IP2 is the server
        return _result_ip2_server(record)

    # Both or neither port is a service port — try interface zone.
    # --- Signal 2: interface zone ---
    iface1_ext = _is_external_interface(record.interface1)
    iface2_ext = _is_external_interface(record.interface2)

    if iface1_ext and not iface2_ext:
        # IP1 is on the external (server) side
        return _result_ip1_server(record)
    if iface2_ext and not iface1_ext:
        # IP2 is on the external side
        return _result_ip2_server(record)

    # --- Signal 3: flag 'O' for outbound ---
    if "O" in record.flag.upper():
        # Outbound from FW perspective: ip2 → ip1 (client → server)
        # ip1 is on the internet side (server/dst)
        return _result_ip1_server(record)

    # --- Signal 4: fallback UNKNOWN ---
    return DirectionResult(
        direction=DirectionLabel.UNKNOWN,
        src_ip=record.ip1,
        dst_ip=record.ip2,
        service_port=record.port1,
        client_port=record.port2,
    )


# -- helpers ----------------------------------------------------------------

def _result_ip1_server(record: ExcelTrafficRecord) -> DirectionResult:
    """Build result where IP1 is the server (dst) and IP2 is the client (src).

    When IP1 is on the external / internet side and is the server,
    traffic flows from internal client (IP2) to external server (IP1)
    → direction is OUTBOUND from the firewall's perspective.
    """
    return DirectionResult(
        direction=DirectionLabel.OUTBOUND,
        src_ip=record.ip2,
        dst_ip=record.ip1,
        service_port=record.port1,
        client_port=record.port2,
    )


def _result_ip2_server(record: ExcelTrafficRecord) -> DirectionResult:
    """Build result where IP2 is the server (dst) and IP1 is the client (src).

    When IP2 is the server and IP1 is the client on the external side,
    traffic flows from external client (IP1) into internal server (IP2)
    → direction is INBOUND.
    """
    return DirectionResult(
        direction=DirectionLabel.INBOUND,
        src_ip=record.ip1,
        dst_ip=record.ip2,
        service_port=record.port2,
        client_port=record.port1,
    )
