"""PipelineState TypedDict for LangGraph state management.

LangGraph state container. Uses TypedDict (not Pydantic) for LangGraph
compatibility. Stores flow log references as strings to prevent checkpoint
bloat.
"""

from typing import TypedDict


class PipelineState(TypedDict, total=False):
    """LangGraph pipeline state container.

    All fields are optional (total=False) to allow partial state construction
    during pipeline execution. Each stage populates its relevant fields.

    Flow log data is referenced by path (string), not stored inline, to
    prevent LangGraph checkpoint serialization from bloating with raw log data.
    """

    run_id: str
    started_at: str
    current_stage: str
    flow_log_path: str
    sg_ids: list[str]
    analysis: dict
    assessment: dict
    proposals: list[dict]
    decisions: list[dict]
    token_usage: dict
