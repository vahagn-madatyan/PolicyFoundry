"""Rich terminal formatter for pipeline results.

Renders a full pipeline report with summary panel, traffic analysis,
security assessment, proposal details, risk-colored decision table,
and optional token usage footer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)

if TYPE_CHECKING:
    from policyfoundry.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

RISK_COLORS: dict[str, str] = {
    "LOW": "green",
    "MEDIUM": "yellow",
    "HIGH": "red",
    "CRITICAL": "bold red",
}


def risk_text(level: str) -> Text:
    """Create a Rich Text with risk-appropriate color."""
    style = RISK_COLORS.get(level, "white")
    return Text(level, style=style)


def render_summary(state: dict[str, Any], console: Console) -> None:
    """Render the pipeline run summary panel."""
    run_id = state.get("run_id", "unknown")
    started_at = state.get("started_at", "unknown")
    sg_ids = state.get("sg_ids", "unknown")
    current_stage = state.get("current_stage", "unknown")

    lines = [
        f"Run ID:    {run_id}",
        f"Started:   {started_at}",
        f"Stage:     {current_stage}",
        f"SG IDs:    {', '.join(sg_ids) if sg_ids else 'N/A'}",
    ]
    panel = Panel(
        "\n".join(lines),
        title="Pipeline Summary",
        border_style="blue",
    )
    console.print(panel)


def render_traffic_analysis(analysis: TrafficAnalysis, console: Console) -> None:
    """Render traffic analysis section."""
    console.print("\n[bold]Traffic Analysis[/bold]")
    console.print("  ", analysis.summary)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Total Flows", f"{analysis.total_flows:,}")
    table.add_row("Unique Sources", f"{analysis.unique_sources:,}")
    table.add_row("Unique Destinations", f"{analysis.unique_destinations:,}")

    talkers: list[dict[str, Any]] = analysis.top_talkers[:5]
    talkers_str = ", ".join(str(t) for t in talkers) if talkers else "N/A"
    table.add_row("Top Talkers", talkers_str)

    console.print(table)


def render_security_assessment(assessment: SecurityAssessment, console: Console) -> None:
    """Render security assessment section."""
    console.print("\n[bold]Security Assessment[/bold]")

    risk_str = str(assessment.overall_risk)
    risk_styled = risk_text(risk_str)
    console.print("  Overall Risk: ", risk_styled)

    scores: list[dict[str, Any]] = assessment.risk_scores
    score_table = Table(show_header=True, header_style="bold cyan")
    score_table.add_column("Category")
    score_table.add_column("Score", justify="right")
    score_table.add_column("Description")

    for score in scores:
        score_table.add_row(
            score.get("category", ""),
            f"{score.get('score', 0):.2f}",
            score.get("description", ""),
        )
    console.print(score_table)

    gaps: list[dict[str, Any]] = assessment.rule_gaps
    if gaps:
        console.print("  [bold]Rule Gaps:[/bold]")
        for gap in gaps:
            console.print(f"    • [{gap.get('severity', 'UNKNOWN')}] {gap}")

    if assessment.compliance_findings:
        console.print("  [bold]Compliance Findings:[/bold]")
        for finding in assessment.compliance_findings:
            console.print(f"    • {finding}")


def render_proposals(proposals: list[PolicyProposal], console: Console) -> None:
    """Render policy proposals section."""
    console.print("\n[bold]Policy Proposals[/bold]")

    if not proposals:
        console.print("  No proposals generated.")
        return

    for proposal in proposals:
        risk_str = str(proposal.risk_level)
        risk_styled = risk_text(risk_str)

        console.print(f"\n  [bold]{proposal.proposal_id}[/bold]")
        console.print(f"    Rule:          {proposal.rule.name}")
        console.print(f"    Justification: {proposal.justification}")
        console.print("    Risk Level:    ", risk_styled)
        console.print(f"    Confidence:    {proposal.confidence:.0%}")


def render_decisions(decisions: list[RuleDecision], console: Console) -> None:
    """Render decisions table with risk-colored risk_level cells."""
    console.print("\n[bold]Decisions[/bold]")

    if not decisions:
        console.print("  No decisions generated.")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Decision ID")
    table.add_column("Proposal ID")
    table.add_column("Action")
    table.add_column("Risk Level")
    table.add_column("Reason", overflow="fold")
    table.add_column("Approval Req.")

    for decision in decisions:
        risk_str = str(decision.risk_level)
        risk_styled = risk_text(risk_str)

        table.add_row(
            str(decision.decision_id),
            str(decision.proposal_id),
            str(decision.action),
            risk_styled,
            str(decision.reason),
            "Yes" if decision.approval_required else "No",
        )

    console.print(table)


def render_token_usage(token_data: dict[str, Any] | None, console: Console) -> None:
    """Render token usage footer, or N/A if absent."""
    console.print("\n[bold]Token Usage[/bold]")

    if token_data is None:
        console.print("  N/A")
        return

    prompt = token_data.get("prompt_tokens", 0)
    completion = token_data.get("completion_tokens", 0)
    total = token_data.get("total_tokens", 0)
    cost = token_data.get("total_cost", 0.0)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Prompt Tokens", f"{prompt:,}")
    table.add_row("Completion Tokens", f"{completion:,}")
    table.add_row("Total Tokens", f"{total:,}")
    table.add_row("Cost", f"${cost:.4f}")

    console.print(table)


def format_rich(state: PipelineState, *, console: Console | None = None) -> None:
    """Render a full pipeline report to the terminal using Rich.

    Renders six sections: summary panel, traffic analysis, security
    assessment, proposals, decisions (risk-colored table), and token
    usage footer.

    Gracefully handles missing stage data — sections with reconstruction
    errors are skipped with a log warning rather than crashing.

    Args:
        state: A :class:`PipelineState` dict from pipeline execution.
        console: Optional Rich Console instance. Defaults to ``Console()``
            (auto-detect TTY).
    """
    if console is None:
        console = Console()

    raw: dict[str, Any] = dict(state)

    # Summary always renders
    render_summary(raw, console)

    # Traffic analysis
    try:
        analysis_data = raw.get("analysis")
        if analysis_data is not None:
            analysis = TrafficAnalysis.model_validate(analysis_data)
            render_traffic_analysis(analysis, console)
    except Exception:
        logger.warning("Failed to render traffic analysis section", exc_info=True)
        console.print("[yellow]⚠ Failed to render traffic analysis[/yellow]")

    # Security assessment
    try:
        assessment_data = raw.get("assessment")
        if assessment_data is not None:
            assessment = SecurityAssessment.model_validate(assessment_data)
            render_security_assessment(assessment, console)
    except Exception:
        logger.warning("Failed to render security assessment section", exc_info=True)
        console.print("[yellow]⚠ Failed to render security assessment[/yellow]")

    # Proposals
    try:
        proposals_data = raw.get("proposals")
        proposals: list[PolicyProposal] = []
        if proposals_data is not None:
            proposals = [PolicyProposal.model_validate(p) for p in proposals_data]
        render_proposals(proposals, console)
    except Exception:
        logger.warning("Failed to render proposals section", exc_info=True)
        console.print("[yellow]⚠ Failed to render proposals[/yellow]")

    # Decisions
    try:
        decisions_data = raw.get("decisions")
        decisions: list[RuleDecision] = []
        if decisions_data is not None:
            decisions = [RuleDecision.model_validate(d) for d in decisions_data]
        render_decisions(decisions, console)
    except Exception:
        logger.warning("Failed to render decisions section", exc_info=True)
        console.print("[yellow]⚠ Failed to render decisions[/yellow]")

    # Token usage
    render_token_usage(raw.get("token_usage"), console)
