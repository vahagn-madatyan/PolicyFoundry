"""Excel decide stage: Stage 5 of the Excel pipeline.

Reviews all validated proposals in a single LLM call with
cross-proposal reasoning, assigning risk levels and actions.
Excel-specific: only CREATE or SKIP (no UPDATE — no existing rules).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from policyfoundry.pipeline.excel_prompts.decide import (
    EXCEL_DECIDE_SYSTEM_PROMPT,
    format_excel_decide_user_message,
)
from policyfoundry.pipeline.schema import RuleDecision

if TYPE_CHECKING:
    from policyfoundry.pipeline.excel_state import ExcelPipelineState


class RuleDecisionList(BaseModel):
    """Wrapper model for LLM structured output of decisions."""

    decisions: list[RuleDecision]


async def excel_decide_stage(
    state: ExcelPipelineState,
    runtime: Any,
) -> dict[str, Any]:
    """Stage 5: Make rule decisions on validated proposals.

    Processes all proposals in a single LLM call for cross-proposal
    reasoning and conflict detection. Short-circuits on empty proposals
    (D024).

    Args:
        state: Current pipeline state with validated proposals.
        runtime: LangGraph runtime with ``context`` carrying
            ``llm_client``.

    Returns:
        Dict with ``decisions`` (list of RuleDecision dicts) and
        ``current_stage`` set to ``"decide"``.
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
    user_message = format_excel_decide_user_message(proposals)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": EXCEL_DECIDE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Call LLM with wrapper model for list output (temperature=0.1)
    result = await ctx.llm_client.complete(
        messages, RuleDecisionList, temperature=0.1, stage="decide",
    )

    return {
        "decisions": [d.model_dump() for d in result.decisions],
        "current_stage": "decide",
    }
