"""Tests for all 5 pipeline stages."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from policyfoundry.adapters.schema import AdapterCapabilities, UniversalRule, ValidationIssue, ValidationResult
from policyfoundry.pipeline.schema import PolicyProposal, SecurityAssessment, TrafficAnalysis
from policyfoundry.pipeline.state import PipelineState
from policyfoundry.storage.models import (
    DeniedFlowResult,
    TopTalkerResult,
    TrafficByProtocolResult,
    TrafficSummary,
)

_QUERIES_PATH = "policyfoundry.pipeline.stages.analyze"


class TestAnalyzeStage:
    """Tests for the analyze pipeline stage."""

    @pytest.fixture
    def _mock_runtime(self, mock_llm_client: MagicMock, sample_traffic_analysis: TrafficAnalysis) -> MagicMock:
        """Create a mock Runtime with PipelineContext."""
        mock_llm_client.complete = AsyncMock(return_value=sample_traffic_analysis)
        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.data_dir = "/tmp/test-data"
        return runtime

    @pytest.fixture
    def _mock_state(self) -> PipelineState:
        """Create a minimal pipeline state."""
        return PipelineState(run_id="test-run", current_stage="starting")

    async def test_analyze_stage_calls_duckdb_queries(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
        sample_top_talkers: list[TopTalkerResult],
        sample_denied_flows: list[DeniedFlowResult],
        sample_traffic_by_protocol: list[TrafficByProtocolResult],
        sample_traffic_summary: TrafficSummary,
    ) -> None:
        """analyze_stage calls all 4 DuckDB query functions."""
        from policyfoundry.pipeline.stages.analyze import analyze_stage

        with (
            patch(f"{_QUERIES_PATH}.traffic_summary", new_callable=AsyncMock, return_value=sample_traffic_summary) as mock_summary,
            patch(f"{_QUERIES_PATH}.top_talkers", new_callable=AsyncMock, return_value=sample_top_talkers) as mock_talkers,
            patch(f"{_QUERIES_PATH}.denied_flows", new_callable=AsyncMock, return_value=sample_denied_flows) as mock_denied,
            patch(f"{_QUERIES_PATH}.traffic_by_protocol", new_callable=AsyncMock, return_value=sample_traffic_by_protocol) as mock_protocol,
        ):
            await analyze_stage(_mock_state, _mock_runtime)

            mock_summary.assert_called_once_with("/tmp/test-data")
            mock_talkers.assert_called_once_with(20, "/tmp/test-data")
            mock_denied.assert_called_once_with("/tmp/test-data")
            mock_protocol.assert_called_once_with("/tmp/test-data")

    async def test_analyze_stage_calls_llm_complete(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
        sample_traffic_analysis: TrafficAnalysis,
        sample_top_talkers: list[TopTalkerResult],
        sample_denied_flows: list[DeniedFlowResult],
        sample_traffic_by_protocol: list[TrafficByProtocolResult],
        sample_traffic_summary: TrafficSummary,
    ) -> None:
        """analyze_stage calls LLMClient.complete with TrafficAnalysis."""
        from policyfoundry.pipeline.stages.analyze import analyze_stage

        with (
            patch(f"{_QUERIES_PATH}.traffic_summary", new_callable=AsyncMock, return_value=sample_traffic_summary),
            patch(f"{_QUERIES_PATH}.top_talkers", new_callable=AsyncMock, return_value=sample_top_talkers),
            patch(f"{_QUERIES_PATH}.denied_flows", new_callable=AsyncMock, return_value=sample_denied_flows),
            patch(f"{_QUERIES_PATH}.traffic_by_protocol", new_callable=AsyncMock, return_value=sample_traffic_by_protocol),
        ):
            await analyze_stage(_mock_state, _mock_runtime)

            _mock_runtime.context.llm_client.complete.assert_called_once()
            call_args = _mock_runtime.context.llm_client.complete.call_args
            assert call_args[0][1] is TrafficAnalysis
            assert call_args[1]["temperature"] == 0.1
            assert call_args[1]["stage"] == "analyze"

    async def test_analyze_stage_returns_analysis_dict(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
        sample_traffic_analysis: TrafficAnalysis,
        sample_top_talkers: list[TopTalkerResult],
        sample_denied_flows: list[DeniedFlowResult],
        sample_traffic_by_protocol: list[TrafficByProtocolResult],
        sample_traffic_summary: TrafficSummary,
    ) -> None:
        """analyze_stage returns dict with analysis and current_stage."""
        from policyfoundry.pipeline.stages.analyze import analyze_stage

        with (
            patch(f"{_QUERIES_PATH}.traffic_summary", new_callable=AsyncMock, return_value=sample_traffic_summary),
            patch(f"{_QUERIES_PATH}.top_talkers", new_callable=AsyncMock, return_value=sample_top_talkers),
            patch(f"{_QUERIES_PATH}.denied_flows", new_callable=AsyncMock, return_value=sample_denied_flows),
            patch(f"{_QUERIES_PATH}.traffic_by_protocol", new_callable=AsyncMock, return_value=sample_traffic_by_protocol),
        ):
            result = await analyze_stage(_mock_state, _mock_runtime)

            assert result["current_stage"] == "analyze"
            assert "analysis" in result
            assert result["analysis"] == sample_traffic_analysis.model_dump()

    async def test_analyze_stage_empty_data_still_calls_llm(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """analyze_stage with empty DuckDB results still calls LLM."""
        from policyfoundry.pipeline.stages.analyze import analyze_stage

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
            await analyze_stage(_mock_state, _mock_runtime)

            _mock_runtime.context.llm_client.complete.assert_called_once()


class TestEmptyDataHandling:
    """Tests for empty/sparse data handling."""

    async def test_analyze_with_zero_records(
        self,
        mock_llm_client: MagicMock,
        sample_traffic_analysis: TrafficAnalysis,
    ) -> None:
        """Analyze stage completes without error on zero records."""
        from policyfoundry.pipeline.stages.analyze import analyze_stage

        mock_llm_client.complete = AsyncMock(return_value=sample_traffic_analysis)
        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.data_dir = "/tmp/empty-data"

        state = PipelineState(run_id="test", current_stage="starting")

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
            result = await analyze_stage(state, runtime)

            assert result["current_stage"] == "analyze"
            assert "analysis" in result


class TestBuildPipeline:
    """Tests for build_pipeline graph construction."""

    def test_build_pipeline_returns_compiled_graph(self) -> None:
        """build_pipeline() returns a compiled graph with 5 user nodes."""
        from policyfoundry.pipeline.graph import build_pipeline

        graph = build_pipeline()
        node_names = list(graph.nodes.keys())

        for name in ("analyze", "assess", "generate", "validate", "decide"):
            assert name in node_names, f"Expected node '{name}' in graph"


class TestRunPipeline:
    """Tests for run_pipeline error handling."""

    async def test_run_pipeline_catches_exceptions(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """run_pipeline wraps exceptions in PipelineError."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.runner import run_pipeline

        mock_llm_client.complete = AsyncMock(side_effect=RuntimeError("LLM down"))

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
            with pytest.raises(PipelineError) as exc_info:
                await run_pipeline(mock_llm_client, mock_adapter, "/tmp/test-data", ["sg-123"])

            # Stage-level wrapping catches first, carrying stage details
            assert exc_info.value.details.get("stage") == "analyze"


class TestAssessStage:
    """Tests for the assess pipeline stage."""

    @pytest.fixture
    def _mock_runtime(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        sample_security_assessment: SecurityAssessment,
        sample_universal_rules: list[UniversalRule],
    ) -> MagicMock:
        """Create a mock Runtime with PipelineContext for assess."""
        mock_llm_client.complete = AsyncMock(return_value=sample_security_assessment)
        mock_adapter.get_rules = AsyncMock(return_value=sample_universal_rules)
        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.adapter = mock_adapter
        return runtime

    @pytest.fixture
    def _mock_state(self, sample_traffic_analysis_dict: dict) -> PipelineState:
        """Pipeline state with analysis data from previous stage."""
        return PipelineState(
            run_id="test-run",
            current_stage="analyze",
            analysis=sample_traffic_analysis_dict,
        )

    async def test_assess_stage_calls_adapter_get_rules(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """assess_stage calls adapter.get_rules() to fetch SG rules."""
        from policyfoundry.pipeline.stages.assess import assess_stage

        await assess_stage(_mock_state, _mock_runtime)

        _mock_runtime.context.adapter.get_rules.assert_called_once()

    async def test_assess_stage_calls_llm_with_security_assessment(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """assess_stage calls llm_client.complete with SecurityAssessment."""
        from policyfoundry.pipeline.stages.assess import assess_stage

        await assess_stage(_mock_state, _mock_runtime)

        _mock_runtime.context.llm_client.complete.assert_called_once()
        call_args = _mock_runtime.context.llm_client.complete.call_args
        assert call_args[0][1] is SecurityAssessment
        assert call_args[1]["stage"] == "assess"

    async def test_assess_stage_reads_analysis_from_state(
        self,
        _mock_runtime: MagicMock,
        sample_traffic_analysis_dict: dict,
    ) -> None:
        """assess_stage reads analysis from state and passes to prompt."""
        from policyfoundry.pipeline.stages.assess import assess_stage

        state = PipelineState(
            run_id="test-run",
            current_stage="analyze",
            analysis=sample_traffic_analysis_dict,
        )

        await assess_stage(state, _mock_runtime)

        _mock_runtime.context.llm_client.complete.assert_called_once()
        call_args = _mock_runtime.context.llm_client.complete.call_args
        # The user message (second message) should contain the traffic analysis
        user_msg = call_args[0][0][1]["content"]
        assert "traffic_analysis" in user_msg

    async def test_assess_stage_returns_assessment_dict(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
        sample_security_assessment: SecurityAssessment,
    ) -> None:
        """assess_stage returns dict with assessment and current_stage."""
        from policyfoundry.pipeline.stages.assess import assess_stage

        result = await assess_stage(_mock_state, _mock_runtime)

        assert result["current_stage"] == "assess"
        assert "assessment" in result
        assert result["assessment"] == sample_security_assessment.model_dump()


class TestGenerateStage:
    """Tests for the generate pipeline stage."""

    @pytest.fixture
    def _sample_proposals(self, sample_universal_rules: list[UniversalRule]) -> list[PolicyProposal]:
        """Sample list of PolicyProposal objects for generate output."""
        from policyfoundry.adapters.schema import RiskLevel

        return [
            PolicyProposal(
                proposal_id="prop-001",
                rule=sample_universal_rules[0],
                justification="High HTTPS traffic needs allow rule",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                impact_analysis="Allows HTTPS from any source on port 443",
            )
        ]

    @pytest.fixture
    def _mock_runtime(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        _sample_proposals: list[PolicyProposal],
    ) -> MagicMock:
        """Create a mock Runtime with PipelineContext for generate."""
        from policyfoundry.pipeline.stages.generate import PolicyProposalList

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=_sample_proposals)
        )
        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.adapter = mock_adapter
        return runtime

    @pytest.fixture
    def _mock_state(
        self,
        sample_security_assessment: SecurityAssessment,
        sample_traffic_analysis_dict: dict,
    ) -> PipelineState:
        """Pipeline state with assessment data from previous stage."""
        return PipelineState(
            run_id="test-run",
            current_stage="assess",
            assessment=sample_security_assessment.model_dump(),
            analysis=sample_traffic_analysis_dict,
        )

    async def test_generate_stage_calls_adapter_capabilities(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """generate_stage calls adapter.capabilities()."""
        from policyfoundry.pipeline.stages.generate import generate_stage

        await generate_stage(_mock_state, _mock_runtime)

        _mock_runtime.context.adapter.capabilities.assert_called_once()

    async def test_generate_stage_calls_llm_complete(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """generate_stage calls llm_client.complete."""
        from policyfoundry.pipeline.stages.generate import generate_stage

        await generate_stage(_mock_state, _mock_runtime)

        _mock_runtime.context.llm_client.complete.assert_called_once()
        call_args = _mock_runtime.context.llm_client.complete.call_args
        assert call_args[1]["stage"] == "generate"

    async def test_generate_stage_returns_proposals_list(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
        _sample_proposals: list[PolicyProposal],
    ) -> None:
        """generate_stage returns dict with proposals list."""
        from policyfoundry.pipeline.stages.generate import generate_stage

        result = await generate_stage(_mock_state, _mock_runtime)

        assert result["current_stage"] == "generate"
        assert "proposals" in result
        assert isinstance(result["proposals"], list)
        assert len(result["proposals"]) == len(_sample_proposals)

    async def test_generate_stage_caps_at_20_proposals(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
        _mock_state: PipelineState,
        sample_universal_rules: list[UniversalRule],
    ) -> None:
        """generate_stage caps proposals at 20."""
        from policyfoundry.adapters.schema import RiskLevel
        from policyfoundry.pipeline.stages.generate import PolicyProposalList, generate_stage

        # Create 25 proposals
        big_proposals = [
            PolicyProposal(
                proposal_id=f"prop-{i:03d}",
                rule=sample_universal_rules[0],
                justification=f"Reason {i}",
                risk_level=RiskLevel.LOW,
                confidence=0.8,
                impact_analysis=f"Impact {i}",
            )
            for i in range(25)
        ]

        mock_llm_client.complete = AsyncMock(
            return_value=PolicyProposalList(proposals=big_proposals)
        )

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.adapter = mock_adapter

        result = await generate_stage(_mock_state, runtime)

        assert len(result["proposals"]) == 20


class TestValidateProposals:
    """Tests for the validate_proposals pipeline step."""

    @pytest.fixture
    def _mock_runtime(
        self,
        mock_adapter: MagicMock,
        sample_universal_rules: list[UniversalRule],
    ) -> MagicMock:
        """Create a mock Runtime with adapter for validate."""
        mock_adapter.get_rules = AsyncMock(return_value=sample_universal_rules)
        runtime = MagicMock()
        runtime.context.adapter = mock_adapter
        return runtime

    async def test_validate_calls_adapter_validate_for_each(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """validate_proposals calls adapter.validate for each."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        await validate_proposals(state, _mock_runtime)

        assert _mock_runtime.context.adapter.validate.call_count == len(sample_policy_proposals)

    async def test_validate_removes_invalid_proposals(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """validate_proposals removes proposals with valid=False."""
        from policyfoundry.adapters.schema import ValidationResult
        from policyfoundry.pipeline.stages.validate import validate_proposals

        _mock_runtime.context.adapter.validate = AsyncMock(
            side_effect=[
                ValidationResult(valid=True),
                ValidationResult(valid=False),
                ValidationResult(valid=True),
            ]
        )

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        result = await validate_proposals(state, _mock_runtime)

        assert len(result["proposals"]) == 2

    async def test_validate_keeps_valid_proposals(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """validate_proposals keeps proposals with valid=True."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        result = await validate_proposals(state, _mock_runtime)

        assert len(result["proposals"]) == len(sample_policy_proposals)

    async def test_validate_empty_proposals_returns_empty(
        self,
        _mock_runtime: MagicMock,
    ) -> None:
        """validate_proposals with empty list returns empty."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[],
        )

        result = await validate_proposals(state, _mock_runtime)

        assert result["proposals"] == []
        assert result["current_stage"] == "validate"

    async def test_validate_passes_current_rule_count(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
        sample_universal_rules: list[UniversalRule],
    ) -> None:
        """validate_proposals passes current_rule_count to validate."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        await validate_proposals(state, _mock_runtime)

        for call in _mock_runtime.context.adapter.validate.call_args_list:
            assert call.kwargs["current_rule_count"] == len(sample_universal_rules)


class TestDecideStage:
    """Tests for the decide pipeline stage."""

    @pytest.fixture
    def _mock_runtime(
        self,
        mock_llm_client: MagicMock,
        sample_rule_decisions: list,
    ) -> MagicMock:
        """Create a mock Runtime with PipelineContext for decide."""
        from policyfoundry.pipeline.stages.decide import RuleDecisionList

        mock_llm_client.complete = AsyncMock(
            return_value=RuleDecisionList(decisions=sample_rule_decisions)
        )
        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        return runtime

    @pytest.fixture
    def _mock_state(
        self,
        sample_policy_proposals: list[PolicyProposal],
    ) -> PipelineState:
        """Pipeline state with proposals from previous stage."""
        return PipelineState(
            run_id="test-run",
            current_stage="validate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

    async def test_decide_stage_calls_llm_with_all_proposals(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """decide_stage calls llm_client.complete with proposals."""
        from policyfoundry.pipeline.stages.decide import decide_stage

        await decide_stage(_mock_state, _mock_runtime)

        _mock_runtime.context.llm_client.complete.assert_called_once()
        call_args = _mock_runtime.context.llm_client.complete.call_args
        assert call_args[1]["temperature"] == 0.1
        assert call_args[1]["stage"] == "decide"

    async def test_decide_stage_returns_decisions_list(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
        sample_rule_decisions: list,
    ) -> None:
        """decide_stage returns dict with decisions list."""
        from policyfoundry.pipeline.stages.decide import decide_stage

        result = await decide_stage(_mock_state, _mock_runtime)

        assert result["current_stage"] == "decide"
        assert "decisions" in result
        assert isinstance(result["decisions"], list)
        assert len(result["decisions"]) == len(sample_rule_decisions)

    async def test_decide_stage_empty_proposals_skips_llm(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """decide_stage with empty proposals returns empty decisions without LLM call."""
        from policyfoundry.pipeline.stages.decide import decide_stage

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client

        state = PipelineState(
            run_id="test-run",
            current_stage="validate",
            proposals=[],
        )

        result = await decide_stage(state, runtime)

        assert result["decisions"] == []
        assert result["current_stage"] == "decide"
        mock_llm_client.complete.assert_not_called()

    async def test_decide_stage_single_llm_call(
        self,
        _mock_runtime: MagicMock,
        _mock_state: PipelineState,
    ) -> None:
        """decide_stage calls LLM exactly once (not per-proposal)."""
        from policyfoundry.pipeline.stages.decide import decide_stage

        await decide_stage(_mock_state, _mock_runtime)

        assert _mock_runtime.context.llm_client.complete.call_count == 1


# ---------------------------------------------------------------------------
# VPC validate rejection logging tests
# ---------------------------------------------------------------------------


class TestVpcValidateRejectionLogging:
    """Tests that VPC validate logs rejected proposals."""

    @pytest.fixture
    def _mock_runtime(
        self,
        mock_adapter: MagicMock,
        sample_universal_rules: list[UniversalRule],
    ) -> MagicMock:
        """Create a mock Runtime with adapter for validate."""
        mock_adapter.get_rules = AsyncMock(return_value=sample_universal_rules)
        runtime = MagicMock()
        runtime.context.adapter = mock_adapter
        return runtime

    async def test_logs_warning_on_rejected_proposal(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """Rejected VPC proposal emits logger.warning with proposal_id and reason."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        _mock_runtime.context.adapter.validate = AsyncMock(
            side_effect=[
                ValidationResult(valid=True),
                ValidationResult(
                    valid=False,
                    errors=[ValidationIssue(code="RULE_LIMIT", message="Max rules exceeded", field="rule_count")],
                ),
                ValidationResult(valid=True),
            ],
        )

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        with patch("policyfoundry.pipeline.stages.validate.logger") as mock_logger:
            result = await validate_proposals(state, _mock_runtime)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "prop-002" in str(call_args)
            assert "Max rules exceeded" in str(call_args)
            assert len(result["proposals"]) == 2

    async def test_logs_fallback_reason_when_no_errors(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """Rejected VPC proposal with empty errors logs fallback reason."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        _mock_runtime.context.adapter.validate = AsyncMock(
            side_effect=[
                ValidationResult(valid=False),
                ValidationResult(valid=True),
                ValidationResult(valid=True),
            ],
        )

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        with patch("policyfoundry.pipeline.stages.validate.logger") as mock_logger:
            await validate_proposals(state, _mock_runtime)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "prop-001" in str(call_args)
            assert "validation failed" in str(call_args)

    async def test_no_warning_when_all_valid(
        self,
        _mock_runtime: MagicMock,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """No warnings emitted when all VPC proposals are valid."""
        from policyfoundry.pipeline.stages.validate import validate_proposals

        state = PipelineState(
            run_id="test-run",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        with patch("policyfoundry.pipeline.stages.validate.logger") as mock_logger:
            await validate_proposals(state, _mock_runtime)

            mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# VPC stage error wrapping tests
# ---------------------------------------------------------------------------


class TestVpcStageErrorWrapping:
    """Tests that VPC stage functions wrap non-PipelineError exceptions."""

    async def test_analyze_wraps_runtime_error(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """analyze_stage wraps RuntimeError in PipelineError with stage."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.stages.analyze import analyze_stage

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.data_dir = "/tmp/test-data"

        state = PipelineState(run_id="test", current_stage="starting")

        with (
            patch(f"{_QUERIES_PATH}.traffic_summary", new_callable=AsyncMock, side_effect=RuntimeError("DB connection lost")),
        ):
            with pytest.raises(PipelineError) as exc_info:
                await analyze_stage(state, runtime)

            assert exc_info.value.details["stage"] == "analyze"
            assert "DB connection lost" in str(exc_info.value)
            assert isinstance(exc_info.value.__cause__, RuntimeError)

    async def test_assess_wraps_with_stage_name(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """assess_stage wraps exceptions with stage='assess'."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.stages.assess import assess_stage

        mock_adapter.get_rules = AsyncMock(side_effect=ConnectionError("adapter unreachable"))

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.adapter = mock_adapter

        state = PipelineState(
            run_id="test",
            current_stage="analyze",
            analysis={"summary": "test"},
        )

        with pytest.raises(PipelineError) as exc_info:
            await assess_stage(state, runtime)

        assert exc_info.value.details["stage"] == "assess"
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    async def test_generate_wraps_with_stage_name(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """generate_stage wraps exceptions with stage='generate'."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.stages.generate import generate_stage

        mock_llm_client.complete = AsyncMock(side_effect=ValueError("invalid schema"))

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.adapter = mock_adapter

        state = PipelineState(
            run_id="test",
            current_stage="assess",
            assessment={"overall_risk": "MEDIUM"},
            analysis={"summary": "test"},
        )

        with pytest.raises(PipelineError) as exc_info:
            await generate_stage(state, runtime)

        assert exc_info.value.details["stage"] == "generate"

    async def test_validate_wraps_unexpected_error(
        self,
        mock_adapter: MagicMock,
        sample_universal_rules: list[UniversalRule],
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """validate_proposals wraps unexpected errors with stage='validate'."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.stages.validate import validate_proposals

        mock_adapter.get_rules = AsyncMock(side_effect=OSError("disk error"))
        runtime = MagicMock()
        runtime.context.adapter = mock_adapter

        state = PipelineState(
            run_id="test",
            current_stage="generate",
            proposals=[p.model_dump() for p in sample_policy_proposals],
        )

        with pytest.raises(PipelineError) as exc_info:
            await validate_proposals(state, runtime)

        assert exc_info.value.details["stage"] == "validate"

    async def test_decide_wraps_with_stage_name(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """decide_stage wraps exceptions with stage='decide'."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.stages.decide import decide_stage

        mock_llm_client.complete = AsyncMock(side_effect=TypeError("bad type"))

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client

        state = PipelineState(
            run_id="test",
            current_stage="validate",
            proposals=[{"proposal_id": "p1", "rule": {}, "justification": "test",
                        "risk_level": "LOW", "confidence": 0.5, "impact_analysis": "test"}],
        )

        with pytest.raises(PipelineError) as exc_info:
            await decide_stage(state, runtime)

        assert exc_info.value.details["stage"] == "decide"

    async def test_pipeline_error_not_double_wrapped(
        self,
        mock_llm_client: MagicMock,
        mock_adapter: MagicMock,
    ) -> None:
        """PipelineError raised inside VPC stage is re-raised, not wrapped."""
        from policyfoundry.exceptions import PipelineError
        from policyfoundry.pipeline.stages.assess import assess_stage

        original = PipelineError("original error", details={"stage": "assess", "custom": True})
        mock_adapter.get_rules = AsyncMock(side_effect=original)

        runtime = MagicMock()
        runtime.context.llm_client = mock_llm_client
        runtime.context.adapter = mock_adapter

        state = PipelineState(
            run_id="test",
            current_stage="analyze",
            analysis={"summary": "test"},
        )

        with pytest.raises(PipelineError) as exc_info:
            await assess_stage(state, runtime)

        assert exc_info.value is original
        assert exc_info.value.details.get("custom") is True
