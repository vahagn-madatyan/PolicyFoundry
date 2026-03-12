"""PolicyFoundry adapter layer: schema, ABC, and registry."""

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.registry import AdapterRegistry
from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
    ValidationIssue,
    ValidationResult,
)

__all__ = [
    "AdapterCapabilities",
    "AdapterRegistry",
    "Direction",
    "FirewallAdapter",
    "NetworkEndpoint",
    "PortRange",
    "RiskLevel",
    "RuleAction",
    "UniversalRule",
    "ValidationIssue",
    "ValidationResult",
]
