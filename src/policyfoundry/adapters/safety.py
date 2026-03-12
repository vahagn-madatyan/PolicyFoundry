"""ReadOnlyAdapter: safety wrapper that blocks write operations.

Wraps any FirewallAdapter to delegate read operations (get_rules, validate,
capabilities) while raising SafetyError on any write attempt (apply_rule,
apply_rules). Used by the CLI to enforce suggest-only mode.
"""

from __future__ import annotations

from typing import Any

from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    UniversalRule,
    ValidationResult,
)
from policyfoundry.exceptions import SafetyError


class ReadOnlyAdapter(FirewallAdapter):
    """Safety wrapper that delegates reads and blocks writes.

    Wraps another FirewallAdapter, forwarding get_rules(), validate(),
    and capabilities() to the wrapped adapter. Any call to apply_rule()
    or apply_rules() raises SafetyError with error_code
    ``SAFETY_WRITE_BLOCKED``.

    Args:
        wrapped: The underlying FirewallAdapter to delegate reads to.
    """

    def __init__(self, wrapped: FirewallAdapter) -> None:
        self._wrapped = wrapped

    async def get_rules(self) -> list[UniversalRule]:
        """Delegate to wrapped adapter."""
        return await self._wrapped.get_rules()

    async def validate(
        self,
        rule: UniversalRule,
        *,
        current_rule_count: int = 0,
        allow_wide_open: bool = False,
    ) -> ValidationResult:
        """Delegate to wrapped adapter."""
        return await self._wrapped.validate(rule)

    def capabilities(self) -> AdapterCapabilities:
        """Delegate to wrapped adapter."""
        return self._wrapped.capabilities()

    async def apply_rule(self, rule: Any) -> Any:
        """Block write operation with SafetyError."""
        raise SafetyError(
            "Write operations are blocked in read-only mode",
            error_code="SAFETY_WRITE_BLOCKED",
            details={"method": "apply_rule"},
        )

    async def apply_rules(self, rules: Any) -> Any:
        """Block write operation with SafetyError."""
        raise SafetyError(
            "Write operations are blocked in read-only mode",
            error_code="SAFETY_WRITE_BLOCKED",
            details={"method": "apply_rules"},
        )
