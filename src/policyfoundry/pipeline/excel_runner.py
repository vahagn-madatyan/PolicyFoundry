"""Excel pipeline runner: async entry point with error handling.

Provides run_excel_pipeline() which aggregates raw records, builds
the graph, creates context, and executes the pipeline with PipelineError
wrapping on failure.

Token usage is NOT attached inside the runner — the CLI layer calls
llm_client.get_usage() after execution (matching M01 pattern).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from policyfoundry.adapters.null import NullAdapter
from policyfoundry.analysis.aggregator import aggregate_flows
from policyfoundry.analysis.subnet import group_to_subnets
from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.excel_graph import (
    ExcelPipelineContext,
    build_excel_pipeline,
)

if TYPE_CHECKING:
    from policyfoundry.adapters.base import FirewallAdapter
    from policyfoundry.ingestion.excel_schema import ExcelTrafficRecord
    from policyfoundry.pipeline.excel_state import ExcelPipelineState
    from policyfoundry.pipeline.llm import LLMClient


async def run_excel_pipeline(
    llm_client: LLMClient,
    records: list[ExcelTrafficRecord],
    adapter: FirewallAdapter | None = None,
) -> ExcelPipelineState:
    """Run the full Excel analysis pipeline and return the final state.

    Aggregates raw traffic records, groups to subnet candidates, then
    executes the 5-stage LangGraph pipeline (analyze → assess → generate
    → validate → decide).

    Args:
        llm_client: Configured LLM client for structured output.
        records: Raw Excel traffic records to analyze.
        adapter: Firewall adapter for rule validation. Defaults to
            NullAdapter() (no-FW mode) when None.

    Returns:
        Final ExcelPipelineState dict after all stages complete.

    Raises:
        PipelineError: On any pipeline stage failure, with the
            original exception chained and stage name in details.
    """
    if adapter is None:
        adapter = NullAdapter()

    # Prepare data: aggregate flows and group to subnets
    aggregated_flows = aggregate_flows(records)
    subnet_groups = group_to_subnets(aggregated_flows)

    context = ExcelPipelineContext(
        llm_client=llm_client,
        adapter=adapter,
        aggregated_flows=aggregated_flows,
        subnet_groups=subnet_groups,
    )

    initial_state: dict[str, object] = {
        "run_id": str(uuid.uuid4()),
        "started_at": datetime.now(tz=UTC).isoformat(),
        "current_stage": "starting",
        "aggregated_flows": [f.model_dump() for f in aggregated_flows],
        "subnet_groups": [sg.model_dump() for sg in subnet_groups],
    }

    pipeline = build_excel_pipeline()

    try:
        result = await pipeline.ainvoke(initial_state, context=context)
    except PipelineError:
        raise
    except Exception as exc:
        stage = initial_state.get("current_stage", "unknown")
        raise PipelineError(
            f"Excel pipeline failed at stage: {stage}",
            error_code="PIPELINE_STAGE_FAILED",
            details={"stage": str(stage), "error": str(exc)},
        ) from exc

    return result  # type: ignore[return-value]
