"""Shared fixtures for output formatter tests.

Provides realistic PipelineState dicts with all 4 stage outputs populated,
plus variants for missing token_usage and minimal/empty state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
)
from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)
from policyfoundry.pipeline.state import PipelineState

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_pipeline_state() -> PipelineState:
    """Full PipelineState with all 4 stages populated and token_usage.

    Contains realistic data matching what the pipeline runner would produce
    after running all stages (analyze → assess → generate → decide).
    """
    analysis = TrafficAnalysis(
        summary="Moderate inbound traffic with TCP dominance on ports 443 and 80.",
        total_flows=15000,
        unique_sources=42,
        unique_destinations=8,
        top_talkers=[
            {"ip": "10.0.1.50", "bytes": 5000000, "protocol": "TCP"},
            {"ip": "10.0.1.75", "bytes": 3200000, "protocol": "TCP"},
        ],
        port_distribution=[
            {"port": 443, "protocol": "TCP", "percentage": 68.5},
            {"port": 80, "protocol": "TCP", "percentage": 22.1},
        ],
        anomalies=[],
        bandwidth_outliers=[
            {"ip": "10.0.1.50", "bytes": 5000000, "reason": "3x median"},
        ],
    )

    assessment = SecurityAssessment(
        overall_risk=RiskLevel.MEDIUM,
        risk_scores=[
            {"category": "open_ports", "score": 0.6, "description": "Several high-risk ports open"},
            {"category": "denied_traffic", "score": 0.3, "description": "Moderate denied traffic volume"},
        ],
        rule_gaps=[
            {
                "gap_type": "missing_rule",
                "description": "No rule for SSH traffic from 10.0.1.0/24",
                "severity": "MEDIUM",
            },
        ],
        compliance_findings=[
            "SSH access not restricted to bastion host",
        ],
    )

    proposals = [
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
    ]

    decisions = [
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
            reason="MySQL access conflicts with DB isolation policy",
            approval_required=True,
        ),
    ]

    state: PipelineState = {
        "run_id": "run-test-20260311-001",
        "started_at": "2026-03-11T10:00:00+00:00",
        "current_stage": "decide",
        "flow_log_path": "/data/test-data/flowlogs.parquet",
        "sg_ids": ["sg-abc123"],
        "analysis": analysis.model_dump(),
        "assessment": assessment.model_dump(),
        "proposals": [p.model_dump() for p in proposals],
        "decisions": [d.model_dump() for d in decisions],
        "token_usage": {
            "prompt_tokens": 4200,
            "completion_tokens": 1800,
            "total_tokens": 6000,
            "total_cost": 0.0042,
            "per_stage": [
                {"stage": "analyze", "prompt_tokens": 1500, "completion_tokens": 600, "total_tokens": 2100, "cost": 0.0015},
                {"stage": "assess", "prompt_tokens": 1200, "completion_tokens": 500, "total_tokens": 1700, "cost": 0.0012},
                {"stage": "generate", "prompt_tokens": 800, "completion_tokens": 400, "total_tokens": 1200, "cost": 0.0008},
                {"stage": "decide", "prompt_tokens": 700, "completion_tokens": 300, "total_tokens": 1000, "cost": 0.0007},
            ],
        },
    }

    return state


@pytest.fixture
def sample_pipeline_state_no_tokens(sample_pipeline_state: PipelineState) -> PipelineState:
    """PipelineState with all stages but no token_usage key.

    Tests backward compatibility when token tracking is unavailable.
    """
    state = dict(sample_pipeline_state)
    state.pop("token_usage")
    return state  # type: ignore[return-value]


@pytest.fixture
def sample_pipeline_state_empty() -> PipelineState:
    """Minimal PipelineState with only run_id, started_at, current_stage.

    Tests rendering with missing stage outputs — formatters must handle
    absent analysis/assessment/proposals/decisions gracefully.
    """
    state: PipelineState = {
        "run_id": "run-empty-20260311-001",
        "started_at": "2026-03-11T10:00:00+00:00",
        "current_stage": "analyze",
    }
    return state
