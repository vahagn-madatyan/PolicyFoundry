"""JSON output formatter for pipeline results.

Serializes :class:`PipelineState` to a structured JSON string via
:class:`PipelineResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from policyfoundry.exceptions import OutputError
from policyfoundry.output.models import PipelineResult

if TYPE_CHECKING:
    from policyfoundry.pipeline.state import PipelineState


def format_json(state: PipelineState) -> str:
    """Serialize a PipelineState dict to a formatted JSON string.

    Constructs a :class:`PipelineResult` from the state dict and returns
    its JSON representation with 2-space indentation.

    Args:
        state: A :class:`PipelineState` dict from pipeline execution.

    Returns:
        A JSON string with all pipeline stage data, suitable for file
        output or API responses.

    Raises:
        OutputError: If PipelineResult construction or serialization fails,
            with ``error_code="OUTPUT_SERIALIZE_FAILED"``.
    """
    try:
        result = PipelineResult.from_state(state)
        return result.model_dump_json(indent=2)
    except Exception as exc:
        raise OutputError(
            f"Failed to serialize pipeline state to JSON: {exc}",
            error_code="OUTPUT_SERIALIZE_FAILED",
        ) from exc
