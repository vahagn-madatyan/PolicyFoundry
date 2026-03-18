"""Shared fixtures for pipeline tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    Direction,
    NetworkEndpoint,
    PortRange,
    RuleAction,
    UniversalRule,
    ValidationResult,
)
from policyfoundry.adapters.schema import RiskLevel
from policyfoundry.config.models import LLMConfig
from policyfoundry.pipeline.graph import PipelineContext
from policyfoundry.pipeline.llm import LLMClient
from policyfoundry.pipeline.schema import (
    Anomaly,
    BandwidthOutlier,
    PolicyProposal,
    PortDistributionEntry,
    RiskScore,
    RuleDecision,
    RuleGap,
    SecurityAssessment,
    TopTalker,
    TrafficAnalysis,
)
from policyfoundry.storage.models import (
    DeniedFlowResult,
    TopTalkerResult,
    TrafficByProtocolResult,
    TrafficSummary,
)


@pytest.fixture
def mock_llm_config() -> LLMConfig:
    """Return a standard LLMConfig for testing."""
    return LLMConfig(
        provider="ollama",
        model="llama3.2",
        temperature=0.1,
        base_url="http://localhost:11434",
    )


@pytest.fixture
def mock_instructor_client() -> MagicMock:
    """Return an AsyncMock mimicking Instructor's patched client.

    The client has a ``chat.completions.create_with_completion`` async
    method that can be configured per-test to return ``(model, raw)``
    tuples.
    """
    client = MagicMock()
    client.chat.completions.create_with_completion = AsyncMock()
    return client


@pytest.fixture
def sample_messages() -> list[dict[str, str]]:
    """Return simple LLM messages for testing."""
    return [{"role": "user", "content": "Analyze traffic"}]


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Mock FirewallAdapter for pipeline tests."""
    adapter = MagicMock(spec=FirewallAdapter)
    adapter.get_rules = AsyncMock(return_value=[])
    adapter.validate = AsyncMock(return_value=ValidationResult(valid=True))
    adapter.capabilities = MagicMock(
        return_value=AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
        )
    )
    return adapter


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mock LLMClient with async complete method."""
    client = MagicMock(spec=LLMClient)
    client.complete = AsyncMock()
    return client


@pytest.fixture
def mock_pipeline_context(mock_llm_client: MagicMock, mock_adapter: MagicMock) -> PipelineContext:
    """PipelineContext with mocked dependencies."""
    return PipelineContext(
        llm_client=mock_llm_client,
        adapter=mock_adapter,
        data_dir="/tmp/test-data",
    )


@pytest.fixture
def sample_traffic_analysis() -> TrafficAnalysis:
    """Pre-built TrafficAnalysis with realistic test data."""
    return TrafficAnalysis(
        summary="Moderate inbound traffic with TCP dominance.",
        total_flows=15000,
        unique_sources=42,
        unique_destinations=8,
        top_talkers=[
            TopTalker(ip="10.0.1.50", bytes=5000000, protocol="TCP"),
            TopTalker(ip="10.0.1.75", bytes=3200000, protocol="TCP"),
        ],
        port_distribution=[
            PortDistributionEntry(port=443, protocol="TCP", percentage=68.5),
            PortDistributionEntry(port=80, protocol="TCP", percentage=22.1),
        ],
        anomalies=[],
        bandwidth_outliers=[
            BandwidthOutlier(ip="10.0.1.50", bytes=5000000, reason="3x median"),
        ],
    )


@pytest.fixture
def sample_top_talkers() -> list[TopTalkerResult]:
    """Sample TopTalkerResult list for testing."""
    return [
        TopTalkerResult(src_ip="10.0.1.50", total_bytes=5000000, flow_count=800),
        TopTalkerResult(src_ip="10.0.1.75", total_bytes=3200000, flow_count=500),
        TopTalkerResult(src_ip="10.0.2.10", total_bytes=1100000, flow_count=200),
    ]


@pytest.fixture
def sample_denied_flows() -> list[DeniedFlowResult]:
    """Sample DeniedFlowResult list for testing."""
    return [
        DeniedFlowResult(src_ip="203.0.113.5", dst_ip="10.0.1.50", dst_port=22, protocol="TCP", deny_count=150),
        DeniedFlowResult(src_ip="198.51.100.10", dst_ip="10.0.1.75", dst_port=3389, protocol="TCP", deny_count=45),
    ]


@pytest.fixture
def sample_traffic_by_protocol() -> list[TrafficByProtocolResult]:
    """Sample TrafficByProtocolResult list for testing."""
    return [
        TrafficByProtocolResult(protocol="TCP", total_bytes=8000000, flow_count=12000, percentage=85.5),
        TrafficByProtocolResult(protocol="UDP", total_bytes=1200000, flow_count=2500, percentage=14.5),
    ]


@pytest.fixture
def sample_traffic_summary() -> TrafficSummary:
    """Sample TrafficSummary with realistic counts."""
    return TrafficSummary(
        total_records=15000,
        total_bytes=9200000,
        unique_sources=42,
        unique_destinations=8,
        allowed_count=14500,
        denied_count=500,
        date_range_start="2026-03-01T00:00:00+00:00",
        date_range_end="2026-03-10T23:59:59+00:00",
    )


@pytest.fixture
def sample_security_assessment() -> SecurityAssessment:
    """Pre-built SecurityAssessment with realistic test data."""
    return SecurityAssessment(
        overall_risk=RiskLevel.MEDIUM,
        risk_scores=[
            RiskScore(category="open_ports", score=0.6, description="Several high-risk ports open"),
            RiskScore(category="denied_traffic", score=0.3, description="Moderate denied traffic volume"),
        ],
        rule_gaps=[
            RuleGap(gap_type="missing_rule", description="No rule for SSH traffic from 10.0.1.0/24", severity="MEDIUM"),
        ],
        compliance_findings=["SSH access not restricted to bastion host"],
    )


@pytest.fixture
def sample_traffic_analysis_dict(sample_traffic_analysis: TrafficAnalysis) -> dict:
    """Serialized TrafficAnalysis dict (as stored in PipelineState)."""
    return sample_traffic_analysis.model_dump()


@pytest.fixture
def sample_universal_rules() -> list[UniversalRule]:
    """Two sample UniversalRule instances representing existing SG rules."""
    return [
        UniversalRule(
            id="sgr-001",
            name="allow-https-inbound",
            description="Allow HTTPS inbound from any",
            action=RuleAction.ALLOW,
            direction=Direction.INBOUND,
            protocol="TCP",
            source=[NetworkEndpoint(cidr="0.0.0.0/0")],
            destination=[],
            port_range=PortRange(from_port=443, to_port=443),
        ),
        UniversalRule(
            id="sgr-002",
            name="allow-http-inbound",
            description="Allow HTTP inbound from any",
            action=RuleAction.ALLOW,
            direction=Direction.INBOUND,
            protocol="TCP",
            source=[NetworkEndpoint(cidr="0.0.0.0/0")],
            destination=[],
            port_range=PortRange(from_port=80, to_port=80),
        ),
    ]


@pytest.fixture
def sample_policy_proposals() -> list[PolicyProposal]:
    """Three sample PolicyProposal instances with valid UniversalRules."""
    return [
        PolicyProposal(
            proposal_id="prop-001",
            rule=UniversalRule(
                name="allow-ssh-bastion",
                description="Allow SSH from bastion subnet",
                action=RuleAction.ALLOW,
                direction=Direction.INBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(cidr="10.0.1.0/24")],
                destination=[],
                port_range=PortRange(from_port=22, to_port=22),
            ),
            justification="Repeated denied SSH from bastion subnet",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.85,
            impact_analysis="Allows SSH from 10.0.1.0/24 on port 22",
        ),
        PolicyProposal(
            proposal_id="prop-002",
            rule=UniversalRule(
                name="allow-https-api",
                description="Allow HTTPS to API servers",
                action=RuleAction.ALLOW,
                direction=Direction.INBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(cidr="10.0.2.0/24")],
                destination=[],
                port_range=PortRange(from_port=443, to_port=443),
            ),
            justification="High-volume HTTPS traffic from app tier",
            risk_level=RiskLevel.LOW,
            confidence=0.95,
            impact_analysis="Allows HTTPS from app tier on port 443",
        ),
        PolicyProposal(
            proposal_id="prop-003",
            rule=UniversalRule(
                name="allow-mysql-db",
                description="Allow MySQL from app servers",
                action=RuleAction.ALLOW,
                direction=Direction.INBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(cidr="10.0.2.0/24")],
                destination=[],
                port_range=PortRange(from_port=3306, to_port=3306),
            ),
            justification="Database traffic pattern identified",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.75,
            impact_analysis="Allows MySQL from 10.0.2.0/24 on port 3306",
        ),
    ]


@pytest.fixture
def sample_rule_decisions() -> list[RuleDecision]:
    """Three sample RuleDecision instances: CREATE, UPDATE, and SKIP."""
    return [
        RuleDecision(
            decision_id="dec-001",
            proposal_id="prop-001",
            action="CREATE",
            risk_level=RiskLevel.MEDIUM,
            reason="SSH bastion access needed based on traffic patterns",
            approval_required=True,
        ),
        RuleDecision(
            decision_id="dec-002",
            proposal_id="prop-002",
            action="UPDATE",
            risk_level=RiskLevel.LOW,
            reason="Existing HTTPS rule covers this; update source CIDR",
            approval_required=False,
        ),
        RuleDecision(
            decision_id="dec-003",
            proposal_id="prop-003",
            action="SKIP",
            risk_level=RiskLevel.HIGH,
            reason="MySQL access from app tier conflicts with DB isolation policy",
            approval_required=False,
        ),
    ]
