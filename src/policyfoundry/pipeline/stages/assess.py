"""Assess stage: Stage 2 of the pipeline.

Compares TrafficAnalysis patterns against current firewall rules
and calls the LLM to produce a SecurityAssessment with rule gaps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from policyfoundry.pipeline.prompts.assess import (
    ASSESS_SYSTEM_PROMPT,
    format_assess_user_message,
)
from policyfoundry.pipeline.schema import SecurityAssessment

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

    from policyfoundry.pipeline.graph import PipelineContext
    from policyfoundry.pipeline.state import PipelineState


async def assess_stage(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    """Stage 2: Assess security risks from traffic analysis.

    Reads the TrafficAnalysis from state, fetches current rules from
    the adapter, and calls the LLM for risk assessment.
    """
    ctx = runtime.context
    analysis = state.get("analysis", {})

    # Fetch current firewall rules
    current_rules = await ctx.adapter.get_rules()

    # Format user message
    user_message = format_assess_user_message(
        analysis, current_rules,
    )

    messages = [
        {"role": "system", "content": ASSESS_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Call LLM with structured output
    assessment = await ctx.llm_client.complete(
        messages, SecurityAssessment, temperature=0.1, stage="assess",
    )

    return {
        "assessment": assessment.model_dump(),
        "current_stage": "assess",
    }
