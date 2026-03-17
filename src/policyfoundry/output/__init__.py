"""Output formatting and data models for pipeline results.

Exports:
    format_rich: Rich terminal formatter with risk-colored output (M01).
    format_json: JSON serialization of M01 pipeline results.
    format_excel_rich: Rich terminal formatter for Excel pipeline results.
    format_excel_json: JSON serialization of Excel pipeline results.
    PipelineResult: Pydantic model for typed M01 result serialization.
    ExcelPipelineResult: Pydantic model for typed Excel result serialization.
    TokenUsage: Dataclass for accumulating LLM token usage and cost.
    RISK_COLORS: Risk level to Rich color/style mapping.
    Shared renderers: render_traffic_analysis, render_security_assessment,
        render_proposals, render_decisions, render_token_usage, risk_text.
"""

from policyfoundry.output.excel_json_output import format_excel_json
from policyfoundry.output.excel_rich_output import format_excel_rich
from policyfoundry.output.json_output import format_json
from policyfoundry.output.models import ExcelPipelineResult, PipelineResult, TokenUsage
from policyfoundry.output.rich_output import (
    RISK_COLORS,
    format_rich,
    render_decisions,
    render_proposals,
    render_security_assessment,
    render_token_usage,
    render_traffic_analysis,
    risk_text,
)

__all__ = [
    "ExcelPipelineResult",
    "PipelineResult",
    "RISK_COLORS",
    "TokenUsage",
    "format_excel_json",
    "format_excel_rich",
    "format_json",
    "format_rich",
    "render_decisions",
    "render_proposals",
    "render_security_assessment",
    "render_token_usage",
    "render_traffic_analysis",
    "risk_text",
]
