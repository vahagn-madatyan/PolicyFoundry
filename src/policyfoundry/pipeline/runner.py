"""Pipeline runner: async entry point with error handling.

Provides run_pipeline() which builds the graph, creates context,
and executes the pipeline with PipelineError wrapping on failure.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.graph import PipelineContext, build_pipeline

if TYPE_CHECKING:
    from policyfoundry.adapters.base import FirewallAdapter
    from policyfoundry.pipeline.llm import LLMClient
    from policyfoundry.pipeline.state import PipelineState


async def run_pipeline(
    llm_client: LLMClient,
    adapter: FirewallAdapter,
    data_dir: str,
    sg_ids: list[str],
) -> PipelineState:
    """Run the full pipeline and return the final state.

    Builds a PipelineContext, creates the initial state with a unique
    run ID and timestamp, and executes the compiled LangGraph pipeline.

    Args:
        llm_client: Configured LLM client for structured output.
        adapter: Firewall adapter for rule fetching and validation.
        data_dir: Path to the flow log data directory.
        sg_ids: Security group IDs to analyze.

    Returns:
        Final PipelineState dict after all stages complete.

    Raises:
        PipelineError: On any pipeline stage failure, with the
            original exception chained.
    """
    context = PipelineContext(
        llm_client=llm_client,
        adapter=adapter,
        data_dir=data_dir,
    )

    initial_state = {
        "run_id": str(uuid.uuid4()),
        "started_at": datetime.now(tz=UTC).isoformat(),
        "current_stage": "starting",
        "flow_log_path": data_dir,
        "sg_ids": sg_ids,
    }

    pipeline = build_pipeline()

    try:
        result = await pipeline.ainvoke(initial_state, context=context)
    except PipelineError:
        raise
    except Exception as exc:
        stage = initial_state.get("current_stage", "unknown")
        raise PipelineError(
            f"Pipeline failed at stage: {stage}",
            error_code="PIPELINE_STAGE_FAILED",
            details={"stage": stage, "error": str(exc)},
        ) from exc

    return result
