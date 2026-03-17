"""Excel validate step: Adapter constraint filtering (non-LLM).

Mirrors M01's validate stage exactly — filters proposals through
adapter.validate() and removes invalid ones. With NullAdapter this
passes all proposals through, preserving the seam for future adapters.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.schema import PolicyProposal

if TYPE_CHECKING:
    from policyfoundry.pipeline.excel_state import ExcelPipelineState

logger = logging.getLogger(__name__)


async def excel_validate_proposals(
    state: ExcelPipelineState,
    runtime: Any,
) -> dict[str, Any]:
    """Validate proposals against adapter constraints.

    Non-LLM step that filters proposals through adapter.validate()
    and removes invalid ones before the Decide stage. With NullAdapter,
    all proposals pass through.

    Args:
        state: Current pipeline state with proposals from generate stage.
        runtime: LangGraph runtime with ``context`` carrying ``adapter``.

    Returns:
        Dict with ``proposals`` (filtered list) and ``current_stage``
        set to ``"validate"``.
    """
    try:
        ctx = runtime.context
        proposals = state.get("proposals", [])

        # Get current rules for rule count (empty with NullAdapter)
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
                reasons = "; ".join(e.message for e in result.errors) or "validation failed"
                logger.warning("Rejected proposal %s: %s", proposal.proposal_id, reasons)
                continue
            valid_proposals.append(proposal_dict)

        return {
            "proposals": valid_proposals,
            "current_stage": "validate",
        }
    except PipelineError:
        raise
    except Exception as e:
        raise PipelineError(str(e), details={"stage": "validate"}) from e
