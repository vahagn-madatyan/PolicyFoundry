"""Excel assess stage: Stage 2 of the Excel pipeline.

Compares TrafficAnalysis against current firewall rules (empty with
NullAdapter) and calls the LLM to produce a SecurityAssessment that
infers likely existing rules from traffic patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from policyfoundry.pipeline.excel_prompts.assess import (
    EXCEL_ASSESS_SYSTEM_PROMPT,
    format_excel_assess_user_message,
)
from policyfoundry.pipeline.excel_summarizer import (
    format_flow_summary_message,
    summarize_flows,
)
from policyfoundry.pipeline.schema import SecurityAssessment

if TYPE_CHECKING:
    from policyfoundry.analysis.models import AggregatedFlow, SubnetGroup
    from policyfoundry.pipeline.excel_state import ExcelPipelineState


async def excel_assess_stage(
    state: ExcelPipelineState,
    runtime: Any,
) -> dict[str, Any]:
    """Stage 2: Assess security risks from traffic analysis.

    Reads the TrafficAnalysis from state, fetches current rules from
    the adapter (empty with NullAdapter), and includes a compact flow
    summary for additional context. The LLM infers likely existing
    rules from traffic patterns when no rules are available.

    Args:
        state: Current pipeline state with analysis from Stage 1
            and aggregated_flows from ingestion.
        runtime: LangGraph runtime with ``context`` carrying
            ``llm_client`` and ``adapter``.

    Returns:
        Dict with ``assessment`` (SecurityAssessment as dict) and
        ``current_stage`` set to ``"assess"``.
    """
    ctx = runtime.context
    analysis = state.get("analysis", {})

    # Fetch current firewall rules (empty list with NullAdapter)
    current_rules = await ctx.adapter.get_rules()

    # Build a compact flow summary for additional context in the prompt
    raw_flows = state.get("aggregated_flows", [])
    raw_subnets = state.get("subnet_groups", [])

    # Avoid importing at module level to keep TYPE_CHECKING clean
    from policyfoundry.analysis.models import AggregatedFlow, SubnetGroup

    flows = [AggregatedFlow(**f) for f in raw_flows]
    subnet_groups = [SubnetGroup(**sg) for sg in raw_subnets]
    flow_summary = summarize_flows(flows, subnet_groups)
    flow_summary_text = format_flow_summary_message(flow_summary)

    # Format user message with analysis + rules
    user_message = format_excel_assess_user_message(analysis, current_rules)

    # Append flow summary as additional context
    user_content = (
        f"{user_message}\n\n"
        f"Additional context — compact flow summary:\n{flow_summary_text}"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": EXCEL_ASSESS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # Call LLM with structured output
    assessment: SecurityAssessment = await ctx.llm_client.complete(
        messages, SecurityAssessment, temperature=0.1, stage="assess",
    )

    return {
        "assessment": assessment.model_dump(),
        "current_stage": "assess",
    }
