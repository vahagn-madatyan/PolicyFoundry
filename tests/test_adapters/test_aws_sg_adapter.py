"""Integration tests for AwsSecurityGroupAdapter using moto mock_aws."""

import boto3
import pytest
from moto import mock_aws

from policyfoundry.adapters.aws_sg.adapter import AwsSecurityGroupAdapter
from policyfoundry.adapters.schema import Direction, RuleAction
from policyfoundry.exceptions import AdapterError


def _create_sg_with_rules() -> str:
    """Create a VPC and SG with an inbound HTTPS rule, return SG ID."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    sg = ec2.create_security_group(
        GroupName="test-sg",
        Description="Test security group",
        VpcId=vpc_id,
    )
    sg_id = sg["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [
                    {"CidrIp": "10.0.0.0/8", "Description": "HTTPS from internal"}
                ],
            }
        ],
    )
    return sg_id


class TestGetRules:
    """Test get_rules() with moto mock AWS."""

    async def test_get_rules_returns_universal_rules(self) -> None:
        """get_rules() returns UniversalRule objects with correct fields."""
        with mock_aws():
            sg_id = _create_sg_with_rules()
            adapter = AwsSecurityGroupAdapter(
                sg_id, region="us-east-1"
            )

            rules = await adapter.get_rules()

            assert len(rules) >= 2  # At least ingress + default egress

            # Find the HTTPS inbound rule
            https_rules = [
                r for r in rules
                if r.direction == Direction.INBOUND and r.protocol == "tcp"
            ]
            assert len(https_rules) == 1
            https_rule = https_rules[0]
            assert https_rule.action == RuleAction.ALLOW
            assert https_rule.port_range is not None
            assert https_rule.port_range.from_port == 443
            assert https_rule.port_range.to_port == 443
            assert len(https_rule.source) == 1
            assert https_rule.source[0].cidr == "10.0.0.0/8"

    async def test_get_rules_includes_default_egress(self) -> None:
        """New SG has default allow-all outbound rule in get_rules()."""
        with mock_aws():
            ec2 = boto3.client("ec2", region_name="us-east-1")
            vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
            sg = ec2.create_security_group(
                GroupName="empty-sg",
                Description="Empty SG",
                VpcId=vpc["Vpc"]["VpcId"],
            )
            sg_id = sg["GroupId"]
            adapter = AwsSecurityGroupAdapter(sg_id, region="us-east-1")

            rules = await adapter.get_rules()

            egress_rules = [
                r for r in rules if r.direction == Direction.OUTBOUND
            ]
            assert len(egress_rules) >= 1

    async def test_get_rules_empty_sg(self) -> None:
        """SG with no custom rules returns only default egress."""
        with mock_aws():
            ec2 = boto3.client("ec2", region_name="us-east-1")
            vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
            sg = ec2.create_security_group(
                GroupName="minimal-sg",
                Description="Minimal SG",
                VpcId=vpc["Vpc"]["VpcId"],
            )
            sg_id = sg["GroupId"]
            adapter = AwsSecurityGroupAdapter(sg_id, region="us-east-1")

            rules = await adapter.get_rules()

            assert len(rules) >= 1
            assert all(r.direction == Direction.OUTBOUND for r in rules)


class TestCapabilities:
    """Test capabilities() returns correct static values."""

    def test_capabilities_static(self) -> None:
        """capabilities() returns AWS SG constraints."""
        adapter = AwsSecurityGroupAdapter("sg-test123", region="us-east-1")
        caps = adapter.capabilities()
        assert caps.name == "aws_sg"
        assert caps.vendor == "AWS"
        assert caps.supports_deny_rules is False
        assert caps.max_rules_per_direction == 60
        assert caps.supports_l7_app_filtering is False
        assert caps.allows_all_outbound_default is True


class TestErrorHandling:
    """Test error handling for AWS API failures."""

    async def test_get_rules_invalid_sg_id(self) -> None:
        """Malformed SG ID raises AdapterError."""
        with mock_aws():
            adapter = AwsSecurityGroupAdapter("sg-nonexistent99999", region="us-east-1")
            with pytest.raises(AdapterError) as exc_info:
                await adapter.get_rules()
            assert exc_info.value.details["sg_id"] == "sg-nonexistent99999"

    async def test_get_rules_handles_client_error(self) -> None:
        """AdapterError wraps AWS API errors with context."""
        with mock_aws():
            adapter = AwsSecurityGroupAdapter("sg-test123", region="us-east-1")

            original = adapter._client._client.describe_security_group_rules

            def mock_describe(**_kwargs: object) -> None:
                from botocore.exceptions import ClientError

                raise ClientError(
                    {"Error": {"Code": "InvalidGroup.NotFound", "Message": "SG not found"}},
                    "DescribeSecurityGroupRules",
                )

            adapter._client._client.describe_security_group_rules = mock_describe  # type: ignore[assignment]

            with pytest.raises(AdapterError) as exc_info:
                await adapter.get_rules()

            assert exc_info.value.error_code == "InvalidGroup.NotFound"
            assert "sg_id" in exc_info.value.details
