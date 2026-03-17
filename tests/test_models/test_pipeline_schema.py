"""Tests for pipeline LLM output models."""

from typing import Any

import pytest
from pydantic import ValidationError

from policyfoundry.pipeline.schema import (
    DecisionAction,
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)


def test_valid_traffic_analysis() -> None:
    """TrafficAnalysis accepts valid data with all fields populated."""
    ta = TrafficAnalysis(
        summary="High SSH traffic from external sources",
        total_flows=1500,
        unique_sources=42,
        unique_destinations=10,
        top_talkers=[{"ip": "10.0.1.5", "flows": 300}],
        port_distribution=[{"port": 22, "count": 800}],
        anomalies=[{"type": "port_scan", "source": "203.0.113.5"}],
        bandwidth_outliers=[{"ip": "10.0.1.5", "bytes": 50000000}],
    )
    assert ta.summary == "High SSH traffic from external sources"
    assert ta.total_flows == 1500
    assert ta.unique_sources == 42
    assert ta.unique_destinations == 10
    assert len(ta.top_talkers) == 1
    assert len(ta.port_distribution) == 1
    assert len(ta.anomalies) == 1
    assert len(ta.bandwidth_outliers) == 1


def test_traffic_analysis_negative_counts_rejected() -> None:
    """TrafficAnalysis rejects negative values for count fields."""
    base = {
        "summary": "test",
        "total_flows": 0,
        "unique_sources": 0,
        "unique_destinations": 0,
        "top_talkers": [],
        "port_distribution": [],
        "anomalies": [],
        "bandwidth_outliers": [],
    }
    with pytest.raises(ValidationError):
        TrafficAnalysis(**{**base, "total_flows": -1})

    with pytest.raises(ValidationError):
        TrafficAnalysis(**{**base, "unique_sources": -1})

    with pytest.raises(ValidationError):
        TrafficAnalysis(**{**base, "unique_destinations": -1})


def test_traffic_analysis_list_fields() -> None:
    """TrafficAnalysis list fields accept lists of dicts."""
    ta = TrafficAnalysis(
        summary="test",
        total_flows=0,
        unique_sources=0,
        unique_destinations=0,
        top_talkers=[{"ip": "10.0.0.1", "flows": 100}, {"ip": "10.0.0.2", "flows": 50}],
        port_distribution=[{"port": 80, "count": 500}],
        anomalies=[{"ip": "10.0.0.1", "bytes": 999999}],
        bandwidth_outliers=[],
    )
    assert len(ta.top_talkers) == 2
    assert len(ta.anomalies) == 1
    assert len(ta.bandwidth_outliers) == 0


def test_valid_security_assessment() -> None:
    """SecurityAssessment accepts valid data with all fields populated."""
    sa = SecurityAssessment(
        overall_risk="HIGH",
        risk_scores=[{"category": "open_ports", "score": 8.5}],
        rule_gaps=[{"description": "No egress filtering"}],
        compliance_findings=["CIS 4.1 - Restrict SSH access"],
    )
    assert sa.overall_risk == "HIGH"
    assert len(sa.risk_scores) == 1
    assert len(sa.rule_gaps) == 1
    assert sa.compliance_findings == ["CIS 4.1 - Restrict SSH access"]


def test_security_assessment_risk_levels() -> None:
    """SecurityAssessment accepts all RiskLevel values for overall_risk."""
    base = {"risk_scores": [], "rule_gaps": []}
    for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        sa = SecurityAssessment(**{**base, "overall_risk": level})
        assert sa.overall_risk == level


def test_security_assessment_default_compliance() -> None:
    """SecurityAssessment compliance_findings defaults to empty list."""
    sa = SecurityAssessment(
        overall_risk="LOW",
        risk_scores=[],
        rule_gaps=[],
    )
    assert sa.compliance_findings == []


def test_valid_policy_proposal() -> None:
    """PolicyProposal accepts valid data including nested UniversalRule."""
    pp = PolicyProposal(
        proposal_id="prop-001",
        rule={
            "name": "Allow HTTPS inbound",
            "description": "Allow inbound HTTPS traffic",
            "action": "ALLOW",
            "direction": "INBOUND",
            "protocol": "TCP",
            "port_range": {"from_port": 443, "to_port": 443},
            "risk_level": "LOW",
        },
        justification="High volume of HTTPS traffic observed",
        risk_level="LOW",
        confidence=0.95,
        impact_analysis="Enables HTTPS traffic from all sources",
    )
    assert pp.proposal_id == "prop-001"
    assert pp.rule.name == "Allow HTTPS inbound"
    assert pp.rule.protocol == "TCP"
    assert pp.confidence == 0.95


def test_proposal_confidence_range() -> None:
    """PolicyProposal confidence must be 0.0-1.0; boundary and out-of-range tested."""
    base = {
        "proposal_id": "prop-001",
        "rule": {
            "name": "test",
            "description": "test",
            "action": "ALLOW",
            "direction": "INBOUND",
            "protocol": "TCP",
        },
        "justification": "test",
        "risk_level": "LOW",
        "impact_analysis": "test",
    }
    pp_zero = PolicyProposal(**{**base, "confidence": 0.0})
    assert pp_zero.confidence == 0.0

    pp_one = PolicyProposal(**{**base, "confidence": 1.0})
    assert pp_one.confidence == 1.0

    with pytest.raises(ValidationError):
        PolicyProposal(**{**base, "confidence": -0.1})

    with pytest.raises(ValidationError):
        PolicyProposal(**{**base, "confidence": 1.1})


def test_valid_rule_decision() -> None:
    """RuleDecision accepts valid data with all fields populated."""
    rd = RuleDecision(
        decision_id="dec-001",
        proposal_id="prop-001",
        action="CREATE",
        risk_level="LOW",
        reason="Low risk, high confidence proposal",
        approval_required=False,
    )
    assert rd.decision_id == "dec-001"
    assert rd.proposal_id == "prop-001"
    assert rd.action == "CREATE"
    assert rd.reason == "Low risk, high confidence proposal"
    assert rd.approval_required is False


def test_rule_decision_defaults() -> None:
    """RuleDecision approval_required defaults to True."""
    rd = RuleDecision(
        decision_id="dec-002",
        proposal_id="prop-002",
        action="SKIP",
        risk_level="HIGH",
        reason="High risk requires review",
    )
    assert rd.approval_required is True


# ---------------------------------------------------------------------------
# DecisionAction enum
# ---------------------------------------------------------------------------


class TestDecisionAction:
    """DecisionAction StrEnum tests."""

    @pytest.mark.parametrize("value", ["CREATE", "SKIP", "UPDATE"])
    def test_valid_members(self, value: str) -> None:
        """DecisionAction accepts valid action strings."""
        action = DecisionAction(value)
        assert action == value
        assert isinstance(action, str)

    def test_is_strenum(self) -> None:
        """DecisionAction is a StrEnum — critical for Instructor compat."""
        assert issubclass(DecisionAction, str)
        assert DecisionAction.CREATE.upper() == "CREATE"

    def test_invalid_action_rejected(self) -> None:
        """DecisionAction rejects unknown action strings."""
        with pytest.raises(ValueError):
            DecisionAction("INVALID")


class TestRuleDecisionEnum:
    """RuleDecision validates action against DecisionAction enum."""

    _base: dict[str, Any] = {
        "decision_id": "dec-001",
        "proposal_id": "prop-001",
        "risk_level": "LOW",
        "reason": "test",
    }

    def test_valid_action_accepted(self) -> None:
        """RuleDecision accepts a valid DecisionAction string."""
        rd = RuleDecision(**{**self._base, "action": "CREATE"})
        assert rd.action == DecisionAction.CREATE
        assert isinstance(rd.action, DecisionAction)

    def test_invalid_action_rejected(self) -> None:
        """RuleDecision rejects an action string not in the enum."""
        with pytest.raises(ValidationError):
            RuleDecision(**{**self._base, "action": "INVALID"})

    @pytest.mark.parametrize("action", ["CREATE", "SKIP", "UPDATE"])
    def test_all_actions_accepted(self, action: str) -> None:
        """RuleDecision accepts all three DecisionAction values."""
        rd = RuleDecision(**{**self._base, "action": action})
        assert rd.action == action
