"""Analyze stage: Stage 1 of the pipeline.

Queries pre-aggregated DuckDB statistics and calls the LLM to produce
a structured TrafficAnalysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.prompts.analyze import (
    ANALYZE_SYSTEM_PROMPT,
    format_analyze_user_message,
)
from policyfoundry.pipeline.schema import TrafficAnalysis
from policyfoundry.storage.queries import (
    denied_flows,
    top_talkers,
    traffic_by_protocol,
    traffic_summary,
)

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

    from policyfoundry.pipeline.graph import PipelineContext
    from policyfoundry.pipeline.state import PipelineState


async def analyze_stage(state: PipelineState, runtime: Runtime[PipelineContext]) -> dict[str, Any]:
    """Stage 1: Analyze traffic patterns from DuckDB pre-aggregated stats.

    Queries all 4 DuckDB analytics functions and passes results to the LLM
    for structured traffic analysis.
    """
    try:
        ctx = runtime.context
        data_dir = ctx.data_dir

        # Query all DuckDB analytics
        summary = await traffic_summary(data_dir)
        talkers = await top_talkers(20, data_dir)
        denied = await denied_flows(data_dir)
        protocols = await traffic_by_protocol(data_dir)

        # Format user message with all query results
        user_message = format_analyze_user_message(
            summary, talkers, denied, protocols,
        )

        messages = [
            {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Call LLM with structured output
        analysis = await ctx.llm_client.complete(
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
