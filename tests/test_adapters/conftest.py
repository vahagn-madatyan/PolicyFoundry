"""Shared test fixtures for adapter layer tests."""

from typing import Any

import pytest


@pytest.fixture
def valid_network_endpoint_data() -> dict[str, Any]:
    """Return a dict with valid CIDR-based NetworkEndpoint fields."""
    return {"cidr": "10.0.0.0/8"}


@pytest.fixture
def valid_sg_endpoint_data() -> dict[str, Any]:
    """Return a dict with valid security-group-id-based NetworkEndpoint fields."""
    return {"security_group_id": "sg-0123456789abcdef0"}


@pytest.fixture
def valid_validation_issue_data() -> dict[str, Any]:
    """Return a dict with valid ValidationIssue fields."""
    return {
        "code": "INVALID_CIDR",
        "message": "CIDR notation is invalid",
        "field": "source",
    }


@pytest.fixture(autouse=True)
def _aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy AWS credentials for moto in adapter tests."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def cidr_rule_dict() -> dict[str, Any]:
    """AWS SG rule dict with CidrIpv4 source."""
    return {
        "SecurityGroupRuleId": "sgr-cidr-ipv4",
        "GroupId": "sg-test123",
        "IsEgress": False,
        "IpProtocol": "tcp",
        "FromPort": 443,
        "ToPort": 443,
        "CidrIpv4": "10.0.0.0/8",
        "Description": "HTTPS from internal",
        "Tags": [{"Key": "env", "Value": "prod"}],
    }


@pytest.fixture
def sg_ref_rule_dict() -> dict[str, Any]:
    """AWS SG rule dict with security group reference source."""
    return {
        "SecurityGroupRuleId": "sgr-sg-ref",
        "GroupId": "sg-test123",
        "IsEgress": False,
        "IpProtocol": "tcp",
        "FromPort": 80,
        "ToPort": 80,
        "ReferencedGroupInfo": {"GroupId": "sg-source456"},
        "Description": "HTTP from source SG",
        "Tags": [],
    }


@pytest.fixture
def all_traffic_rule_dict() -> dict[str, Any]:
    """AWS SG rule dict for all-traffic (protocol -1)."""
    return {
        "SecurityGroupRuleId": "sgr-all-traffic",
        "GroupId": "sg-test123",
        "IsEgress": True,
        "IpProtocol": "-1",
        "FromPort": -1,
        "ToPort": -1,
        "CidrIpv4": "0.0.0.0/0",
        "Description": "Allow all outbound",
        "Tags": [],
    }


@pytest.fixture
def icmp_rule_dict() -> dict[str, Any]:
    """AWS SG rule dict for ICMP (type/code, not ports)."""
    return {
        "SecurityGroupRuleId": "sgr-icmp",
        "GroupId": "sg-test123",
        "IsEgress": False,
        "IpProtocol": "icmp",
        "FromPort": 8,
        "ToPort": -1,
        "CidrIpv4": "10.0.0.0/8",
        "Description": "ICMP echo request",
        "Tags": [],
    }
