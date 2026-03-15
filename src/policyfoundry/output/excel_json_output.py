"""JSON output formatter for Excel pipeline results.

Serializes :class:`ExcelPipelineState` to a structured JSON string via
:class:`ExcelPipelineResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from policyfoundry.exceptions import OutputError
from policyfoundry.output.models import ExcelPipelineResult

if TYPE_CHECKING:
    from policyfoundry.pipeline.excel_state import ExcelPipelineState


def format_excel_json(state: ExcelPipelineState) -> str:
    """Serialize an ExcelPipelineState dict to a formatted JSON string.

    Constructs an :class:`ExcelPipelineResult` from the state dict and
    returns its JSON representation with 2-space indentation.

    Args:
        state: An :class:`ExcelPipelineState` dict from pipeline execution.

    Returns:
        A JSON string with all pipeline stage data, suitable for file
        output or API responses.

    Raises:
        OutputError: If ExcelPipelineResult construction or serialization
            fails, with ``error_code="OUTPUT_SERIALIZE_FAILED"``.
    """
    try:
        result = ExcelPipelineResult.from_state(state)
        return result.model_dump_json(indent=2)
    except Exception as exc:
        raise OutputError(
            f"Failed to serialize Excel pipeline state to JSON: {exc}",
            error_code="OUTPUT_SERIALIZE_FAILED",
        ) from exc
