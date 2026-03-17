"""Shared fixtures for export tests.

Provides ExcelPipelineState dicts with proposals+decisions populated,
plus an empty variant for edge-case testing.
"""

from __future__ import annotations

from typing import Any

import pytest

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
)
from policyfoundry.pipeline.excel_state import ExcelPipelineState
from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)


@pytest.fixture
def sample_excel_state() -> ExcelPipelineState:
    """Full ExcelPipelineState with proposals+decisions for export tests.

    Includes:
    - prop-001: SSH allow (CREATE, MEDIUM risk, approval_required=True)
    - prop-002: HTTPS allow (UPDATE, LOW risk, approval_required=False)
    - prop-003: MySQL allow (SKIP — should be filtered out by flatten)
    """
    analysis = TrafficAnalysis(
        summary="Mixed traffic with HTTPS dominance and SSH access.",
        total_flows=965,
        unique_sources=3,
        unique_destinations=3,
        top_talkers=[{"ip": "10.0.1.50", "flow_count": 800, "protocol": "TCP"}],
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
            {"category": "inferred_gaps", "score": 0.5, "description": "SSH access pattern"},
        ],
        rule_gaps=[],
        compliance_findings=[],
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
                source=[
                    NetworkEndpoint(cidr="10.0.1.0/24"),
                    NetworkEndpoint(cidr="10.0.2.0/24"),
                ],
                destination=[NetworkEndpoint(cidr="10.0.3.10/32")],
                port_range=PortRange(from_port=22, to_port=22),
            ),
            justification="Repeated denied SSH from bastion subnet",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.85,
            impact_analysis="Allows SSH from bastion subnets",
        ),
        PolicyProposal(
            proposal_id="prop-002",
            rule=UniversalRule(
                name="allow-https-api",
                description="Allow HTTPS to API servers",
                action=RuleAction.ALLOW,
                direction=Direction.OUTBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(is_any=True)],
                destination=[NetworkEndpoint(security_group_id="sg-abc123")],
                port_range=PortRange(from_port=443, to_port=443),
            ),
            justification="High-volume HTTPS traffic from app tier",
            risk_level=RiskLevel.LOW,
            confidence=0.95,
            impact_analysis="Allows HTTPS to API tier",
        ),
        PolicyProposal(
            proposal_id="prop-003",
            rule=UniversalRule(
                name="allow-mysql",
                description="Allow MySQL to DB servers",
                action=RuleAction.ALLOW,
                direction=Direction.INBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(tag={"env": "prod"})],
                destination=[],
                port_range=PortRange(from_port=3306, to_port=3306),
            ),
            justification="DB access from prod tier",
            risk_level=RiskLevel.HIGH,
            confidence=0.6,
            impact_analysis="Opens MySQL access",
        ),
    ]

    decisions = [
        RuleDecision(
            decision_id="dec-001",
            proposal_id="prop-001",
            action="CREATE",
            risk_level=RiskLevel.MEDIUM,
            reason="SSH bastion access needed",
            approval_required=True,
        ),
        RuleDecision(
            decision_id="dec-002",
            proposal_id="prop-002",
            action="UPDATE",
            risk_level=RiskLevel.LOW,
            reason="Update existing HTTPS rule source",
            approval_required=False,
        ),
        RuleDecision(
            decision_id="dec-003",
            proposal_id="prop-003",
            action="SKIP",
            risk_level=RiskLevel.HIGH,
            reason="MySQL conflicts with DB isolation policy",
            approval_required=True,
        ),
    ]

    state: ExcelPipelineState = {
        "run_id": "run-export-test-001",
        "started_at": "2026-03-15T09:00:00+00:00",
        "current_stage": "decide",
        "aggregated_flows": [],
        "subnet_groups": [],
        "analysis": analysis.model_dump(),
        "assessment": assessment.model_dump(),
        "proposals": [p.model_dump() for p in proposals],
        "decisions": [d.model_dump() for d in decisions],
        "token_usage": {
            "prompt_tokens": 3000,
            "completion_tokens": 1200,
            "total_tokens": 4200,
            "total_cost": 0.0030,
            "per_stage": [],
        },
    }
    return state


@pytest.fixture
def sample_excel_state_empty() -> ExcelPipelineState:
    """Minimal ExcelPipelineState with no proposals/decisions.

    Tests export behavior with empty rule data (metadata only).
    """
    state: ExcelPipelineState = {
        "run_id": "run-export-empty-001",
        "started_at": "2026-03-15T09:00:00+00:00",
        "current_stage": "decide",
    }
    return state
