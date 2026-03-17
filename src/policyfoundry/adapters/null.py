"""NullAdapter: no-op firewall adapter for pipeline-only mode.

Implements the FirewallAdapter ABC with minimal stubs, preserving
the pipeline contract when no real firewall vendor is configured.
Used in M02's Excel analysis pipeline (no-FW mode, R112).
"""

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    UniversalRule,
    ValidationResult,
)


class NullAdapter(FirewallAdapter):
    """No-op adapter for pipelines that don't target a real firewall.

    - get_rules() always returns an empty list (no existing rules)
    - validate() always returns valid (no vendor constraints to enforce)
    - capabilities() reports a generic "null" adapter with permissive defaults
    """

    async def get_rules(self) -> list[UniversalRule]:
        """Return empty rule list — no firewall to query."""
        return []

    async def validate(
        self,
        rule: UniversalRule,
        *,
        current_rule_count: int = 0,
        allow_wide_open: bool = False,
    ) -> ValidationResult:
        """Always valid — no vendor constraints to enforce."""
        return ValidationResult(valid=True)

    def capabilities(self) -> AdapterCapabilities:
        """Generic capabilities with permissive defaults."""
        return AdapterCapabilities(
            name="null",
            vendor="none",
            supports_deny_rules=True,
            max_rules_per_direction=1000,
            supports_l7_app_filtering=False,
            allows_all_outbound_default=True,
        )
