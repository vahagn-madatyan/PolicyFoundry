"""Tests for LangGraph pipeline construction and execution flow."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
    ValidationResult,
)
from policyfoundry.exceptions import PipelineError
from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)
from policyfoundry.pipeline.stages.decide import RuleDecisionList
from policyfoundry.pipeline.stages.generate import PolicyProposalList

_QUERIES_PATH = "policyfoundry.pipeline.stages.analyze"


@pytest.fixture
def _sample_rules() -> list[UniversalRule]:
    """Two sample SG rules for integration tests."""
    return [
        UniversalRule(
            id="sgr-001",
            name="allow-https-inbound",
            description="Allow HTTPS inbound",
            action=RuleAction.ALLOW,
            direction=Direction.INBOUND,
            protocol="TCP",
            source=[NetworkEndpoint(cidr="0.0.0.0/0")],
            destination=[],
            port_range=PortRange(from_port=443, to_port=443),
        ),
    ]


@pytest.fixture
def _sample_traffic_analysis() -> TrafficAnalysis:
    """Sample LLM output for analyze stage."""
    return TrafficAnalysis(
        summary="Moderate traffic with TCP dominance.",
        total_flows=10000,
        unique_sources=20,
        unique_destinations=5,
        top_talkers=[],
        port_distribution=[],
        anomalies=[],
        bandwidth_outliers=[],
    )


@pytest.fixture
def _sample_assessment() -> SecurityAssessment:
    """Sample LLM output for assess stage."""
    return SecurityAssessment(
        overall_risk=RiskLevel.MEDIUM,
        risk_scores=[],
        rule_gaps=[],
        compliance_findings=[],
    )


@pytest.fixture
def _sample_proposals(_sample_rules: list[UniversalRule]) -> PolicyProposalList:
    """Sample LLM output for generate stage."""
    return PolicyProposalList(
        proposals=[
            PolicyProposal(
                proposal_id="prop-001",
                rule=_sample_rules[0],
                justification="HTTPS traffic needs explicit allow",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                impact_analysis="Allows HTTPS from any source",
            ),
        ]
    )


@pytest.fixture
def _sample_decisions() -> RuleDecisionList:
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


@pytest.fixture
def _mock_duckdb():
    """Patch all 4 DuckDB query functions with empty/minimal results."""
    from policyfoundry.storage.models import TrafficSummary

    empty_summary = TrafficSummary(
        total_records=0, total_bytes=0,
        unique_sources=0, unique_destinations=0,
        allowed_count=0, denied_count=0,
    )

    with (
        patch(f"{_QUERIES_PATH}.traffic_summary", new_callable=AsyncMock, return_value=empty_summary),
        patch(f"{_QUERIES_PATH}.top_talkers", new_callable=AsyncMock, return_value=[]),
        patch(f"{_QUERIES_PATH}.denied_flows", new_callable=AsyncMock, return_value=[]),
        patch(f"{_QUERIES_PATH}.traffic_by_protocol", new_callable=AsyncMock, return_value=[]),
    ):
        yield


class TestPipelineExecution:
    """Integration tests for full pipeline via run_pipeline()."""

    def _make_llm_mock(
        self,
        analysis: TrafficAnalysis,
        assessment: SecurityAssessment,
        proposals: PolicyProposalList,
        decisions: RuleDecisionList,
    ) -> MagicMock:
        """Create mock LLM that returns correct model per response_model."""
        from policyfoundry.pipeline.llm import LLMClient

        llm_mock = MagicMock(spec=LLMClient)

        response_map = {
            TrafficAnalysis: analysis,
            SecurityAssessment: assessment,
            PolicyProposalList: proposals,
            RuleDecisionList: decisions,
        }

        async def _complete(
            messages: list[dict[str, str]],
            response_model: type,
            temperature: float | None = None,
            **kwargs,
        ) -> object:
            return response_map[response_model]

        llm_mock.complete = AsyncMock(side_effect=_complete)
        return llm_mock

    async def test_full_pipeline_executes_all_stages(
        self,
        _mock_duckdb: None,
        _sample_traffic_analysis: TrafficAnalysis,
        _sample_assessment: SecurityAssessment,
        _sample_proposals: PolicyProposalList,
        _sample_decisions: RuleDecisionList,
        _sample_rules: list[UniversalRule],
    ) -> None:
        """run_pipeline returns PipelineState with all stage output keys."""
        from policyfoundry.pipeline.runner import run_pipeline

        llm = self._make_llm_mock(
            _sample_traffic_analysis, _sample_assessment, _sample_proposals, _sample_decisions,
        )

        adapter = MagicMock()
        adapter.get_rules = AsyncMock(return_value=_sample_rules)
        adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
        adapter.capabilities = MagicMock(
            return_value=AdapterCapabilities(
                name="aws_sg", vendor="AWS",
                supports_deny_rules=False, max_rules_per_direction=60,
            )
        )

        result = await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        assert "analysis" in result
        assert "assessment" in result
        assert "proposals" in result
        assert "decisions" in result

    async def test_pipeline_state_has_metadata(
        self,
        _mock_duckdb: None,
        _sample_traffic_analysis: TrafficAnalysis,
        _sample_assessment: SecurityAssessment,
        _sample_proposals: PolicyProposalList,
        _sample_decisions: RuleDecisionList,
        _sample_rules: list[UniversalRule],
    ) -> None:
        """Final PipelineState has run_id, started_at, current_stage."""
        from policyfoundry.pipeline.runner import run_pipeline

        llm = self._make_llm_mock(
            _sample_traffic_analysis, _sample_assessment, _sample_proposals, _sample_decisions,
        )

        adapter = MagicMock()
        adapter.get_rules = AsyncMock(return_value=_sample_rules)
        adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
        adapter.capabilities = MagicMock(
            return_value=AdapterCapabilities(
                name="aws_sg", vendor="AWS",
                supports_deny_rules=False, max_rules_per_direction=60,
            )
        )

        result = await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        # Validate run_id is a valid UUID
        uuid.UUID(result["run_id"])
        assert "T" in result["started_at"]
        assert result["current_stage"] == "decide"

    async def test_pipeline_stages_execute_in_order(
        self,
        _mock_duckdb: None,
        _sample_traffic_analysis: TrafficAnalysis,
        _sample_assessment: SecurityAssessment,
        _sample_proposals: PolicyProposalList,
        _sample_decisions: RuleDecisionList,
        _sample_rules: list[UniversalRule],
    ) -> None:
        """LLM calls happen in order: analyze, assess, generate, decide."""
        from policyfoundry.pipeline.llm import LLMClient
        from policyfoundry.pipeline.runner import run_pipeline

        call_order: list[str] = []
        response_map = {
            TrafficAnalysis: _sample_traffic_analysis,
            SecurityAssessment: _sample_assessment,
            PolicyProposalList: _sample_proposals,
            RuleDecisionList: _sample_decisions,
        }

        stage_map = {
            TrafficAnalysis: "analyze",
            SecurityAssessment: "assess",
            PolicyProposalList: "generate",
            RuleDecisionList: "decide",
        }

        async def _complete(
            messages: list[dict[str, str]],
            response_model: type,
            temperature: float | None = None,
            **kwargs,
        ) -> object:
            call_order.append(stage_map.get(response_model, "unknown"))
            return response_map[response_model]

        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=_complete)

        adapter = MagicMock()
        adapter.get_rules = AsyncMock(return_value=_sample_rules)
        adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
        adapter.capabilities = MagicMock(
            return_value=AdapterCapabilities(
                name="aws_sg", vendor="AWS",
                supports_deny_rules=False, max_rules_per_direction=60,
            )
        )

        await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        assert call_order == ["analyze", "assess", "generate", "decide"]

    async def test_pipeline_with_empty_data(
        self,
        _mock_duckdb: None,
        _sample_traffic_analysis: TrafficAnalysis,
        _sample_assessment: SecurityAssessment,
        _sample_rules: list[UniversalRule],
    ) -> None:
        """Pipeline completes with empty DuckDB data and no proposals."""
        from policyfoundry.pipeline.runner import run_pipeline

        empty_proposals = PolicyProposalList(proposals=[])
        empty_decisions = RuleDecisionList(decisions=[])

        llm = self._make_llm_mock(
            _sample_traffic_analysis, _sample_assessment, empty_proposals, empty_decisions,
        )

        adapter = MagicMock()
        adapter.get_rules = AsyncMock(return_value=_sample_rules)
        adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
        adapter.capabilities = MagicMock(
            return_value=AdapterCapabilities(
                name="aws_sg", vendor="AWS",
                supports_deny_rules=False, max_rules_per_direction=60,
            )
        )

        result = await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        assert "analysis" in result
        assert "assessment" in result
        assert "proposals" in result
        assert "decisions" in result
        assert result["proposals"] == []
        assert result["decisions"] == []

    async def test_pipeline_with_no_existing_rules(
        self,
        _mock_duckdb: None,
        _sample_traffic_analysis: TrafficAnalysis,
        _sample_assessment: SecurityAssessment,
        _sample_proposals: PolicyProposalList,
        _sample_decisions: RuleDecisionList,
    ) -> None:
        """Pipeline completes when adapter returns no existing rules."""
        from policyfoundry.pipeline.runner import run_pipeline

        llm = self._make_llm_mock(
            _sample_traffic_analysis, _sample_assessment, _sample_proposals, _sample_decisions,
        )

        adapter = MagicMock()
        adapter.get_rules = AsyncMock(return_value=[])
        adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
        adapter.capabilities = MagicMock(
            return_value=AdapterCapabilities(
                name="aws_sg", vendor="AWS",
                supports_deny_rules=False, max_rules_per_direction=60,
            )
        )

        result = await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        assert "analysis" in result
        assert "assessment" in result
        assert "proposals" in result
        assert "decisions" in result


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    async def test_pipeline_error_on_stage_failure(
        self,
        _mock_duckdb: None,
    ) -> None:
        """PipelineError from a stage is re-raised with error_code."""
        from policyfoundry.pipeline.llm import LLMClient
        from policyfoundry.pipeline.runner import run_pipeline

        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(
            side_effect=PipelineError(
                "Analyze failed",
                error_code="LLM_CALL_FAILED",
                details={"stage": "analyze"},
            )
        )

        adapter = MagicMock()

        with pytest.raises(PipelineError) as exc_info:
            await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        assert exc_info.value.error_code == "LLM_CALL_FAILED"

    async def test_pipeline_wraps_unexpected_exception(
        self,
        _mock_duckdb: None,
    ) -> None:
        """Unexpected exception is wrapped in PipelineError."""
        from policyfoundry.pipeline.llm import LLMClient
        from policyfoundry.pipeline.runner import run_pipeline

        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=RuntimeError("Unexpected crash"))

        adapter = MagicMock()

        with pytest.raises(PipelineError) as exc_info:
            await run_pipeline(llm, adapter, "/tmp/test-data", ["sg-123"])

        assert exc_info.value.error_code == "PIPELINE_STAGE_FAILED"
