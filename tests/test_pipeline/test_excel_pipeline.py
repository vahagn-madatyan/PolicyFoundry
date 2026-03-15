"""Tests for Excel pipeline graph construction and end-to-end runner execution."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from policyfoundry.adapters.null import NullAdapter
from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
    ValidationResult,
)
from policyfoundry.analysis.models import AggregatedFlow, DirectionLabel, SubnetGroup
from policyfoundry.exceptions import PipelineError
from policyfoundry.ingestion.excel_schema import ExcelTrafficRecord
from policyfoundry.pipeline.excel_graph import (
    ExcelPipelineContext,
    build_excel_pipeline,
)
from policyfoundry.pipeline.excel_stages.decide import RuleDecisionList
from policyfoundry.pipeline.excel_stages.generate import PolicyProposalList
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
def sample_excel_records() -> list[ExcelTrafficRecord]:
    """Minimal set of ExcelTrafficRecords for runner integration tests.

    These records produce deterministic aggregated flows and subnet groups
    when passed through aggregate_flows() + group_to_subnets().
    """
    return [
        ExcelTrafficRecord(
            ip1="10.0.1.50",
            port1=49152,
            ip2="10.0.2.10",
            port2=443,
            protocol="TCP",
            interface1="eth0",
            interface2="eth1",
            hostname1="host50",
            hostname2="api-server",
            flag="SYN",
        ),
        ExcelTrafficRecord(
            ip1="10.0.1.51",
            port1=49200,
            ip2="10.0.2.10",
            port2=443,
            protocol="TCP",
            interface1="eth0",
            interface2="eth1",
            hostname1="host51",
            hostname2="api-server",
            flag="SYN",
        ),
        ExcelTrafficRecord(
            ip1="192.168.1.5",
            port1=50001,
            ip2="10.0.1.50",
            port2=22,
            protocol="TCP",
            interface1="eth1",
            interface2="eth0",
            hostname1="bastion",
            hostname2="host50",
            flag="SYN",
        ),
    ]


@pytest.fixture
def sample_analysis() -> TrafficAnalysis:
    """Sample LLM output for analyze stage."""
    return TrafficAnalysis(
        summary="Mixed traffic with HTTPS dominance.",
        total_flows=3,
        unique_sources=3,
        unique_destinations=2,
        top_talkers=[],
        port_distribution=[],
        anomalies=[],
        bandwidth_outliers=[],
    )


@pytest.fixture
def sample_assessment() -> SecurityAssessment:
    """Sample LLM output for assess stage."""
    return SecurityAssessment(
        overall_risk=RiskLevel.MEDIUM,
        risk_scores=[],
        rule_gaps=[],
        compliance_findings=[],
    )


@pytest.fixture
def sample_proposals() -> PolicyProposalList:
    """Sample LLM output for generate stage."""
    return PolicyProposalList(
        proposals=[
            PolicyProposal(
                proposal_id="prop-001",
                rule=UniversalRule(
                    name="allow-https-outbound",
                    description="Allow HTTPS to 10.0.2.10",
                    action=RuleAction.ALLOW,
                    direction=Direction.OUTBOUND,
                    protocol="TCP",
                    source=[NetworkEndpoint(cidr="10.0.1.0/24")],
                    destination=[NetworkEndpoint(cidr="10.0.2.10/32")],
                    port_range=PortRange(from_port=443, to_port=443),
                ),
                justification="Repeated HTTPS traffic from 10.0.1.0/24 subnet",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                impact_analysis="Allows HTTPS from app subnet to API server",
            ),
        ]
    )


@pytest.fixture
def sample_decisions() -> RuleDecisionList:
    """Sample LLM output for decide stage."""
    return RuleDecisionList(
        decisions=[
            RuleDecision(
                decision_id="dec-001",
                proposal_id="prop-001",
                action="CREATE",
                risk_level=RiskLevel.LOW,
                reason="Low-risk HTTPS rule approved",
                approval_required=False,
            ),
        ]
    )


def _make_llm_mock(
    analysis: TrafficAnalysis,
    assessment: SecurityAssessment,
    proposals: PolicyProposalList,
    decisions: RuleDecisionList,
) -> MagicMock:
    """Create mock LLM client that dispatches by response_model type."""
    from policyfoundry.pipeline.llm import LLMClient

    llm = MagicMock(spec=LLMClient)

    response_map: dict[type, object] = {
        TrafficAnalysis: analysis,
        SecurityAssessment: assessment,
        PolicyProposalList: proposals,
        RuleDecisionList: decisions,
    }

    async def _complete(
        messages: list[dict[str, str]],
        response_model: type,
        temperature: float | None = None,
        **kwargs: object,
    ) -> object:
        return response_map[response_model]

    llm.complete = AsyncMock(side_effect=_complete)
    return llm


# ---------------------------------------------------------------------------
# Graph construction tests
# ---------------------------------------------------------------------------


class TestBuildExcelPipeline:
    """Tests for build_excel_pipeline() graph construction."""

    def test_graph_compiles(self) -> None:
        """build_excel_pipeline() returns a compiled graph without errors."""
        graph = build_excel_pipeline()
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        """Compiled graph contains all 5 stage nodes."""
        graph = build_excel_pipeline()
        # LangGraph exposes node names via the graph's nodes dict
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"analyze", "assess", "generate", "validate", "decide"}
        assert expected.issubset(node_names), (
            f"Missing nodes: {expected - node_names}"
        )


# ---------------------------------------------------------------------------
# Runner integration tests
# ---------------------------------------------------------------------------


class TestRunExcelPipeline:
    """Integration tests for run_excel_pipeline() end-to-end execution."""

    async def test_full_pipeline_produces_all_outputs(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
        sample_analysis: TrafficAnalysis,
        sample_assessment: SecurityAssessment,
        sample_proposals: PolicyProposalList,
        sample_decisions: RuleDecisionList,
    ) -> None:
        """Runner produces state with all stage output keys populated."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline

        llm = _make_llm_mock(
            sample_analysis, sample_assessment, sample_proposals, sample_decisions,
        )

        result = await run_excel_pipeline(llm, sample_excel_records)

        assert "analysis" in result
        assert "assessment" in result
        assert "proposals" in result
        assert "decisions" in result
        assert "aggregated_flows" in result
        assert "subnet_groups" in result

    async def test_runner_defaults_to_null_adapter(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
        sample_analysis: TrafficAnalysis,
        sample_assessment: SecurityAssessment,
        sample_proposals: PolicyProposalList,
        sample_decisions: RuleDecisionList,
    ) -> None:
        """When adapter=None, runner uses NullAdapter (all proposals pass validate)."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline

        llm = _make_llm_mock(
            sample_analysis, sample_assessment, sample_proposals, sample_decisions,
        )

        # adapter=None (default)
        result = await run_excel_pipeline(llm, sample_excel_records)

        # With NullAdapter, all proposals pass validation
        assert len(result["proposals"]) == len(sample_proposals.proposals)

    async def test_runner_accepts_explicit_adapter(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
        sample_analysis: TrafficAnalysis,
        sample_assessment: SecurityAssessment,
        sample_proposals: PolicyProposalList,
        sample_decisions: RuleDecisionList,
    ) -> None:
        """Runner accepts an explicit adapter and uses it for validation."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline

        llm = _make_llm_mock(
            sample_analysis, sample_assessment, sample_proposals, sample_decisions,
        )

        adapter = NullAdapter()
        result = await run_excel_pipeline(llm, sample_excel_records, adapter=adapter)

        assert "decisions" in result

    async def test_state_has_metadata(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
        sample_analysis: TrafficAnalysis,
        sample_assessment: SecurityAssessment,
        sample_proposals: PolicyProposalList,
        sample_decisions: RuleDecisionList,
    ) -> None:
        """Final state has run_id (valid UUID), started_at, current_stage."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline

        llm = _make_llm_mock(
            sample_analysis, sample_assessment, sample_proposals, sample_decisions,
        )

        result = await run_excel_pipeline(llm, sample_excel_records)

        uuid.UUID(result["run_id"])  # validates format
        assert "T" in result["started_at"]
        assert result["current_stage"] == "decide"

    async def test_stages_execute_in_order(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
        sample_analysis: TrafficAnalysis,
        sample_assessment: SecurityAssessment,
        sample_proposals: PolicyProposalList,
        sample_decisions: RuleDecisionList,
    ) -> None:
        """LLM calls happen in order: analyze, assess, generate, decide."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline
        from policyfoundry.pipeline.llm import LLMClient

        call_order: list[str] = []
        response_map: dict[type, object] = {
            TrafficAnalysis: sample_analysis,
            SecurityAssessment: sample_assessment,
            PolicyProposalList: sample_proposals,
            RuleDecisionList: sample_decisions,
        }
        stage_map: dict[type, str] = {
            TrafficAnalysis: "analyze",
            SecurityAssessment: "assess",
            PolicyProposalList: "generate",
            RuleDecisionList: "decide",
        }

        async def _complete(
            messages: list[dict[str, str]],
            response_model: type,
            temperature: float | None = None,
            **kwargs: object,
        ) -> object:
            call_order.append(stage_map.get(response_model, "unknown"))
            return response_map[response_model]

        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=_complete)

        await run_excel_pipeline(llm, sample_excel_records)

        assert call_order == ["analyze", "assess", "generate", "decide"]


class TestRunExcelPipelineErrorHandling:
    """Tests for pipeline error wrapping."""

    async def test_pipeline_error_passthrough(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
    ) -> None:
        """PipelineError from a stage is re-raised directly."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline
        from policyfoundry.pipeline.llm import LLMClient

        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(
            side_effect=PipelineError(
                "Analyze failed",
                error_code="LLM_CALL_FAILED",
                details={"stage": "analyze"},
            )
        )

        with pytest.raises(PipelineError) as exc_info:
            await run_excel_pipeline(llm, sample_excel_records)

        assert exc_info.value.error_code == "LLM_CALL_FAILED"

    async def test_unexpected_error_wrapped_in_pipeline_error(
        self,
        sample_excel_records: list[ExcelTrafficRecord],
    ) -> None:
        """Non-PipelineError exceptions are wrapped with PIPELINE_STAGE_FAILED."""
        from policyfoundry.pipeline.excel_runner import run_excel_pipeline
        from policyfoundry.pipeline.llm import LLMClient

        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(PipelineError) as exc_info:
            await run_excel_pipeline(llm, sample_excel_records)

        assert exc_info.value.error_code == "PIPELINE_STAGE_FAILED"
        assert exc_info.value.__cause__ is not None
