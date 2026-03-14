"""Validate step: Adapter constraint filtering (non-LLM).

Filters proposals through adapter.validate() and removes invalid
ones before the Decide stage. Saves LLM tokens by preventing the
decision stage from evaluating impossible rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from policyfoundry.pipeline.schema import PolicyProposal

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

    from policyfoundry.pipeline.graph import PipelineContext
    from policyfoundry.pipeline.state import PipelineState


async def validate_proposals(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    """Validate proposals against adapter constraints.

    Non-LLM step that filters proposals through adapter.validate()
    and removes invalid ones before the Decide stage.
    """
    ctx = runtime.context
    proposals = state.get("proposals", [])

    # Get current rules for rule count
    current_rules = await ctx.adapter.get_rules()
    rule_count = len(current_rules)

    valid_proposals: list[dict[str, Any]] = []
    for proposal_dict in proposals:
        # Reconstruct typed model for validation
        proposal = PolicyProposal.model_validate(proposal_dict)
        result = await ctx.adapter.validate(
            proposal.rule, current_rule_count=rule_count,
        )

        if not result.valid:
            continue
        valid_proposals.append(proposal_dict)

    return {
        "proposals": valid_proposals,
        "current_stage": "validate",
    }
