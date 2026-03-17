"""Pipeline LLM output models for traffic analysis and policy generation."""

from enum import StrEnum

from pydantic import BaseModel, Field

from policyfoundry.adapters.schema import RiskLevel, UniversalRule


class DecisionAction(StrEnum):
    """Valid actions for a rule decision.

    Uses ``StrEnum`` so values serialize as plain strings — critical for
    Instructor structured-output compatibility and downstream ``.upper()``
    comparisons.
    """

    CREATE = "CREATE"
    SKIP = "SKIP"
    UPDATE = "UPDATE"


class TrafficAnalysis(BaseModel):
    """LLM-generated traffic analysis summary from flow log data."""

    summary: str
    total_flows: int = Field(ge=0)
    unique_sources: int = Field(ge=0)
    unique_destinations: int = Field(ge=0)
    top_talkers: list[dict]
    port_distribution: list[dict]
    anomalies: list[dict]
    bandwidth_outliers: list[dict]


class SecurityAssessment(BaseModel):
    """LLM-generated security risk assessment."""

    overall_risk: RiskLevel
    risk_scores: list[dict]
    rule_gaps: list[dict]
    compliance_findings: list[str] = Field(default_factory=list)


class PolicyProposal(BaseModel):
    """LLM-generated firewall policy proposal with nested UniversalRule."""

    proposal_id: str
    rule: UniversalRule
    justification: str
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    impact_analysis: str


class RuleDecision(BaseModel):
    """LLM-generated decision on a policy proposal."""

    decision_id: str
    proposal_id: str
    action: DecisionAction
    risk_level: RiskLevel
    reason: str
    approval_required: bool = True
