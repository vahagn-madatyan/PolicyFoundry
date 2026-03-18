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


# --- TrafficAnalysis sub-models -------------------------------------------


class TopTalker(BaseModel):
    """A high-volume source or destination IP."""

    ip: str
    bytes: int = Field(ge=0, default=0)
    flows: int = Field(ge=0, default=0)
    protocol: str = ""


class PortDistributionEntry(BaseModel):
    """Port usage statistics."""

    port: int = Field(ge=0, le=65535)
    protocol: str = ""
    count: int = Field(ge=0, default=0)
    percentage: float = Field(ge=0.0, le=100.0, default=0.0)


class Anomaly(BaseModel):
    """A detected traffic anomaly."""

    type: str = ""
    description: str = ""
    source: str = ""
    severity: str = ""


class BandwidthOutlier(BaseModel):
    """A source/destination with disproportionate bandwidth."""

    ip: str
    bytes: int = Field(ge=0, default=0)
    reason: str = ""
    z_score: float = 0.0


# --- SecurityAssessment sub-models ----------------------------------------


class RiskScore(BaseModel):
    """Risk score for a security category."""

    category: str
    score: float = Field(ge=0.0)
    description: str = ""


class RuleGap(BaseModel):
    """A gap in the current firewall ruleset."""

    gap_type: str = ""
    description: str
    severity: str = ""


# --- Top-level pipeline models --------------------------------------------


class TrafficAnalysis(BaseModel):
    """LLM-generated traffic analysis summary from flow log data."""

    summary: str
    total_flows: int = Field(ge=0)
    unique_sources: int = Field(ge=0)
    unique_destinations: int = Field(ge=0)
    top_talkers: list[TopTalker]
    port_distribution: list[PortDistributionEntry]
    anomalies: list[Anomaly]
    bandwidth_outliers: list[BandwidthOutlier]


class SecurityAssessment(BaseModel):
    """LLM-generated security risk assessment."""

    overall_risk: RiskLevel
    risk_scores: list[RiskScore]
    rule_gaps: list[RuleGap]
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
