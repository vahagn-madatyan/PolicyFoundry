"""Tests for AwsSgTranslator: AWS SecurityGroupRule dict -> UniversalRule."""

from typing import Any

from policyfoundry.adapters.aws_sg.translator import AwsSgTranslator
from policyfoundry.adapters.schema import Direction, RuleAction


class TestFromSgRuleCidr:
    """Test CIDR-based endpoint translation."""

    def test_from_sg_rule_cidr_ipv4(self, cidr_rule_dict: dict[str, Any]) -> None:
        """CidrIpv4 field produces NetworkEndpoint with cidr set."""
        rule = AwsSgTranslator.from_sg_rule(cidr_rule_dict)
        assert len(rule.source) == 1
        assert rule.source[0].cidr == "10.0.0.0/8"
        assert rule.source[0].security_group_id is None

    def test_from_sg_rule_cidr_ipv6(self) -> None:
        """CidrIpv6 field produces NetworkEndpoint with cidr set."""
        sg_rule = {
            "SecurityGroupRuleId": "sgr-ipv6",
            "GroupId": "sg-test123",
            "IsEgress": False,
            "IpProtocol": "tcp",
            "FromPort": 443,
            "ToPort": 443,
            "CidrIpv6": "2001:db8::/32",
            "Description": "HTTPS from IPv6",
            "Tags": [],
        }
        rule = AwsSgTranslator.from_sg_rule(sg_rule)
        assert len(rule.source) == 1
        assert rule.source[0].cidr == "2001:db8::/32"


class TestFromSgRuleSgRef:
    """Test security group reference translation."""

    def test_from_sg_rule_sg_reference(self, sg_ref_rule_dict: dict[str, Any]) -> None:
        """ReferencedGroupInfo produces NetworkEndpoint with security_group_id."""
        rule = AwsSgTranslator.from_sg_rule(sg_ref_rule_dict)
        assert len(rule.source) == 1
        assert rule.source[0].security_group_id == "sg-source456"
        assert rule.source[0].cidr is None


class TestFromSgRuleDirection:
    """Test direction mapping."""

    def test_from_sg_rule_direction_inbound(self, cidr_rule_dict: dict[str, Any]) -> None:
        """IsEgress=False maps to Direction.INBOUND."""
        rule = AwsSgTranslator.from_sg_rule(cidr_rule_dict)
        assert rule.direction == Direction.INBOUND

    def test_from_sg_rule_direction_outbound(self, all_traffic_rule_dict: dict[str, Any]) -> None:
        """IsEgress=True maps to Direction.OUTBOUND."""
        rule = AwsSgTranslator.from_sg_rule(all_traffic_rule_dict)
        assert rule.direction == Direction.OUTBOUND


class TestFromSgRuleAction:
    """Test action mapping."""

    def test_from_sg_rule_action_always_allow(self, cidr_rule_dict: dict[str, Any]) -> None:
        """AWS SG rules always translate to ALLOW action."""
        rule = AwsSgTranslator.from_sg_rule(cidr_rule_dict)
        assert rule.action == RuleAction.ALLOW


class TestFromSgRulePortRange:
    """Test port range translation."""

    def test_from_sg_rule_tcp_port_range(self, cidr_rule_dict: dict[str, Any]) -> None:
        """TCP rule with FromPort/ToPort produces PortRange."""
        rule = AwsSgTranslator.from_sg_rule(cidr_rule_dict)
        assert rule.port_range is not None
        assert rule.port_range.from_port == 443
        assert rule.port_range.to_port == 443

    def test_from_sg_rule_udp_port_range(self) -> None:
        """UDP rule with port range produces PortRange."""
        sg_rule = {
            "SecurityGroupRuleId": "sgr-udp",
            "GroupId": "sg-test123",
            "IsEgress": False,
            "IpProtocol": "udp",
            "FromPort": 1024,
            "ToPort": 65535,
            "CidrIpv4": "10.0.0.0/8",
            "Description": "UDP high ports",
            "Tags": [],
        }
        rule = AwsSgTranslator.from_sg_rule(sg_rule)
        assert rule.port_range is not None
        assert rule.port_range.from_port == 1024
        assert rule.port_range.to_port == 65535

    def test_from_sg_rule_all_traffic(self, all_traffic_rule_dict: dict[str, Any]) -> None:
        """Protocol -1 (all traffic) -> protocol='-1', port_range=None."""
        rule = AwsSgTranslator.from_sg_rule(all_traffic_rule_dict)
        assert rule.protocol == "-1"
        assert rule.port_range is None

    def test_from_sg_rule_all_traffic_missing_ports(self) -> None:
        """Protocol -1 with no FromPort/ToPort keys -> no KeyError."""
        sg_rule = {
            "SecurityGroupRuleId": "sgr-all-no-ports",
            "GroupId": "sg-test123",
            "IsEgress": True,
            "IpProtocol": "-1",
            "CidrIpv4": "0.0.0.0/0",
            "Description": "All traffic no port keys",
            "Tags": [],
        }
        rule = AwsSgTranslator.from_sg_rule(sg_rule)
        assert rule.protocol == "-1"
        assert rule.port_range is None

    def test_from_sg_rule_icmp(self, icmp_rule_dict: dict[str, Any]) -> None:
        """ICMP rules do not produce PortRange (type/code are not ports)."""
        rule = AwsSgTranslator.from_sg_rule(icmp_rule_dict)
        assert rule.protocol == "icmp"
        assert rule.port_range is None


class TestFromSgRuleMetadata:
    """Test metadata field mapping."""

    def test_from_sg_rule_description(self, cidr_rule_dict: dict[str, Any]) -> None:
        """Description maps to both name and description fields."""
        rule = AwsSgTranslator.from_sg_rule(cidr_rule_dict)
        assert rule.name == "HTTPS from internal"
        assert rule.description == "HTTPS from internal"

    def test_from_sg_rule_id(self, cidr_rule_dict: dict[str, Any]) -> None:
        """SecurityGroupRuleId maps to id field."""
        rule = AwsSgTranslator.from_sg_rule(cidr_rule_dict)
        assert rule.id == "sgr-cidr-ipv4"
