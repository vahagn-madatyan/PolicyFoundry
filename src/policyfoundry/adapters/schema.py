"""Adapter domain models: UniversalRule and related enums."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class RuleAction(StrEnum):
    """Firewall rule action types."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    DROP = "DROP"
    REJECT = "REJECT"


class Direction(StrEnum):
    """Firewall rule direction."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class RiskLevel(StrEnum):
    """Risk level classification for rules and assessments.

    Retained for pipeline models to import; removed from UniversalRule fields.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PortRange(BaseModel):
    """Port range specification for firewall rules."""

    from_port: int = Field(ge=0, le=65535)
    to_port: int = Field(ge=0, le=65535)


class NetworkEndpoint(BaseModel):
    """Network endpoint identifier for firewall rules.

    At least one of cidr, security_group_id, or tag must be set,
    or is_any must be True.
    """

    cidr: str | None = None
    security_group_id: str | None = None
    tag: dict[str, str] | None = None
    is_any: bool = False

    @model_validator(mode="after")
    def _check_at_least_one_identifier(self) -> Self:
        has_identifier = (
            self.cidr is not None
            or self.security_group_id is not None
            or self.tag is not None
        )

        if not self.is_any and not has_identifier:
            msg = (
                "At least one of cidr, security_group_id, or tag "
                "must be set, or is_any must be True"
            )
            raise ValueError(msg)

        return self


class UniversalRule(BaseModel):
    """Vendor-neutral firewall rule representation."""

    id: str | None = None
    name: str
    description: str
    action: RuleAction
    direction: Direction
    protocol: str
    source: list[NetworkEndpoint] = []
    destination: list[NetworkEndpoint] = []
    port_range: PortRange | None = None
    priority: int | None = None
    zone: str | None = None
    tags: dict[str, str] = {}


class ValidationIssue(BaseModel):
    """Single validation issue (error or warning)."""

    code: str
    message: str
    field: str


class ValidationResult(BaseModel):
    """Result of adapter rule validation."""

    valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []


class AdapterCapabilities(BaseModel):
    """Declares vendor-specific adapter constraints."""

    name: str
    vendor: str
    supports_deny_rules: bool = True
    max_rules_per_direction: int = 60
    supports_l7_app_filtering: bool = False
    allows_all_outbound_default: bool = True
