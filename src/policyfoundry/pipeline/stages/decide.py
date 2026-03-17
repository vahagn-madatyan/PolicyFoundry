"""Decide stage: Stage 4 of the pipeline.

Reviews all validated proposals in a single LLM call with
cross-proposal reasoning, assigning risk levels and actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from policyfoundry.pipeline.prompts.decide import (
    DECIDE_SYSTEM_PROMPT,
    format_decide_user_message,
)
from policyfoundry.pipeline.schema import RuleDecision

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

    from policyfoundry.pipeline.graph import PipelineContext
    from policyfoundry.pipeline.state import PipelineState


class RuleDecisionList(BaseModel):
    """Wrapper model for LLM structured output of decisions."""

    decisions: list[RuleDecision]


async def decide_stage(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    """Stage 4: Make rule decisions on validated proposals.

    Processes all proposals in a single LLM call for cross-proposal
    reasoning and conflict detection.
    """
    ctx = runtime.context
    proposals = state.get("proposals", [])

    # Short-circuit if no proposals (D024)
    if not proposals:
        return {
            "decisions": [],
            "current_stage": "decide",
        }

    # Format user message with proposal summaries
    user_message = format_decide_user_message(proposals)

    messages = [
        {"role": "system", "content": DECIDE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Call LLM with wrapper model for list output
    result = await ctx.llm_client.complete(
        messages, RuleDecisionList, temperature=0.1, stage="decide",
    )

    return {
        "decisions": [d.model_dump() for d in result.decisions],
        "current_stage": "decide",
    }
