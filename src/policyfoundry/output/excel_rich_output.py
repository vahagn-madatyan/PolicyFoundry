"""Rich terminal formatter for Excel pipeline results.

Renders an Excel-specific summary panel (source type, flow counts,
direction breakdown, subnet candidates), then reuses shared renderers
for traffic analysis, security assessment, proposals, decisions, and
token usage.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from policyfoundry.output.rich_output import (
    render_decisions,
    render_proposals,
    render_security_assessment,
    render_token_usage,
    render_traffic_analysis,
)
from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)

if TYPE_CHECKING:
    from policyfoundry.pipeline.excel_state import ExcelPipelineState

logger = logging.getLogger(__name__)


def _render_excel_summary(state: dict[str, Any], console: Console) -> None:
    """Render Excel-specific pipeline summary panel."""
    run_id = state.get("run_id", "unknown")
    started_at = state.get("started_at", "unknown")
    current_stage = state.get("current_stage", "unknown")

    aggregated_flows: list[dict[str, Any]] = state.get("aggregated_flows", [])
    subnet_groups: list[dict[str, Any]] = state.get("subnet_groups", [])

    total_flows = len(aggregated_flows)

    # Direction breakdown
    inbound = sum(1 for f in aggregated_flows if f.get("direction") == "INBOUND")
    outbound = sum(1 for f in aggregated_flows if f.get("direction") == "OUTBOUND")
    unknown = total_flows - inbound - outbound

    direction_parts: list[str] = []
    if inbound:
        direction_parts.append(f"{inbound} inbound")
    if outbound:
        direction_parts.append(f"{outbound} outbound")
    if unknown:
        direction_parts.append(f"{unknown} unknown")
    direction_str = ", ".join(direction_parts) if direction_parts else "none"

    lines = [
        f"Run ID:              {run_id}",
        f"Started:             {started_at}",
        f"Stage:               {current_stage}",
        f"Source:               Excel traffic export",
        f"Aggregated Flows:    {total_flows}",
        f"Direction Breakdown: {direction_str}",
        f"Subnet Candidates:   {len(subnet_groups)}",
    ]
    panel = Panel(
        "\n".join(lines),
        title="Excel Pipeline Summary",
        border_style="cyan",
    )
    console.print(panel)


def format_excel_rich(
    state: ExcelPipelineState,
    *,
    console: Console | None = None,
) -> None:
    """Render a full Excel pipeline report to the terminal using Rich.

    Renders an Excel-specific summary panel, then reuses shared renderers
    for traffic analysis, security assessment, proposals, decisions, and
    token usage.

    Gracefully handles missing stage data — sections with reconstruction
    errors are skipped with a log warning rather than crashing.

    Args:
        state: An :class:`ExcelPipelineState` dict from pipeline execution.
        console: Optional Rich Console instance. Defaults to ``Console()``
            (auto-detect TTY).
    """
    if console is None:
        console = Console()

    raw: dict[str, Any] = dict(state)

    # Excel-specific summary panel
    _render_excel_summary(raw, console)

    # Traffic analysis (shared renderer)
    try:
        analysis_data = raw.get("analysis")
        if analysis_data is not None:
            analysis = TrafficAnalysis.model_validate(analysis_data)
            render_traffic_analysis(analysis, console)
    except Exception:
        logger.warning("Failed to render traffic analysis section", exc_info=True)
        console.print("[yellow]⚠ Failed to render traffic analysis[/yellow]")

    # Security assessment (shared renderer)
    try:
        assessment_data = raw.get("assessment")
        if assessment_data is not None:
            assessment = SecurityAssessment.model_validate(assessment_data)
            render_security_assessment(assessment, console)
    except Exception:
        logger.warning("Failed to render security assessment section", exc_info=True)
        console.print("[yellow]⚠ Failed to render security assessment[/yellow]")

    # Proposals (shared renderer)
    try:
        proposals_data = raw.get("proposals")
        proposals: list[PolicyProposal] = []
        if proposals_data is not None:
            proposals = [PolicyProposal.model_validate(p) for p in proposals_data]
        render_proposals(proposals, console)
    except Exception:
        logger.warning("Failed to render proposals section", exc_info=True)
        console.print("[yellow]⚠ Failed to render proposals[/yellow]")

    # Decisions (shared renderer)
    try:
        decisions_data = raw.get("decisions")
        decisions: list[RuleDecision] = []
        if decisions_data is not None:
            decisions = [RuleDecision.model_validate(d) for d in decisions_data]
        render_decisions(decisions, console)
    except Exception:
        logger.warning("Failed to render decisions section", exc_info=True)
        console.print("[yellow]⚠ Failed to render decisions[/yellow]")

    # Token usage (shared renderer)
    render_token_usage(raw.get("token_usage"), console)
