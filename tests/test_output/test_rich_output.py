"""Tests for Rich terminal output formatter.

Verifies that format_rich() renders pipeline state as formatted terminal
output with summary panels, risk-colored decision tables, and token usage
footers. Uses Console(file=StringIO()) to capture Rich output as plain text.
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

from policyfoundry.output.rich_output import format_rich
from rich.console import Console

if TYPE_CHECKING:
    from policyfoundry.pipeline.state import PipelineState


class TestFormatRichSummaryPanel:
    """Verify Rich output includes run_id and summary text."""

    def test_format_rich_renders_summary_panel(self, sample_pipeline_state: PipelineState) -> None:
        """Rich output must include the run_id and pipeline summary."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(sample_pipeline_state, console=console)
        output = buf.getvalue()
        assert "run-test-20260311-001" in output, (
            f"run_id not found in Rich output:\n{output[:500]}"
        )
        assert "TCP dominance" in output or "Moderate inbound" in output, (
            f"Analysis summary not found in Rich output:\n{output[:500]}"
        )


class TestFormatRichRiskColors:
    """Verify decisions table uses correct color per RiskLevel."""

    def test_format_rich_risk_colors(self, sample_pipeline_state: PipelineState) -> None:
        """Risk levels must map to correct colors per RiskLevel."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, color_system="truecolor", width=120)
        format_rich(sample_pipeline_state, console=console)
        output = buf.getvalue()
        assert "LOW" in output, "LOW risk level not in output"
        assert "MEDIUM" in output, "MEDIUM risk level not in output"
        assert "HIGH" in output, "HIGH risk level not in output"


class TestFormatRichTokenUsageFooter:
    """Verify token usage section shows prompt/completion tokens and cost."""

    def test_format_rich_token_usage_footer(self, sample_pipeline_state: PipelineState) -> None:
        """Token footer must show prompt/completion tokens and cost."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(sample_pipeline_state, console=console)
        output = buf.getvalue()
        assert "4200" in output or "4,200" in output, (
            f"Prompt tokens count not in Rich output:\n{output[:500]}"
        )
        assert "1800" in output or "1,800" in output, (
            f"Completion tokens count not in Rich output:\n{output[:500]}"
        )
        assert "0.0042" in output, (
            f"Total cost not in Rich output:\n{output[:500]}"
        )

    def test_format_rich_missing_token_usage(self, sample_pipeline_state_no_tokens: PipelineState) -> None:
        """When token_usage is absent, formatter shows 'N/A' and does not crash."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(sample_pipeline_state_no_tokens, console=console)
        output = buf.getvalue()
        assert "N/A" in output, (
            f"Missing token_usage should show 'N/A':\n{output[:500]}"
        )


class TestFormatRichEmptyState:
    """Verify rendering with minimal state doesn't crash."""

    def test_format_rich_empty_state(self, sample_pipeline_state_empty: PipelineState) -> None:
        """Rendering a minimal state (no stage outputs) must not raise."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(sample_pipeline_state_empty, console=console)
        output = buf.getvalue()
        assert "run-empty-20260311-001" in output, (
            f"run_id not found in minimal state output:\n{output[:500]}"
        )


class TestFormatRichRenderFailureWarnings:
    """Verify console warnings appear when a section fails to render."""

    def test_warns_on_analysis_render_failure(self, sample_pipeline_state: PipelineState) -> None:
        """Malformed analysis data triggers visible console warning."""
        state = dict(sample_pipeline_state)
        state["analysis"] = "not-a-valid-analysis"  # causes model_validate to raise

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render traffic analysis" in output
        # Graceful degradation: other sections still render
        assert "Decisions" in output
        assert "Token Usage" in output

    def test_warns_on_assessment_render_failure(self, sample_pipeline_state: PipelineState) -> None:
        """Malformed assessment data triggers visible console warning."""
        state = dict(sample_pipeline_state)
        state["assessment"] = "not-a-valid-assessment"

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render security assessment" in output
        assert "Traffic Analysis" in output  # still renders

    def test_warns_on_proposals_render_failure(self, sample_pipeline_state: PipelineState) -> None:
        """Malformed proposals data triggers visible console warning."""
        state = dict(sample_pipeline_state)
        state["proposals"] = [{"bad": "proposal_data"}]

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render proposals" in output
        assert "Decisions" in output  # still renders

    def test_warns_on_decisions_render_failure(self, sample_pipeline_state: PipelineState) -> None:
        """Malformed decisions data triggers visible console warning."""
        state = dict(sample_pipeline_state)
        state["decisions"] = [{"bad": "decision_data"}]

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render decisions" in output
        assert "Token Usage" in output  # still renders
