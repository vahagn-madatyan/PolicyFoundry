"""Tests for Excel pipeline stages (analyze, assess, generate, validate, decide)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

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
def sample_aggregated_flows() -> list[AggregatedFlow]:
    """Realistic aggregated flows including UNKNOWN direction."""
    return [
        AggregatedFlow(
            src_ip="10.0.1.50",
            dst_ip="10.0.2.10",
            service_port=443,
            protocol="TCP",
            direction=DirectionLabel.OUTBOUND,
            flow_count=800,
            src_interface="eth0",
            dst_interface="eth1",
            sample_src_ports=[49152, 49200],
        ),
        AggregatedFlow(
            src_ip="192.168.1.5",
            dst_ip="10.0.1.50",
            service_port=22,
            protocol="TCP",
            direction=DirectionLabel.INBOUND,
            flow_count=120,
            src_interface="eth1",
            dst_interface="eth0",
            sample_src_ports=[50001],
        ),
        AggregatedFlow(
            src_ip="10.0.1.75",
            dst_ip="10.0.3.20",
            service_port=8080,
            protocol="TCP",
            direction=DirectionLabel.UNKNOWN,
            flow_count=45,
            src_interface="eth0",
            dst_interface="eth0",
            sample_src_ports=[51000, 51001],
        ),
        AggregatedFlow(
            src_ip="10.0.1.50",
            dst_ip="8.8.8.8",
            service_port=53,
            protocol="UDP",
            direction=DirectionLabel.OUTBOUND,
            flow_count=200,
            src_interface="eth0",
            dst_interface="eth1",
            sample_src_ports=[60000],
        ),
    ]


@pytest.fixture
def sample_subnet_groups() -> list[SubnetGroup]:
    """Subnet group candidates from upstream analysis."""
    return [
        SubnetGroup(
            cidr="10.0.1.0/24",
            member_ips=["10.0.1.50", "10.0.1.75", "10.0.1.100"],
            member_count=3,
            shared_patterns=[
                {"protocol": "TCP", "port": 443},
                {"protocol": "TCP", "port": 22},
            ],
        ),
    ]


@pytest.fixture
def sample_aggregated_flows_dicts(
    sample_aggregated_flows: list[AggregatedFlow],
) -> list[dict]:
    """Aggregated flows as dicts (as stored in ExcelPipelineState)."""
    return [f.model_dump() for f in sample_aggregated_flows]


@pytest.fixture
def sample_subnet_groups_dicts(
    sample_subnet_groups: list[SubnetGroup],
) -> list[dict]:
    """Subnet groups as dicts (as stored in ExcelPipelineState)."""
    return [sg.model_dump() for sg in sample_subnet_groups]


@pytest.fixture
def sample_excel_traffic_analysis() -> TrafficAnalysis:
    """TrafficAnalysis the mock LLM returns for Excel analyze stage."""
    return TrafficAnalysis(
        summary="Mixed traffic with HTTPS dominance and some UNKNOWN flows.",
        total_flows=1165,
        unique_sources=3,
        unique_destinations=4,
        top_talkers=[
            {"ip": "10.0.1.50", "flow_count": 1000, "protocol": "TCP/UDP"},
        ],
        port_distribution=[
            {"port": 443, "protocol": "TCP", "percentage": 68.7},
            {"port": 53, "protocol": "UDP", "percentage": 17.2},
        ],
        anomalies=[
            {"type": "unknown_direction", "flow_count": 45, "note": "UNKNOWN direction on port 8080"},
        ],
        bandwidth_outliers=[],
    )


@pytest.fixture
def sample_excel_security_assessment() -> SecurityAssessment:
    """SecurityAssessment the mock LLM returns for Excel assess stage."""
    return SecurityAssessment(
        overall_risk=RiskLevel.MEDIUM,
        risk_scores=[
            {"category": "inferred_gaps", "score": 0.5, "description": "SSH access pattern without explicit rule"},
            {"category": "unknown_direction", "score": 0.3, "description": "UNKNOWN direction flows on 8080"},
        ],
        rule_gaps=[
            {"gap_type": "inferred_missing", "description": "SSH from 192.168.1.5 likely needs explicit rule", "severity": "MEDIUM"},
        ],
        compliance_findings=["SSH access not restricted to bastion host"],
    )


@pytest.fixture
def mock_excel_runtime(
    mock_llm_client: MagicMock,
    mock_adapter: MagicMock,
) -> MagicMock:
    """Mock runtime with llm_client and adapter for Excel stages."""
    runtime = MagicMock()
    runtime.context.llm_client = mock_llm_client
    runtime.context.adapter = mock_adapter
    return runtime


# ---------------------------------------------------------------------------
# Analyze stage tests
# ---------------------------------------------------------------------------


class TestExcelAnalyzeStage:
    """Tests for the excel_analyze_stage."""

    async def test_returns_analysis_and_current_stage(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """excel_analyze_stage returns dict with analysis and current_stage."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        result = await excel_analyze_stage(state, mock_excel_runtime)

        assert result["current_stage"] == "analyze"
        assert "analysis" in result
        assert result["analysis"] == sample_excel_traffic_analysis.model_dump()

    async def test_calls_llm_with_traffic_analysis_model(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """excel_analyze_stage calls LLM with TrafficAnalysis and temperature 0.1."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_analyze_stage(state, mock_excel_runtime)

        mock_llm_client.complete.assert_called_once()
        call_args = mock_llm_client.complete.call_args
        assert call_args[0][1] is TrafficAnalysis
        assert call_args[1]["temperature"] == 0.1
        assert call_args[1]["stage"] == "analyze"

    async def test_prompt_mentions_excel_traffic_export(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """Analyze system prompt mentions firewall traffic export context."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_analyze_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        system_msg = call_args[0][0][0]["content"]
        assert "firewall traffic export" in system_msg
        assert "not VPC flow logs" in system_msg

    async def test_prompt_includes_summarized_flow_data(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """User message contains pre-summarized stats, not raw flow records."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_analyze_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        # Should contain summarized keys, not raw AggregatedFlow fields
        assert "total_flows" in user_msg
        assert "direction_breakdown" in user_msg
        assert "top_talkers" in user_msg
        assert "port_distribution" in user_msg

    async def test_unknown_direction_appears_in_summary(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """UNKNOWN direction flows appear in the summarized data passed to LLM."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_analyze_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        # The summary should include UNKNOWN in direction_breakdown
        parsed = json.loads(user_msg)
        assert "UNKNOWN" in parsed["direction_breakdown"]
        assert parsed["direction_breakdown"]["UNKNOWN"] > 0

    async def test_uses_pre_summarizer_not_raw_serialization(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """Analyze stage calls summarize_flows, producing compact keys."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_analyze_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        parsed = json.loads(user_msg)
        # These keys are from summarize_flows(), not raw AggregatedFlow
        assert "subnet_candidates" in parsed
        assert "unique_sources" in parsed
        # Raw flow fields should NOT be present at top level
        assert "src_interface" not in user_msg or "src_interface" not in parsed

    async def test_empty_flows_still_calls_llm(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_traffic_analysis: TrafficAnalysis,
    ) -> None:
        """Analyze stage with empty flows still calls LLM."""
        from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_traffic_analysis)

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "starting",
            "aggregated_flows": [],
            "subnet_groups": [],
        }

        await excel_analyze_stage(state, mock_excel_runtime)

        mock_llm_client.complete.assert_called_once()


# ---------------------------------------------------------------------------
# Assess stage tests
# ---------------------------------------------------------------------------


class TestExcelAssessStage:
    """Tests for the excel_assess_stage."""

    async def test_returns_assessment_and_current_stage(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """excel_assess_stage returns dict with assessment and current_stage."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test analysis"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        result = await excel_assess_stage(state, mock_excel_runtime)

        assert result["current_stage"] == "assess"
        assert "assessment" in result
        assert result["assessment"] == sample_excel_security_assessment.model_dump()

    async def test_calls_llm_with_security_assessment_model(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """excel_assess_stage calls LLM with SecurityAssessment and temperature 0.1."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        mock_llm_client.complete.assert_called_once()
        call_args = mock_llm_client.complete.call_args
        assert call_args[0][1] is SecurityAssessment
        assert call_args[1]["temperature"] == 0.1
        assert call_args[1]["stage"] == "assess"

    async def test_calls_adapter_get_rules(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """excel_assess_stage calls adapter.get_rules()."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        mock_adapter.get_rules.assert_called_once()

    async def test_prompt_handles_empty_rules_with_inference(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """Assess system prompt includes inference guidance for empty rules."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        system_msg = call_args[0][0][0]["content"]
        assert "infer likely existing rules" in system_msg.lower()
        assert "empty" in system_msg.lower()

    async def test_prompt_includes_empty_rules_in_user_message(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """User message includes empty current_rules list."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        assert '"current_rules": []' in user_msg

    async def test_prompt_includes_flow_summary_context(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """User message includes compact flow summary as additional context."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        assert "compact flow summary" in user_msg.lower()
        assert "total_flows" in user_msg

    async def test_prompt_includes_analysis_from_state(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """User message includes the traffic analysis dict from state."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        analysis = {"summary": "Test analysis with specific marker XYZ123"}

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": analysis,
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        assert "traffic_analysis" in user_msg
        assert "XYZ123" in user_msg

    async def test_unknown_direction_in_assess_context(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_security_assessment: SecurityAssessment,
        sample_aggregated_flows_dicts: list[dict],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """UNKNOWN direction flows appear in the flow summary passed to assess."""
        from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_excel_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "analyze",
            "analysis": {"summary": "test"},
            "aggregated_flows": sample_aggregated_flows_dicts,
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_assess_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        assert "UNKNOWN" in user_msg


# ---------------------------------------------------------------------------
# Generate stage fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_excel_proposals() -> list[PolicyProposal]:
    """PolicyProposals the mock LLM returns for Excel generate stage."""
    return [
        PolicyProposal(
            proposal_id="excel-prop-001",
            rule=UniversalRule(
                name="allow-https-subnet",
                description="Allow HTTPS from 10.0.1.0/24 subnet",
                action=RuleAction.ALLOW,
                direction=Direction.OUTBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(cidr="10.0.1.0/24")],
                destination=[NetworkEndpoint(cidr="10.0.2.10/32")],
                port_range=PortRange(from_port=443, to_port=443),
            ),
            justification="SubnetGroup 10.0.1.0/24 shares HTTPS pattern to 10.0.2.10",
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            impact_analysis="Allows HTTPS from internal subnet to server",
        ),
        PolicyProposal(
            proposal_id="excel-prop-002",
            rule=UniversalRule(
                name="allow-ssh-inbound",
                description="Allow SSH from management host",
                action=RuleAction.ALLOW,
                direction=Direction.INBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(cidr="192.168.1.5/32")],
                destination=[NetworkEndpoint(cidr="10.0.1.50/32")],
                port_range=PortRange(from_port=22, to_port=22),
            ),
            justification="SSH traffic pattern from management host",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.85,
            impact_analysis="Allows SSH from 192.168.1.5 to 10.0.1.50",
        ),
    ]


@pytest.fixture
def sample_excel_proposals_dicts(
    sample_excel_proposals: list[PolicyProposal],
) -> list[dict]:
    """Proposals as dicts (as stored in ExcelPipelineState)."""
    return [p.model_dump() for p in sample_excel_proposals]


@pytest.fixture
def sample_excel_decisions() -> list[RuleDecision]:
    """RuleDecisions the mock LLM returns for Excel decide stage."""
    return [
        RuleDecision(
            decision_id="excel-dec-001",
            proposal_id="excel-prop-001",
            action="CREATE",
            risk_level=RiskLevel.LOW,
            reason="Subnet HTTPS rule is well-scoped and low risk",
            approval_required=False,
        ),
        RuleDecision(
            decision_id="excel-dec-002",
            proposal_id="excel-prop-002",
            action="CREATE",
            risk_level=RiskLevel.MEDIUM,
            reason="SSH access needed but requires approval",
            approval_required=True,
        ),
    ]


# ---------------------------------------------------------------------------
# Generate prompt content tests
# ---------------------------------------------------------------------------


class TestExcelGeneratePromptContent:
    """Verify the generate system prompt references correct shared_patterns field names."""

    def test_prompt_contains_dst_ip(self) -> None:
        """Prompt references dst_ip for source-side subnet groups."""
        from policyfoundry.pipeline.excel_prompts.generate import EXCEL_GENERATE_SYSTEM_PROMPT

        assert "dst_ip" in EXCEL_GENERATE_SYSTEM_PROMPT

    def test_prompt_contains_src_ip(self) -> None:
        """Prompt references src_ip for destination-side subnet groups."""
        from policyfoundry.pipeline.excel_prompts.generate import EXCEL_GENERATE_SYSTEM_PROMPT

        assert "src_ip" in EXCEL_GENERATE_SYSTEM_PROMPT

    def test_prompt_does_not_contain_counterpart_ip(self) -> None:
        """counterpart_ip is not a real field — must not appear in prompt."""
        from policyfoundry.pipeline.excel_prompts.generate import EXCEL_GENERATE_SYSTEM_PROMPT

        assert "counterpart_ip" not in EXCEL_GENERATE_SYSTEM_PROMPT

    def test_prompt_describes_both_grouping_directions(self) -> None:
        """Prompt explains both source-side and destination-side grouping."""
        from policyfoundry.pipeline.excel_prompts.generate import EXCEL_GENERATE_SYSTEM_PROMPT

        assert "Source-side groups" in EXCEL_GENERATE_SYSTEM_PROMPT
        assert "Destination-side groups" in EXCEL_GENERATE_SYSTEM_PROMPT

    def test_prompt_mentions_service_port_and_protocol(self) -> None:
        """Prompt references the other shared_patterns keys."""
        from policyfoundry.pipeline.excel_prompts.generate import EXCEL_GENERATE_SYSTEM_PROMPT

        assert "service_port" in EXCEL_GENERATE_SYSTEM_PROMPT
        assert "protocol" in EXCEL_GENERATE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Generate stage tests
# ---------------------------------------------------------------------------


class TestExcelGenerateStage:
    """Tests for the excel_generate_stage."""

    async def test_returns_proposals_and_current_stage(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals: list[PolicyProposal],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """excel_generate_stage returns dict with proposals and current_stage."""
        from policyfoundry.pipeline.excel_stages.generate import (
            PolicyProposalList,
            excel_generate_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=sample_excel_proposals),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "assess",
            "assessment": {"overall_risk": "MEDIUM"},
            "analysis": {"summary": "test analysis"},
            "subnet_groups": sample_subnet_groups_dicts,
        }

        result = await excel_generate_stage(state, mock_excel_runtime)

        assert result["current_stage"] == "generate"
        assert "proposals" in result
        assert len(result["proposals"]) == 2
        assert result["proposals"][0]["proposal_id"] == "excel-prop-001"

    async def test_calls_llm_with_temperature_03(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals: list[PolicyProposal],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """Generate stage uses temperature=0.3 per D025."""
        from policyfoundry.pipeline.excel_stages.generate import (
            PolicyProposalList,
            excel_generate_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=sample_excel_proposals),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "assess",
            "assessment": {"overall_risk": "MEDIUM"},
            "analysis": {"summary": "test"},
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_generate_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        assert call_args[1]["temperature"] == 0.3
        assert call_args[1]["stage"] == "generate"

    async def test_subnet_groups_passed_in_prompt(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals: list[PolicyProposal],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """User message includes subnet_group_candidates from state."""
        from policyfoundry.pipeline.excel_stages.generate import (
            PolicyProposalList,
            excel_generate_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=sample_excel_proposals),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "assess",
            "assessment": {"overall_risk": "MEDIUM"},
            "analysis": {"summary": "test"},
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_generate_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args[0][0][1]["content"]
        parsed = json.loads(user_msg)
        assert "subnet_group_candidates" in parsed
        assert len(parsed["subnet_group_candidates"]) == 1
        assert parsed["subnet_group_candidates"][0]["cidr"] == "10.0.1.0/24"

    async def test_system_prompt_mentions_cidr_format(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals: list[PolicyProposal],
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """Generate system prompt includes CIDR format guidance."""
        from policyfoundry.pipeline.excel_stages.generate import (
            PolicyProposalList,
            excel_generate_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=sample_excel_proposals),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "assess",
            "assessment": {},
            "analysis": {},
            "subnet_groups": sample_subnet_groups_dicts,
        }

        await excel_generate_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        system_msg = call_args[0][0][0]["content"]
        assert "/32" in system_msg
        assert "/24" in system_msg
        assert "subnet_group" in system_msg.lower() or "SubnetGroup" in system_msg

    async def test_limits_to_max_proposals(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_subnet_groups_dicts: list[dict],
    ) -> None:
        """Generate stage limits output to 20 proposals."""
        from policyfoundry.pipeline.excel_stages.generate import (
            PolicyProposalList,
            excel_generate_stage,
        )

        # Create 25 proposals
        many_proposals = [
            PolicyProposal(
                proposal_id=f"prop-{i:03d}",
                rule=UniversalRule(
                    name=f"rule-{i}",
                    description=f"Test rule {i}",
                    action=RuleAction.ALLOW,
                    direction=Direction.INBOUND,
                    protocol="TCP",
                    source=[NetworkEndpoint(cidr="10.0.0.0/8")],
                    destination=[],
                    port_range=PortRange(from_port=443, to_port=443),
                ),
                justification=f"Test justification {i}",
                risk_level=RiskLevel.LOW,
                confidence=0.5,
                impact_analysis=f"Test impact {i}",
            )
            for i in range(25)
        ]

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=many_proposals),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "assess",
            "assessment": {},
            "analysis": {},
            "subnet_groups": sample_subnet_groups_dicts,
        }

        result = await excel_generate_stage(state, mock_excel_runtime)

        assert len(result["proposals"]) == 20


# ---------------------------------------------------------------------------
# Validate stage tests
# ---------------------------------------------------------------------------


class TestExcelValidateStage:
    """Tests for the excel_validate_proposals."""

    async def test_null_adapter_passes_all(
        self,
        mock_excel_runtime: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_proposals_dicts: list[dict],
    ) -> None:
        """NullAdapter (mock returning valid=True) passes all proposals."""
        from policyfoundry.pipeline.excel_stages.validate import excel_validate_proposals

        mock_adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "generate",
            "proposals": sample_excel_proposals_dicts,
        }

        result = await excel_validate_proposals(state, mock_excel_runtime)

        assert result["current_stage"] == "validate"
        assert len(result["proposals"]) == 2

    async def test_failing_validation_removes_proposal(
        self,
        mock_excel_runtime: MagicMock,
        mock_adapter: MagicMock,
        sample_excel_proposals_dicts: list[dict],
    ) -> None:
        """A proposal failing validation is removed from output."""
        from policyfoundry.pipeline.excel_stages.validate import excel_validate_proposals

        # First proposal passes, second fails
        mock_adapter.validate = AsyncMock(
            side_effect=[
                ValidationResult(valid=True),
                ValidationResult(valid=False, reason="Port not supported"),
            ],
        )
        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "generate",
            "proposals": sample_excel_proposals_dicts,
        }

        result = await excel_validate_proposals(state, mock_excel_runtime)

        assert len(result["proposals"]) == 1
        assert result["proposals"][0]["proposal_id"] == "excel-prop-001"

    async def test_empty_proposals_returns_empty(
        self,
        mock_excel_runtime: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """Empty proposals list passes through cleanly."""
        from policyfoundry.pipeline.excel_stages.validate import excel_validate_proposals

        mock_adapter.get_rules = AsyncMock(return_value=[])

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "generate",
            "proposals": [],
        }

        result = await excel_validate_proposals(state, mock_excel_runtime)

        assert result["proposals"] == []
        assert result["current_stage"] == "validate"


# ---------------------------------------------------------------------------
# Decide stage tests
# ---------------------------------------------------------------------------


class TestExcelDecideStage:
    """Tests for the excel_decide_stage."""

    async def test_returns_decisions_from_llm(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals_dicts: list[dict],
        sample_excel_decisions: list[RuleDecision],
    ) -> None:
        """excel_decide_stage calls LLM and returns decisions."""
        from policyfoundry.pipeline.excel_stages.decide import (
            RuleDecisionList,
            excel_decide_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=RuleDecisionList(decisions=sample_excel_decisions),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "validate",
            "proposals": sample_excel_proposals_dicts,
        }

        result = await excel_decide_stage(state, mock_excel_runtime)

        assert result["current_stage"] == "decide"
        assert len(result["decisions"]) == 2
        assert result["decisions"][0]["decision_id"] == "excel-dec-001"

    async def test_empty_proposals_short_circuits(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
    ) -> None:
        """Empty proposals triggers D024 short-circuit — no LLM call."""
        from policyfoundry.pipeline.excel_stages.decide import excel_decide_stage

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "validate",
            "proposals": [],
        }

        result = await excel_decide_stage(state, mock_excel_runtime)

        assert result["decisions"] == []
        assert result["current_stage"] == "decide"
        mock_llm_client.complete.assert_not_called()

    async def test_calls_llm_with_rule_decision_list(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals_dicts: list[dict],
        sample_excel_decisions: list[RuleDecision],
    ) -> None:
        """Decide stage calls LLM with RuleDecisionList wrapper model."""
        from policyfoundry.pipeline.excel_stages.decide import (
            RuleDecisionList,
            excel_decide_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=RuleDecisionList(decisions=sample_excel_decisions),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "validate",
            "proposals": sample_excel_proposals_dicts,
        }

        await excel_decide_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        assert call_args[0][1] is RuleDecisionList
        assert call_args[1]["temperature"] == 0.1
        assert call_args[1]["stage"] == "decide"

    async def test_decide_prompt_is_excel_aware(
        self,
        mock_excel_runtime: MagicMock,
        mock_llm_client: MagicMock,
        sample_excel_proposals_dicts: list[dict],
        sample_excel_decisions: list[RuleDecision],
    ) -> None:
        """Decide system prompt mentions no existing rules / no UPDATE."""
        from policyfoundry.pipeline.excel_stages.decide import (
            RuleDecisionList,
            excel_decide_stage,
        )

        mock_llm_client.complete = AsyncMock(
            return_value=RuleDecisionList(decisions=sample_excel_decisions),
        )

        state: ExcelPipelineState = {
            "run_id": "test-run",
            "current_stage": "validate",
            "proposals": sample_excel_proposals_dicts,
        }

        await excel_decide_stage(state, mock_excel_runtime)

        call_args = mock_llm_client.complete.call_args
        system_msg = call_args[0][0][0]["content"]
        assert "no existing rules" in system_msg.lower()
        assert "CREATE or SKIP" in system_msg
