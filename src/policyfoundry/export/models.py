"""Export data models: ChangeRequestEntry and flattening logic.

Converts pipeline state (proposals + decisions) into flat, display-ready
rows for xlsx/pdf export.
"""

from __future__ import annotations

from pydantic import BaseModel

from policyfoundry.adapters.schema import NetworkEndpoint, PortRange
from policyfoundry.output.models import ExcelPipelineResult
from policyfoundry.pipeline.excel_state import ExcelPipelineState


class ChangeRequestEntry(BaseModel):
    """Single flattened row for a change request export.

    Each entry represents one decided rule proposal with all fields
    formatted as display-ready strings.
    """

    source: str
    destination: str
    port: str
    protocol: str
    direction: str
    action: str
    justification: str
    risk: str
    proposal_id: str
    approval_required: bool


def format_endpoints(endpoints: list[NetworkEndpoint]) -> str:
    """Format a list of NetworkEndpoints into a display string.

    Handles CIDRs, is_any, security_group_id, tag, and empty lists.

    Args:
        endpoints: List of NetworkEndpoint objects.

    Returns:
        Comma-separated string of endpoint identifiers, or ``"any"``
        for empty lists or is_any endpoints.
    """
    if not endpoints:
        return "any"

    parts: list[str] = []
    for ep in endpoints:
        if ep.is_any:
            parts.append("any")
        elif ep.cidr is not None:
            parts.append(ep.cidr)
        elif ep.security_group_id is not None:
            parts.append(ep.security_group_id)
        elif ep.tag is not None:
            # Format tag as "key=value" pairs
            tag_parts = [f"{k}={v}" for k, v in ep.tag.items()]
            parts.append(", ".join(tag_parts))
        else:
            parts.append("any")

    return ", ".join(parts)


def format_port_range(port_range: PortRange | None) -> str:
    """Format a PortRange into a display string.

    Args:
        port_range: PortRange with from_port/to_port, or None.

    Returns:
        Single port number, ``"from-to"`` range, or ``"any"`` for None.
    """
    if port_range is None:
        return "any"

    if port_range.from_port == port_range.to_port:
        return str(port_range.from_port)

    return f"{port_range.from_port}-{port_range.to_port}"


def flatten_to_entries(
    state: ExcelPipelineState,
) -> list[ChangeRequestEntry]:
    """Flatten pipeline state into export-ready ChangeRequestEntry rows.

    Uses ``ExcelPipelineResult.from_state()`` for typed reconstruction,
    pairs proposals with decisions by ``proposal_id``, and produces one
    entry per non-SKIP decision.

    Args:
        state: ExcelPipelineState dict from pipeline execution.

    Returns:
        List of ChangeRequestEntry, one per decided (non-SKIP) rule.
    """
    result = ExcelPipelineResult.from_state(state)

    # Index proposals by proposal_id for O(1) lookup
    proposal_map = {p.proposal_id: p for p in result.proposals}

    entries: list[ChangeRequestEntry] = []
    for decision in result.decisions:
        # Skip decisions with SKIP action
        if decision.action.upper() == "SKIP":
            continue

        proposal = proposal_map.get(decision.proposal_id)
        if proposal is None:
            # Decision references a proposal we don't have — skip gracefully
            continue

        rule = proposal.rule
        entries.append(
            ChangeRequestEntry(
                source=format_endpoints(rule.source),
                destination=format_endpoints(rule.destination),
                port=format_port_range(rule.port_range),
                protocol=rule.protocol,
                direction=rule.direction.value,
                action=decision.action,
                justification=proposal.justification,
                risk=decision.risk_level.value,
                proposal_id=decision.proposal_id,
                approval_required=decision.approval_required,
            )
        )

    return entries
