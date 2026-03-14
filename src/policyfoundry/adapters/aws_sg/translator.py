"""Stateless translator: AWS SecurityGroupRule dict -> UniversalRule."""

from __future__ import annotations

from typing import Any

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RuleAction,
    UniversalRule,
)

_PORT_PROTOCOLS = frozenset({"tcp", "udp"})


class AwsSgTranslator:
    """Translates AWS SecurityGroupRule dicts to UniversalRule models.

    All methods are static -- the translator holds no state.
    """

    @staticmethod
    def from_sg_rule(sg_rule: dict[str, Any]) -> UniversalRule:
        """Convert an AWS SecurityGroupRule dict to a UniversalRule.

        Args:
            sg_rule: Dict as returned by describe_security_group_rules.

        Returns:
            UniversalRule with fields mapped from the AWS rule.
        """
        direction = (
            Direction.OUTBOUND
            if sg_rule.get("IsEgress")
            else Direction.INBOUND
        )

        protocol = sg_rule.get("IpProtocol", "-1")

        endpoint = _build_endpoint(sg_rule)

        port_range = _build_port_range(sg_rule, protocol)

        description = sg_rule.get("Description") or ""

        raw_tags = sg_rule.get("Tags", [])
        tags = {t["Key"]: t["Value"] for t in raw_tags}

        return UniversalRule(
            id=sg_rule.get("SecurityGroupRuleId"),
            name=description,
            description=description,
            action=RuleAction.ALLOW,
            direction=direction,
            protocol=protocol,
            source=[endpoint],
            destination=[],
            port_range=port_range,
            tags=tags,
        )


def _build_endpoint(sg_rule: dict[str, Any]) -> NetworkEndpoint:
    """Build a NetworkEndpoint from an AWS SG rule dict."""

    cidr_v4 = sg_rule.get("CidrIpv4")
    if cidr_v4:
        return NetworkEndpoint(cidr=cidr_v4)

    cidr_v6 = sg_rule.get("CidrIpv6")
    if cidr_v6:
        return NetworkEndpoint(cidr=cidr_v6)

    ref = sg_rule.get("ReferencedGroupInfo")
    if ref:
        return NetworkEndpoint(security_group_id=ref["GroupId"])

    return NetworkEndpoint(is_any=True)


def _build_port_range(sg_rule: dict[str, Any], protocol: str) -> PortRange | None:
    """Build a PortRange for tcp/udp protocols only.

    Returns None for all-traffic (-1), ICMP, and any protocol
    where FromPort/ToPort are absent or sentinel -1 values.
    """

    if protocol not in _PORT_PROTOCOLS:
        return None

    from_port = sg_rule.get("FromPort")
    to_port = sg_rule.get("ToPort")

    if from_port is None or to_port is None:
        return None

    if from_port == -1 or to_port == -1:
        return None

    return PortRange(from_port=from_port, to_port=to_port)
