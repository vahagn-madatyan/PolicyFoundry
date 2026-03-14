# T02: 05-firewall-adapter 02

**Slice:** S05 — **Milestone:** M001

## Description

Implement the AWS Security Group adapter: a thin boto3 client, a stateless rule translator, and the adapter class that ties them together with constraint validation. This delivers the ability to fetch real SG rules and validate proposed changes against AWS constraints.

Purpose: Makes ADAPT-01 (fetch SG rules in universal format) and ADAPT-03 (validate proposed rules) functional. Phase 7 pipeline stages will call get_rules() and validate() on this adapter.
Output: aws_sg/ subpackage with client.py, translator.py, adapter.py, plus comprehensive tests using moto.

## Must-Haves

- [ ] "User can fetch SG rules from AWS and see them as UniversalRule objects"
- [ ] "AWS SG rules with CIDR sources translate to NetworkEndpoint with cidr field"
- [ ] "AWS SG rules with security group references translate to NetworkEndpoint with security_group_id field"
- [ ] "All-traffic rules (protocol -1) translate correctly with no port_range"
- [ ] "ICMP rules do not produce a PortRange (ICMP type/code are not ports)"
- [ ] "Proposed rules with DENY action are rejected (AWS SGs are allow-only)"
- [ ] "Proposed rules with 0.0.0.0/0 or ::/0 source are rejected unless allow_wide_open=True"
- [ ] "Proposed rules exceeding 60-rule limit per direction are rejected"
- [ ] "Invalid protocols, port ranges, and CIDRs are caught by validation"
- [ ] "AWS API errors produce AdapterError with structured context"
- [ ] "AdapterCapabilities reports supports_deny_rules=False and max_rules_per_direction=60"

## Files

- `src/policyfoundry/adapters/aws_sg/__init__.py`
- `src/policyfoundry/adapters/aws_sg/client.py`
- `src/policyfoundry/adapters/aws_sg/translator.py`
- `src/policyfoundry/adapters/aws_sg/adapter.py`
- `pyproject.toml`
- `tests/test_adapters/conftest.py`
- `tests/test_adapters/test_aws_sg_translator.py`
- `tests/test_adapters/test_aws_sg_adapter.py`
- `tests/test_adapters/test_validation.py`
