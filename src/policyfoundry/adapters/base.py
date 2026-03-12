"""FirewallAdapter abstract base class."""

from abc import ABC, abstractmethod

from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    UniversalRule,
    ValidationResult,
)


class FirewallAdapter(ABC):
    """Abstract base class for vendor-specific firewall adapters.

    Defines the read + validate contract:
    - get_rules(): fetch current firewall rules in universal format
    - validate(): check a proposed rule against vendor constraints
    - capabilities(): declare adapter-specific constraints
    """

    @abstractmethod
    async def get_rules(self) -> list[UniversalRule]:
        """Fetch current firewall rules as universal rules."""

    @abstractmethod
    async def validate(
        self,
        rule: UniversalRule,
        *,
        current_rule_count: int = 0,
        allow_wide_open: bool = False,
    ) -> ValidationResult:
        """Validate a proposed rule against vendor constraints."""

    @abstractmethod
    def capabilities(self) -> AdapterCapabilities:
        """Return adapter-specific capabilities and constraints."""
