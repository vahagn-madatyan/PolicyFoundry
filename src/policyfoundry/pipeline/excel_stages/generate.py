"""Excel generate stage: Stage 3 of the Excel pipeline.

Reads assessment + analysis from state, gets adapter capabilities
and subnet_groups, calls the LLM to produce vendor-neutral
PolicyProposals with SubnetGroup context for efficient CIDR rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from policyfoundry.pipeline.excel_prompts.generate import (
    EXCEL_GENERATE_SYSTEM_PROMPT,
    format_excel_generate_user_message,
)
from policyfoundry.pipeline.schema import PolicyProposal

if TYPE_CHECKING:
    from policyfoundry.pipeline.excel_state import ExcelPipelineState

_MAX_PROPOSALS = 20


class PolicyProposalList(BaseModel):
    """Wrapper model for LLM structured output of proposals."""

    proposals: list[PolicyProposal]


async def excel_generate_stage(
    state: ExcelPipelineState,
    runtime: Any,
) -> dict[str, Any]:
    """Stage 3: Generate policy proposals from security assessment.

    Reads the SecurityAssessment, TrafficAnalysis, and SubnetGroup
    candidates from state. Calls the LLM with adapter capabilities
    and subnet group context to produce structured PolicyProposals.

    Args:
        state: Current pipeline state with assessment, analysis,
            and subnet_groups from prior stages.
        runtime: LangGraph runtime with ``context`` carrying
            ``llm_client`` and ``adapter``.

    Returns:
        Dict with ``proposals`` (list of PolicyProposal dicts) and
        ``current_stage`` set to ``"generate"``.
    """
    ctx = runtime.context
    assessment = state.get("assessment", {})
    analysis = state.get("analysis", {})
    subnet_groups = state.get("subnet_groups", [])

    # Get adapter capabilities
    capabilities = ctx.adapter.capabilities()

    # Format user message with subnet group data
    user_message = format_excel_generate_user_message(
        assessment, capabilities, analysis, subnet_groups,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": EXCEL_GENERATE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Call LLM with wrapper model for list output (D025: temperature=0.3)
    result = await ctx.llm_client.complete(
        messages, PolicyProposalList, temperature=0.3, stage="generate",
    )

    # Limit and serialize proposals
    proposals = result.proposals[:_MAX_PROPOSALS]

    return {
        "proposals": [p.model_dump() for p in proposals],
        "current_stage": "generate",
    }
