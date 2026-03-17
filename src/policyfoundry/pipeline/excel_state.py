"""ExcelPipelineState: LangGraph state container for Excel analysis pipeline.

Mirrors M01's PipelineState pattern but carries inline aggregated flow data
(the Excel path produces small enough datasets to store in state directly)
plus full S03 pipeline stage outputs.
"""

from typing import TypedDict


class ExcelPipelineState(TypedDict, total=False):
    """LangGraph state for the Excel traffic analysis pipeline.

    All fields optional (total=False) — each stage populates its outputs.
    This TypedDict defines the S03→S04 boundary contract.

    Fields:
        run_id: Unique pipeline execution identifier.
        started_at: ISO-8601 timestamp of pipeline start.
        current_stage: Name of the currently executing stage.
        aggregated_flows: S02 AggregatedFlow records as dicts.
        subnet_groups: S02 SubnetGroup records as dicts.
        analysis: S03 analyze stage output (traffic patterns, risks).
        assessment: S03 assess stage output (risk scores, recommendations).
        proposals: S03 generate stage output (proposed firewall rules).
        decisions: S03 decide stage output (accepted/rejected proposals).
        token_usage: Per-stage LLM token consumption tracking.
    """

    run_id: str
    started_at: str
    current_stage: str
    aggregated_flows: list[dict]
    subnet_groups: list[dict]
    analysis: dict
    assessment: dict
    proposals: list[dict]
    decisions: list[dict]
    token_usage: dict
