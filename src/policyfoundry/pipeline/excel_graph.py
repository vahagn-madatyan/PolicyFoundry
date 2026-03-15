"""LangGraph StateGraph for the Excel analysis pipeline.

Defines ExcelPipelineContext (runtime dependency injection) and builds
the 5-node linear StateGraph: analyze → assess → generate → validate → decide.

Mirrors M01's graph.py pattern but uses ExcelPipelineState (inline data)
and ExcelPipelineContext (aggregated_flows + subnet_groups instead of data_dir).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from policyfoundry.pipeline.excel_stages import (
    excel_analyze_stage,
    excel_assess_stage,
    excel_decide_stage,
    excel_generate_stage,
    excel_validate_proposals,
)
from policyfoundry.pipeline.excel_state import ExcelPipelineState

if TYPE_CHECKING:
    from policyfoundry.adapters.base import FirewallAdapter
    from policyfoundry.analysis.models import AggregatedFlow, SubnetGroup
    from policyfoundry.pipeline.llm import LLMClient


@dataclass
class ExcelPipelineContext:
    """Runtime dependencies injected into Excel pipeline stages.

    Passed to the compiled graph via ``context=`` parameter at
    invocation time. Stage functions access these through
    ``runtime.context``.

    Unlike M01's PipelineContext (which carries data_dir for DuckDB),
    this carries pre-computed domain models inline — Excel datasets are
    small enough to hold in memory.
    """

    llm_client: LLMClient
    adapter: FirewallAdapter
    aggregated_flows: list[AggregatedFlow]
    subnet_groups: list[SubnetGroup]


def build_excel_pipeline() -> Any:
    """Build and compile the 5-stage linear Excel pipeline graph.

    Returns:
        A compiled LangGraph ``CompiledStateGraph`` wiring analyze → assess →
        generate → validate → decide in sequence. Return typed as ``Any``
        to work around LangGraph's invariant generic parameters in strict
        mode (same pattern as M01's ``build_pipeline()``).
    """
    builder = StateGraph(
        ExcelPipelineState, context_schema=ExcelPipelineContext,
    )

    # Register stage nodes
    builder.add_node("analyze", excel_analyze_stage)
    builder.add_node("assess", excel_assess_stage)
    builder.add_node("generate", excel_generate_stage)
    builder.add_node("validate", excel_validate_proposals)
    builder.add_node("decide", excel_decide_stage)

    # Wire linear edges
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "assess")
    builder.add_edge("assess", "generate")
    builder.add_edge("generate", "validate")
    builder.add_edge("validate", "decide")
    builder.add_edge("decide", END)

    return builder.compile()
