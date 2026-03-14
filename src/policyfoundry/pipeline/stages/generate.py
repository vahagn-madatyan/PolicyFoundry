"""Generate stage: Stage 3 of the pipeline.

Reads SecurityAssessment and adapter capabilities, calls the LLM
to produce vendor-neutral PolicyProposals with impact analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from policyfoundry.pipeline.prompts.generate import (
    GENERATE_SYSTEM_PROMPT,
    format_generate_user_message,
)
from policyfoundry.pipeline.schema import PolicyProposal

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

    from policyfoundry.pipeline.graph import PipelineContext
    from policyfoundry.pipeline.state import PipelineState

_MAX_PROPOSALS = 20


class PolicyProposalList(BaseModel):
    """Wrapper model for LLM structured output of proposals."""

    proposals: list[PolicyProposal]


async def generate_stage(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    """Stage 3: Generate policy proposals from security assessment.

    Reads the SecurityAssessment and adapter capabilities, calls the LLM
    to produce structured PolicyProposals.
    """
    ctx = runtime.context
    assessment = state.get("assessment", {})
    analysis = state.get("analysis", {})

    # Get adapter capabilities
    capabilities = ctx.adapter.capabilities()

    # Format user message
    user_message = format_generate_user_message(
        assessment, capabilities, analysis,
    )

    messages = [
        {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Call LLM with wrapper model for list output
    result = await ctx.llm_client.complete(
        messages, PolicyProposalList, temperature=0.3,
    )

    # Limit and serialize proposals
    proposals = result.proposals[:_MAX_PROPOSALS]

    return {
        "proposals": [p.model_dump() for p in proposals],
        "current_stage": "generate",
    }
