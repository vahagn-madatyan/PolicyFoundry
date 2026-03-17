"""Tests for Excel pipeline output formatters (Rich and JSON).

Verifies format_excel_rich() renders correctly with Excel-specific
summary panel, and format_excel_json() serializes to valid JSON with
expected keys.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import pytest

from rich.console import Console

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
)
from policyfoundry.output.excel_json_output import format_excel_json
from policyfoundry.output.excel_rich_output import format_excel_rich
from policyfoundry.output.models import ExcelPipelineResult
from policyfoundry.pipeline.excel_state import ExcelPipelineState
from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_excel_state() -> ExcelPipelineState:
    """Full ExcelPipelineState with all stages populated."""
    analysis = TrafficAnalysis(
        summary="Mixed traffic with HTTPS dominance and SSH access.",
        total_flows=965,
        unique_sources=3,
        unique_destinations=3,
        top_talkers=[
            {"ip": "10.0.1.50", "flow_count": 800, "protocol": "TCP"},
        ],
        port_distribution=[
            {"port": 443, "protocol": "TCP", "percentage": 82.9},
            {"port": 22, "protocol": "TCP", "percentage": 12.4},
        ],
        anomalies=[],
        bandwidth_outliers=[],
    )

    assessment = SecurityAssessment(
        overall_risk=RiskLevel.MEDIUM,
        risk_scores=[
            {"category": "inferred_gaps", "score": 0.5, "description": "SSH access pattern without explicit rule"},
        ],
        rule_gaps=[
            {"gap_type": "inferred_missing", "description": "SSH from 192.168.1.5 likely needs rule", "severity": "MEDIUM"},
        ],
        compliance_findings=["SSH access not restricted"],
    )

    proposals = [
        PolicyProposal(
            proposal_id="prop-001",
            rule=UniversalRule(
                name="allow-https-outbound",
                description="Allow HTTPS to API server",
                action=RuleAction.ALLOW,
                direction=Direction.OUTBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(cidr="10.0.1.0/24")],
                destination=[NetworkEndpoint(cidr="10.0.2.10/32")],
                port_range=PortRange(from_port=443, to_port=443),
            ),
            justification="Repeated HTTPS traffic from subnet",
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            impact_analysis="Allows HTTPS from app subnet",
        ),
    ]

    decisions = [
        RuleDecision(
            decision_id="dec-001",
            proposal_id="prop-001",
            action="CREATE",
            risk_level=RiskLevel.LOW,
            reason="Low-risk HTTPS rule approved",
            approval_required=False,
        ),
    ]

    aggregated_flows: list[dict[str, Any]] = [
        {
            "src_ip": "10.0.1.50",
            "dst_ip": "10.0.2.10",
            "service_port": 443,
            "protocol": "TCP",
            "direction": "OUTBOUND",
            "flow_count": 800,
            "src_interface": "eth0",
            "dst_interface": "eth1",
            "sample_src_ports": [49152],
        },
        {
            "src_ip": "192.168.1.5",
            "dst_ip": "10.0.1.50",
            "service_port": 22,
            "protocol": "TCP",
            "direction": "INBOUND",
            "flow_count": 120,
            "src_interface": "eth1",
            "dst_interface": "eth0",
            "sample_src_ports": [50001],
        },
        {
            "src_ip": "10.0.1.75",
            "dst_ip": "10.0.3.20",
            "service_port": 8080,
            "protocol": "TCP",
            "direction": "UNKNOWN",
            "flow_count": 45,
            "src_interface": "eth0",
            "dst_interface": "eth0",
            "sample_src_ports": [],
        },
    ]

    subnet_groups: list[dict[str, Any]] = [
        {
            "cidr": "10.0.1.0/24",
            "member_ips": ["10.0.1.50", "10.0.1.75"],
            "member_count": 2,
            "shared_patterns": [{"protocol": "TCP", "port": 443}],
        },
    ]

    state: ExcelPipelineState = {
        "run_id": "run-excel-test-001",
        "started_at": "2026-03-15T09:00:00+00:00",
        "current_stage": "decide",
        "aggregated_flows": aggregated_flows,
        "subnet_groups": subnet_groups,
        "analysis": analysis.model_dump(),
        "assessment": assessment.model_dump(),
        "proposals": [p.model_dump() for p in proposals],
        "decisions": [d.model_dump() for d in decisions],
        "token_usage": {
            "prompt_tokens": 3000,
            "completion_tokens": 1200,
            "total_tokens": 4200,
            "total_cost": 0.0030,
            "per_stage": [
                {"stage": "analyze", "prompt_tokens": 1000, "completion_tokens": 400, "total_tokens": 1400, "cost": 0.0010},
            ],
        },
    }
    return state


@pytest.fixture
def sample_excel_state_empty() -> ExcelPipelineState:
    """Minimal ExcelPipelineState with only metadata fields."""
    state: ExcelPipelineState = {
        "run_id": "run-excel-empty-001",
        "started_at": "2026-03-15T09:00:00+00:00",
        "current_stage": "analyze",
    }
    return state


# ---------------------------------------------------------------------------
# Rich output tests
# ---------------------------------------------------------------------------


class TestFormatExcelRichSummaryPanel:
    """Verify Excel-specific summary panel renders correctly."""

    def test_renders_excel_summary_panel(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Excel summary panel includes source type, flow count, directions."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state, console=console)
        output = buf.getvalue()

        assert "Excel Pipeline Summary" in output
        assert "run-excel-test-001" in output
        assert "Excel traffic export" in output

    def test_renders_direction_breakdown(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Direction breakdown shows inbound, outbound, unknown counts."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state, console=console)
        output = buf.getvalue()

        assert "1 inbound" in output
        assert "1 outbound" in output
        assert "1 unknown" in output

    def test_renders_subnet_candidates_count(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Subnet candidates count appears in summary."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state, console=console)
        output = buf.getvalue()

        assert "Subnet Candidates" in output


class TestFormatExcelRichSharedSections:
    """Verify shared renderers are called for analysis/assessment/etc."""

    def test_renders_traffic_analysis(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Traffic analysis section renders from shared renderer."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state, console=console)
        output = buf.getvalue()

        assert "Traffic Analysis" in output
        assert "HTTPS dominance" in output or "Mixed traffic" in output

    def test_renders_decisions(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Decisions table renders with risk levels."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state, console=console)
        output = buf.getvalue()

        assert "Decisions" in output
        assert "CREATE" in output

    def test_renders_token_usage(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Token usage footer renders with cost."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state, console=console)
        output = buf.getvalue()

        assert "Token Usage" in output
        assert "3000" in output or "3,000" in output


class TestFormatExcelRichEmptyState:
    """Verify rendering with minimal state doesn't crash."""

    def test_renders_empty_state(
        self, sample_excel_state_empty: ExcelPipelineState,
    ) -> None:
        """Rendering minimal state (no stage outputs) does not raise."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(sample_excel_state_empty, console=console)
        output = buf.getvalue()

        assert "run-excel-empty-001" in output


class TestFormatExcelRichRenderFailureWarnings:
    """Verify console warnings appear when a section fails to render."""

    def test_warns_on_analysis_render_failure(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Malformed analysis data triggers visible console warning."""
        state = dict(sample_excel_state)
        state["analysis"] = "not-a-valid-analysis"

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render traffic analysis" in output
        assert "Decisions" in output  # graceful degradation
        assert "Token Usage" in output

    def test_warns_on_assessment_render_failure(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Malformed assessment data triggers visible console warning."""
        state = dict(sample_excel_state)
        state["assessment"] = "not-a-valid-assessment"

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render security assessment" in output
        assert "Excel Pipeline Summary" in output  # still renders

    def test_warns_on_proposals_render_failure(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Malformed proposals data triggers visible console warning."""
        state = dict(sample_excel_state)
        state["proposals"] = [{"bad": "proposal_data"}]

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render proposals" in output
        assert "Decisions" in output  # still renders

    def test_warns_on_decisions_render_failure(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Malformed decisions data triggers visible console warning."""
        state = dict(sample_excel_state)
        state["decisions"] = [{"bad": "decision_data"}]

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        format_excel_rich(state, console=console)
        output = buf.getvalue()

        assert "⚠ Failed to render decisions" in output
        assert "Token Usage" in output  # still renders


# ---------------------------------------------------------------------------
# JSON output tests
# ---------------------------------------------------------------------------


class TestFormatExcelJson:
    """Tests for format_excel_json() serialization."""

    def test_produces_valid_json(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """format_excel_json() returns valid JSON string."""
        result = format_excel_json(sample_excel_state)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_contains_all_stage_keys(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """JSON output contains all pipeline stage keys."""
        result = format_excel_json(sample_excel_state)
        parsed = json.loads(result)

        assert "run_id" in parsed
        assert "started_at" in parsed
        assert "current_stage" in parsed
        assert "aggregated_flows" in parsed
        assert "subnet_groups" in parsed
        assert "analysis" in parsed
        assert "assessment" in parsed
        assert "proposals" in parsed
        assert "decisions" in parsed

    def test_json_run_id_matches(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """JSON run_id matches the input state."""
        result = format_excel_json(sample_excel_state)
        parsed = json.loads(result)
        assert parsed["run_id"] == "run-excel-test-001"

    def test_json_aggregated_flows_populated(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """JSON aggregated_flows contains the expected flow data."""
        result = format_excel_json(sample_excel_state)
        parsed = json.loads(result)
        assert len(parsed["aggregated_flows"]) == 3
        assert parsed["aggregated_flows"][0]["src_ip"] == "10.0.1.50"

    def test_json_empty_state(
        self, sample_excel_state_empty: ExcelPipelineState,
    ) -> None:
        """format_excel_json() handles minimal state without errors."""
        result = format_excel_json(sample_excel_state_empty)
        parsed = json.loads(result)
        assert parsed["run_id"] == "run-excel-empty-001"


class TestExcelPipelineResult:
    """Tests for ExcelPipelineResult.from_state() typed access."""

    def test_from_state_reconstructs_models(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """from_state() produces typed analysis/assessment/proposals/decisions."""
        result = ExcelPipelineResult.from_state(sample_excel_state)

        assert result.analysis is not None
        assert result.assessment is not None
        assert len(result.proposals) == 1
        assert len(result.decisions) == 1
        assert result.analysis.total_flows == 965

    def test_from_state_preserves_flows(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """from_state() preserves aggregated_flows and subnet_groups."""
        result = ExcelPipelineResult.from_state(sample_excel_state)
        assert len(result.aggregated_flows) == 3
        assert len(result.subnet_groups) == 1

    def test_from_state_with_empty_state(
        self, sample_excel_state_empty: ExcelPipelineState,
    ) -> None:
        """from_state() works with minimal state (no stage outputs)."""
        result = ExcelPipelineResult.from_state(sample_excel_state_empty)
        assert result.run_id == "run-excel-empty-001"
        assert result.analysis is None
        assert result.proposals == []
