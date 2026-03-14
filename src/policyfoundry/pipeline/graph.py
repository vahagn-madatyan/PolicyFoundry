"""LangGraph StateGraph definition for the pipeline.

Defines PipelineContext (runtime dependency injection) and builds
the 5-node linear StateGraph: analyze -> assess -> generate ->
validate -> decide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from policyfoundry.pipeline.stages.analyze import analyze_stage
from policyfoundry.pipeline.stages.assess import assess_stage
from policyfoundry.pipeline.stages.decide import decide_stage
from policyfoundry.pipeline.stages.generate import generate_stage
from policyfoundry.pipeline.stages.validate import validate_proposals
from policyfoundry.pipeline.state import PipelineState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from policyfoundry.adapters.base import FirewallAdapter
    from policyfoundry.pipeline.llm import LLMClient


@dataclass
class PipelineContext:
    """Runtime dependencies injected into pipeline stages.

    Passed to the compiled graph via ``context=`` parameter at
    invocation time. Stage functions access these through
    ``runtime.context``.
    """

    llm_client: LLMClient
    adapter: FirewallAdapter
    data_dir: str


def build_pipeline() -> CompiledStateGraph:
    """Build and compile the 5-stage linear pipeline graph.

    Returns:
        A compiled LangGraph StateGraph wiring analyze -> assess ->
        generate -> validate -> decide in sequence.
    """
    builder = StateGraph(PipelineState, context_schema=PipelineContext)

    # Register stage nodes
    builder.add_node("analyze", analyze_stage)
    builder.add_node("assess", assess_stage)
    builder.add_node("generate", generate_stage)
    builder.add_node("validate", validate_proposals)
    builder.add_node("decide", decide_stage)

    # Wire linear edges
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "assess")
    builder.add_edge("assess", "generate")
    builder.add_edge("generate", "validate")
    builder.add_edge("validate", "decide")
    builder.add_edge("decide", END)

    return builder.compile()
