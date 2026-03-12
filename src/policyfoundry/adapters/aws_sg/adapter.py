"""AWS Security Group adapter implementing FirewallAdapter ABC."""

from __future__ import annotations

import ipaddress

from policyfoundry.adapters.aws_sg.client import AwsSgClient
from policyfoundry.adapters.aws_sg.translator import AwsSgTranslator
from policyfoundry.adapters.base import FirewallAdapter
from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    NetworkEndpoint,
    RuleAction,
    UniversalRule,
    ValidationIssue,
    ValidationResult,
)

_VALID_PROTOCOLS = frozenset({"tcp", "udp", "icmp", "-1"})
_WIDE_OPEN_CIDRS = frozenset({"0.0.0.0/0", "::/0"})


class AwsSecurityGroupAdapter(FirewallAdapter):
    """AWS Security Group adapter.

    Fetches security group rules via boto3, translates them to
    UniversalRule objects, and validates proposed rules against
    AWS SG constraints (allow-only, 60-rule limit, etc.).
    """

    def __init__(self, security_group_id: str, *, region: str | None = None) -> None:
        self._client = AwsSgClient(security_group_id, region=region)
        self._sg_id = security_group_id

    async def get_rules(self) -> list[UniversalRule]:
        """Fetch current SG rules as universal rules.

        Returns:
            List of UniversalRule objects translated from AWS SG rules.

        Raises:
            AdapterAuthenticationError: On AWS auth failures.
            AdapterError: On other AWS API errors.
        """
        raw_rules = await self._client.describe_rules()
        return [AwsSgTranslator.from_sg_rule(r) for r in raw_rules]

    async def validate(
        self,
        rule: UniversalRule,
        *,
        current_rule_count: int = 0,
        allow_wide_open: bool = False,
    ) -> ValidationResult:
        """Validate a proposed rule against AWS SG constraints.

        Checks:
        - DENY/DROP/REJECT actions (AWS SGs are allow-only)
        - 0.0.0.0/0 or ::/0 sources without allow_wide_open flag
        - Rule count at or above max_rules_per_direction (60)
        - Invalid protocol (not tcp/udp/icmp/-1)
        - from_port > to_port in port_range
        - Invalid CIDR notation in source/destination endpoints

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        caps = self.capabilities()

        # Check deny rules (AWS SGs are allow-only)
        if rule.action != RuleAction.ALLOW:
            errors.append(
                ValidationIssue(
                    code="DENY_NOT_SUPPORTED",
                    message="AWS Security Groups only support ALLOW rules",
                    field="action",
                )
            )

        # Check overly permissive sources
        if not allow_wide_open:
            for endpoint in rule.source:
                if endpoint.cidr is None:
                    continue
                if endpoint.cidr in _WIDE_OPEN_CIDRS:
                    errors.append(
                        ValidationIssue(
                            code="OVERLY_PERMISSIVE_SOURCE",
                            message=f"Source {endpoint.cidr} is overly permissive; set allow_wide_open=True to override",
                            field="source",
                        )
                    )

        # Check rule limit
        if current_rule_count >= caps.max_rules_per_direction:
            errors.append(
                ValidationIssue(
                    code="RULE_LIMIT_EXCEEDED",
                    message=f"Rule count {current_rule_count} meets or exceeds limit of {caps.max_rules_per_direction}",
                    field="direction",
                )
            )

        # Check protocol
        if rule.protocol not in _VALID_PROTOCOLS:
            errors.append(
                ValidationIssue(
                    code="INVALID_PROTOCOL",
                    message=f"Protocol '{rule.protocol}' is not valid; must be one of: tcp, udp, icmp, -1",
                    field="protocol",
                )
            )

        # Check port range
        if rule.port_range is not None:
            if rule.port_range.from_port > rule.port_range.to_port:
                errors.append(
                    ValidationIssue(
                        code="INVALID_PORT_RANGE",
                        message=f"from_port ({rule.port_range.from_port}) must not exceed to_port ({rule.port_range.to_port})",
                        field="port_range",
                    )
                )

        # Check CIDR notation
        _validate_cidrs(rule.source, "source", errors)
        _validate_cidrs(rule.destination, "destination", errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def capabilities(self) -> AdapterCapabilities:
        """Return AWS SG adapter capabilities."""
        return AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
            supports_l7_app_filtering=False,
            allows_all_outbound_default=True,
        )


def _validate_cidrs(
    endpoints: list[NetworkEndpoint],
    field: str,
    errors: list[ValidationIssue],
) -> None:
    """Validate CIDR notation in a list of NetworkEndpoints."""
    for endpoint in endpoints:
        if endpoint.cidr is None:
            continue
        try:
            ipaddress.ip_network(endpoint.cidr, strict=False)
        except ValueError:
            errors.append(
                ValidationIssue(
                    code="INVALID_CIDR",
                    message=f"Invalid CIDR notation: '{endpoint.cidr}'",
                    field=field,
                )
            )
