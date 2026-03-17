"""Excel analyze stage: Stage 1 of the Excel pipeline.

Reads pre-aggregated flow data from state, computes compact summary
statistics via the pre-summarizer, and calls the LLM to produce a
structured TrafficAnalysis.

Unlike M01's analyze stage which queries DuckDB, this stage works
entirely from in-state data (Excel datasets are small enough to carry
inline).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from policyfoundry.analysis.models import AggregatedFlow, SubnetGroup
from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.excel_prompts.analyze import (
    EXCEL_ANALYZE_SYSTEM_PROMPT,
    format_excel_analyze_user_message,
)
from policyfoundry.pipeline.excel_summarizer import summarize_flows
from policyfoundry.pipeline.schema import TrafficAnalysis

if TYPE_CHECKING:
    from policyfoundry.pipeline.excel_state import ExcelPipelineState


async def excel_analyze_stage(
    state: ExcelPipelineState,
    runtime: Any,
) -> dict[str, Any]:
    """Stage 1: Analyze traffic patterns from pre-summarized Excel data.

    Reads aggregated_flows and subnet_groups from pipeline state,
    computes compact statistics via ``summarize_flows()``, and passes
    the result to the LLM for structured traffic analysis.

    Args:
        state: Current pipeline state with aggregated_flows and
            subnet_groups populated by the ingestion stage.
        runtime: LangGraph runtime with ``context`` carrying
            ``llm_client`` and ``adapter``.

    Returns:
        Dict with ``analysis`` (TrafficAnalysis as dict) and
        ``current_stage`` set to ``"analyze"``.
    """
    try:
        ctx = runtime.context

        # Reconstruct domain models from state dicts
        raw_flows = state.get("aggregated_flows", [])
        raw_subnets = state.get("subnet_groups", [])

        flows = [AggregatedFlow(**f) for f in raw_flows]
        subnet_groups = [SubnetGroup(**sg) for sg in raw_subnets]

        # Pre-summarize to compact stats (< 3K tokens)
        summary = summarize_flows(flows, subnet_groups)

        # Format user message from summary
        user_message = format_excel_analyze_user_message(summary)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": EXCEL_ANALYZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Call LLM with structured output
        analysis: TrafficAnalysis = await ctx.llm_client.complete(
            messages, TrafficAnalysis, temperature=0.1, stage="analyze",
        )

        return {
            "analysis": analysis.model_dump(),
            "current_stage": "analyze",
        }
    except PipelineError:
        raise
    except Exception as e:
        raise PipelineError(str(e), details={"stage": "analyze"}) from e
