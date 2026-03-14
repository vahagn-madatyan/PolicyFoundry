# Phase 5: Firewall Adapter - Research

**Researched:** 2026-03-10
**Domain:** AWS Security Groups, Adapter Pattern, Plugin Architecture, Pydantic v2 Validation
**Confidence:** HIGH

## Summary

Phase 5 implements the firewall adapter layer: an async abstract base class (`FirewallAdapter`) with a concrete AWS Security Group implementation, a vendor-neutral rule schema (`UniversalRule` with `NetworkEndpoint`), constraint validation, adapter capability declaration, and entry-point-based plugin discovery. The scope is read + validate only -- no apply/rollback/dry_run methods.

The existing codebase already has a basic `UniversalRule`, `RuleAction`, `Direction`, `RiskLevel`, and `PortRange` in `adapters/schema.py`, plus `AdapterError` in `exceptions.py`, and an established `asyncio.to_thread` pattern for wrapping boto3 calls (from Phase 3 S3 ingestion). The work involves enriching the schema (adding `NetworkEndpoint`, extending `RuleAction`, adding new fields), creating the ABC, building the AWS SG adapter with translator, adding validation logic, and wiring up entry-point plugin discovery.

All AWS EC2 security group APIs needed (`describe_security_group_rules`, `create_security_group`, `authorize_security_group_ingress`) are fully supported by moto 5.1.22 (already installed). The `describe_security_group_rules` API (preferred over `describe_security_groups`) returns flat per-rule objects with `SecurityGroupRuleId`, `IsEgress`, `IpProtocol`, `FromPort`, `ToPort`, `CidrIpv4`, `CidrIpv6`, `ReferencedGroupInfo`, and `Description` -- ideal for translation to `UniversalRule`.

**Primary recommendation:** Use `describe_security_group_rules` with group-id filter for fetching rules; translate each `SecurityGroupRule` to a `UniversalRule` via a stateless `AwsSgTranslator` class; validate proposed rules against AWS SG constraints using a `ValidationResult` Pydantic model with structured error codes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Read + validate only: implement get_rules(), validate(), and capabilities() methods
- No apply, rollback, or dry_run -- skip entirely, no stubs or dead code
- Add write lifecycle methods when suggest-only mode graduates to auto-apply
- Async ABC: all adapter methods are async (boto3 calls via asyncio.to_thread, consistent with Phase 3 S3 pattern)
- Static capabilities: capabilities() returns a fixed AdapterCapabilities object, no runtime AWS queries
- Entry-point plugin discovery via Python setuptools entry_points
- Third-party packages can register adapters automatically
- Built-in AWS SG adapter registered as a default entry point
- Full architecture plan schema: implement the complete vendor-neutral representation
- Add NetworkEndpoint model (cidr, security_group_id, tag, is_any) -- replaces plain string lists
- source/destination become list[NetworkEndpoint] instead of list[str]
- Add all four RuleAction values: ALLOW, DENY, DROP, REJECT
- Keep zone, tags dict, priority fields from arch plan
- Defer AI metadata (ai_confidence, justification) to Phase 7 -- lives on pipeline models (PolicyProposal), not UniversalRule
- Default boto3 credential chain (env vars, ~/.aws/credentials, IAM role)
- Region from standard AWS resolution (AWS_DEFAULT_REGION, config)
- No custom auth code or config-driven profile selection
- Consistent with Phase 3 S3 approach
- One Security Group per adapter instance
- SG ID provided at adapter construction (from config)
- Multiple SGs = multiple adapter instances
- Preserve SG references in rules as-is (NetworkEndpoint with security_group_id) -- don't resolve to CIDRs
- ValidationResult Pydantic model: valid (bool), errors (list), warnings (list)
- Each error/warning has code + message + field -- structured, machine-readable
- 0.0.0.0/0: reject unless explicit allow_wide_open=True flag passed
- 60-rule limit: validate() takes current_rule_count and rejects if adding proposed rule exceeds limit
- DENY action: reject (AWS SGs are allow-only)
- Additional checks: valid protocol (tcp/udp/icmp/-1), valid port ranges (0-65535, from <= to), valid CIDR notation
- moto for mocking EC2 describe_security_groups (consistent with Phase 3 S3 testing)
- Tests run offline, deterministic

### Claude's Discretion
- Exact AdapterCapabilities field set beyond what's discussed
- Entry-point group name and registration mechanism details
- boto3 client wrapper implementation details
- AWS IpPermission to UniversalRule translator implementation
- Error handling for AWS API failures (retries, error classification)
- Exact ValidationResult error/warning code naming convention

### Deferred Ideas (OUT OF SCOPE)
- Excel input for rule/policy suggestions -- new input source, belongs in its own phase
- Change request output format for other teams to implement -- new output format, belongs in its own phase
- Palo Alto Cloud NGFW adapter -- explicitly out of scope per PROJECT.md (Phase 2+)
- Config-driven AWS profile selection -- add when multi-account support is needed
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADAPT-01 | User can fetch current AWS Security Group rules and view them in universal format | `describe_security_group_rules` API returns per-rule objects; `AwsSgTranslator.from_sg_rule()` converts each to `UniversalRule`; `get_rules()` on adapter wraps the full flow |
| ADAPT-02 | Rules are represented in a vendor-neutral universal schema extensible to other firewall vendors | Enriched `UniversalRule` with `NetworkEndpoint` (CIDR, SG ref, tag, any), four `RuleAction` values, zone, tags, priority; covers AWS SG, Palo Alto, Azure NSG field superset |
| ADAPT-03 | Proposed rule changes are validated against AWS SG constraints (allow-only, 60-rule limit, reject overly permissive 0.0.0.0/0) | `validate()` method returns `ValidationResult` with structured errors for DENY action, rule count > 60, 0.0.0.0/0 without flag, invalid protocols, invalid ports, invalid CIDRs |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| boto3 | >=1.40.61 | AWS EC2 API calls (describe_security_group_rules) | Already a project dependency; standard AWS SDK |
| pydantic | >=2.12 | UniversalRule, NetworkEndpoint, ValidationResult, AdapterCapabilities models | Already used project-wide for all domain models |
| asyncio (stdlib) | 3.12+ | asyncio.to_thread for wrapping sync boto3 calls | Established Phase 3 pattern; no extra dependency |
| importlib.metadata (stdlib) | 3.12+ | entry_points() for plugin discovery | Python standard library since 3.10; no extra dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ipaddress (stdlib) | 3.12+ | CIDR notation validation in validate() | Validating source/destination CIDRs in proposed rules |
| botocore | (transitive) | ClientError exception handling for AWS API failures | Already available as boto3 transitive dependency |

### Dev Dependencies (additions needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| moto[ec2] | >=5.1.22 | Mock EC2 describe_security_group_rules in tests | Already installed (moto 5.1.22 includes EC2 backend) |
| boto3-stubs[ec2] | >=1.42.63 | EC2Client type annotations for pyright strict | Currently only boto3-stubs[s3] in dev deps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| describe_security_group_rules | describe_security_groups | describe_security_groups groups rules by IpPermission (aggregated); describe_security_group_rules returns flat per-rule objects with unique IDs -- better for 1:1 translation |
| importlib.metadata entry_points | Manual registry dict | Entry points enable third-party plugin registration without code changes; manual registry requires import-time registration |
| asyncio.to_thread | aiobotocore/aioboto3 | Phase 3 established asyncio.to_thread pattern; aioboto3 has moto compatibility issues (documented in Phase 3 decisions) |

**Installation (dev dependency update):**
```bash
uv add --dev "moto[ec2,s3]>=5.1.22" "boto3-stubs[s3,ec2]>=1.42.63"
```

Note: moto[ec2] backend is already included in the installed moto 5.1.22, so the `pyproject.toml` change is purely declarative. The `boto3-stubs[ec2]` extra is needed for `mypy_boto3_ec2.client.EC2Client` type hints used in pyright strict mode.

## Architecture Patterns

### Recommended Project Structure
```
src/policyfoundry/adapters/
    __init__.py              # Public exports: FirewallAdapter, registry, schema types
    base.py                  # FirewallAdapter ABC (3 methods: get_rules, validate, capabilities)
    registry.py              # AdapterRegistry: entry_points discovery + get_adapter()
    schema.py                # ENRICHED: UniversalRule, NetworkEndpoint, ValidationResult, AdapterCapabilities
    aws_sg/
        __init__.py          # AwsSecurityGroupAdapter export
        adapter.py           # AwsSecurityGroupAdapter(FirewallAdapter)
        translator.py        # AwsSgTranslator: UniversalRule <-> AWS SecurityGroupRule
        client.py            # AwsSgClient: thin boto3 EC2 wrapper
```

### Pattern 1: Async ABC with Three Methods Only
**What:** Abstract base class with only the three methods needed now (no dead code)
**When to use:** Read + validate lifecycle (Phase 5 scope)
**Example:**
```python
# Source: CONTEXT.md locked decisions
from abc import ABC, abstractmethod

class FirewallAdapter(ABC):
    """Abstract firewall adapter -- read + validate lifecycle only."""

    @abstractmethod
    async def get_rules(self) -> list[UniversalRule]:
        """Fetch current rules in universal format."""

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
        """Declare adapter capabilities (static, no AWS queries)."""
```

### Pattern 2: asyncio.to_thread for boto3 Wrapping
**What:** Wrap synchronous boto3 calls in asyncio.to_thread for async compatibility
**When to use:** Every boto3 API call in the adapter
**Example:**
```python
# Source: established Phase 3 pattern (src/policyfoundry/ingestion/s3.py)
import asyncio
import boto3

class AwsSgClient:
    def __init__(self, security_group_id: str, region: str | None = None):
        self._sg_id = security_group_id
        self._client = boto3.client("ec2", region_name=region)

    async def describe_rules(self) -> list[dict]:
        response = await asyncio.to_thread(
            self._client.describe_security_group_rules,
            Filters=[{"Name": "group-id", "Values": [self._sg_id]}],
        )
        return response["SecurityGroupRules"]
```

### Pattern 3: Entry-Point Plugin Discovery
**What:** Use `importlib.metadata.entry_points()` to discover adapter plugins
**When to use:** Loading adapters by name at runtime
**Example:**
```python
# pyproject.toml registration:
# [project.entry-points."policyfoundry.adapters"]
# aws_sg = "policyfoundry.adapters.aws_sg:AwsSecurityGroupAdapter"

from importlib.metadata import entry_points

class AdapterRegistry:
    @staticmethod
    def get_adapter(name: str, **kwargs) -> FirewallAdapter:
        eps = entry_points(group="policyfoundry.adapters")
        for ep in eps:
            if ep.name == name:
                adapter_cls = ep.load()
                return adapter_cls(**kwargs)
        raise AdapterNotFoundError(f"No adapter registered as '{name}'")

    @staticmethod
    def list_adapters() -> list[str]:
        return [ep.name for ep in entry_points(group="policyfoundry.adapters")]
```

### Pattern 4: Stateless Translator
**What:** Pure translation functions between AWS format and universal format with no side effects
**When to use:** Converting `describe_security_group_rules` response items to `UniversalRule` objects
**Example:**
```python
# Source: boto3 describe_security_group_rules response format
class AwsSgTranslator:
    PROTOCOL_MAP = {"tcp": "tcp", "udp": "udp", "icmp": "icmp", "-1": "-1"}

    @staticmethod
    def from_sg_rule(sg_rule: dict) -> UniversalRule:
        """Convert an AWS SecurityGroupRule dict to UniversalRule."""
        source = _build_endpoint(sg_rule)
        return UniversalRule(
            id=sg_rule.get("SecurityGroupRuleId"),
            name=sg_rule.get("Description", ""),
            description=sg_rule.get("Description", ""),
            action=RuleAction.ALLOW,  # AWS SGs are always ALLOW
            direction=(
                Direction.OUTBOUND if sg_rule.get("IsEgress") else Direction.INBOUND
            ),
            protocol=sg_rule.get("IpProtocol", "-1"),
            source=[source],
            destination=[],
            port_range=_build_port_range(sg_rule),
        )
```

### Pattern 5: Structured Validation with Error Codes
**What:** Machine-readable validation errors with code + message + field
**When to use:** validate() method returns ValidationResult
**Example:**
```python
class ValidationIssue(BaseModel):
    code: str       # e.g., "DENY_NOT_SUPPORTED", "RULE_LIMIT_EXCEEDED"
    message: str    # Human-readable description
    field: str      # e.g., "action", "source", "port_range"

class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
```

### Anti-Patterns to Avoid
- **Mutable capabilities:** Do not query AWS at runtime for capabilities (e.g., checking actual quota). Return static `AdapterCapabilities` -- the 60-rule default is the safe baseline.
- **Resolving SG-to-SG references to CIDRs:** Preserve `security_group_id` in `NetworkEndpoint` as-is. Resolving would lose the semantic meaning and create stale data.
- **Stubbing future methods:** Do not add `apply_rule()`, `rollback()`, `dry_run()` as `NotImplementedError` stubs. The ABC should only declare methods that have implementations.
- **Custom auth flow:** Do not build profile selection, MFA, or SSO helpers. Use default boto3 credential chain.
- **Sync adapter methods:** All adapter methods must be async even if the underlying call is sync (wrap with asyncio.to_thread).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CIDR validation | Custom regex parser | `ipaddress.ip_network(cidr, strict=False)` | Handles IPv4/IPv6, validates prefix length, catches malformed input |
| AWS credential management | Custom env var parsing, profile loading | Default boto3 credential chain | Handles env vars, config files, IAM roles, instance profiles automatically |
| Plugin discovery | Manual adapter registry dict with imports | `importlib.metadata.entry_points()` | Standard Python packaging mechanism; enables third-party plugins without code changes |
| AWS API mocking | Custom mock classes | moto `mock_aws` decorator | Full EC2 API fidelity, automatic request validation, stateful mock backend |
| Protocol number to name mapping | Lookup table | Use string values directly ("tcp", "udp", "icmp", "-1") | AWS API uses the same string values; just pass through |

**Key insight:** AWS SG rules are deceptively complex -- a single IpPermission can reference CIDRs, security groups, prefix lists, or IPv6 ranges. The `describe_security_group_rules` API flattens this complexity (one rule per response item), which is why it should be preferred over `describe_security_groups` (which aggregates multiple sources under a single permission).

## Common Pitfalls

### Pitfall 1: IpProtocol "-1" Means All Traffic
**What goes wrong:** Treating "-1" as an invalid protocol value or forgetting to handle it
**Why it happens:** "-1" is the AWS convention for "all protocols" and also means "all ports" (FromPort/ToPort are -1 or absent)
**How to avoid:** Map "-1" to "ALL" or "-1" in the universal schema protocol field; when protocol is "-1", set port_range to None (all ports implied)
**Warning signs:** Tests that only cover tcp/udp/icmp miss the "all traffic" default egress rule

### Pitfall 2: FromPort/ToPort Semantics Vary by Protocol
**What goes wrong:** Treating FromPort/ToPort as always being port numbers
**Why it happens:** For ICMP, FromPort is the ICMP type and ToPort is the ICMP code; for protocol "-1", both are -1
**How to avoid:** Only create PortRange when protocol is tcp or udp; for icmp, handle type/code separately; for "-1", skip port range entirely
**Warning signs:** ICMP rules translated with port_range showing ICMP type as a port number

### Pitfall 3: Missing Default Egress Rule
**What goes wrong:** Fetching rules via `describe_security_group_rules` and not seeing the default "allow all outbound" rule
**Why it happens:** AWS SGs have a default outbound rule (all traffic, 0.0.0.0/0) that shows up in the API response -- but developers might not expect it
**How to avoid:** Include the default egress rule in get_rules() output; it's a real rule that appears in the API response
**Warning signs:** Rule count mismatch between AWS console and adapter output

### Pitfall 4: describe_security_group_rules Response Has No Port Fields for All-Traffic Rules
**What goes wrong:** Accessing `FromPort` / `ToPort` when they may not exist in the response dict
**Why it happens:** When IpProtocol is "-1", AWS may omit FromPort/ToPort from the response entirely
**How to avoid:** Use `.get("FromPort")` / `.get("ToPort")` with None defaults; only build PortRange when both are present and protocol is tcp/udp
**Warning signs:** KeyError on FromPort in production with all-traffic rules

### Pitfall 5: Rule Count Validation Off-by-One
**What goes wrong:** Counting inbound and outbound rules separately when the 60-rule limit applies per SG total (inbound + outbound combined)
**Why it happens:** AWS documentation is ambiguous -- the default quota is 60 inbound rules AND 60 outbound rules, NOT 60 total
**How to avoid:** Per AWS docs, the default is 60 inbound + 60 outbound = 120 rules total. Validate inbound and outbound counts separately. The validate() method should take `current_rule_count` representing rules in the same direction.
**Warning signs:** Rejecting rules at count 55 when the actual limit for that direction is 60

### Pitfall 6: 0.0.0.0/0 Check Must Also Cover ::/0
**What goes wrong:** Only checking for IPv4 "all addresses" (0.0.0.0/0) but not IPv6 (::/0)
**Why it happens:** IPv6 "all addresses" is a separate CIDR that has the same security implications
**How to avoid:** Check both `0.0.0.0/0` and `::/0` as "overly permissive" sources; same flag `allow_wide_open` controls both
**Warning signs:** IPv6 rules bypassing the wide-open check

### Pitfall 7: Entry Point Discovery Requires Package Installation
**What goes wrong:** `entry_points(group="policyfoundry.adapters")` returns empty during development
**Why it happens:** Entry points are only available after `pip install -e .` or equivalent; running from source without install doesn't register them
**How to avoid:** Use `uv pip install -e .` for development; add a fallback in the registry that imports the built-in adapter directly if no entry points are found
**Warning signs:** "No adapter registered" errors in development but works in CI

## Code Examples

Verified patterns from official sources and existing codebase:

### AWS describe_security_group_rules Response Item
```python
# Source: https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_group_rules.html
{
    "SecurityGroupRuleId": "sgr-0123456789abcdef0",
    "GroupId": "sg-0123456789abcdef0",
    "GroupOwnerId": "123456789012",
    "IsEgress": False,
    "IpProtocol": "tcp",
    "FromPort": 443,
    "ToPort": 443,
    "CidrIpv4": "10.0.0.0/8",
    "CidrIpv6": None,
    "PrefixListId": None,
    "ReferencedGroupInfo": None,
    "Description": "Allow HTTPS from internal",
    "Tags": [],
    "SecurityGroupRuleArn": "arn:aws:ec2:us-east-1:123456789012:security-group-rule/sgr-0123456789abcdef0"
}
```

### SG-to-SG Reference Response Item
```python
# Source: https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_group_rules.html
{
    "SecurityGroupRuleId": "sgr-abcdef0123456789a",
    "GroupId": "sg-0123456789abcdef0",
    "IsEgress": False,
    "IpProtocol": "tcp",
    "FromPort": 3306,
    "ToPort": 3306,
    "CidrIpv4": None,
    "CidrIpv6": None,
    "ReferencedGroupInfo": {
        "GroupId": "sg-aaaa1111bbbb2222c",
        "UserId": "123456789012"
    },
    "Description": "MySQL from app tier"
}
```

### All-Traffic Default Egress Rule
```python
# Source: AWS SG default behavior
{
    "SecurityGroupRuleId": "sgr-default-egress",
    "GroupId": "sg-0123456789abcdef0",
    "IsEgress": True,
    "IpProtocol": "-1",
    # NOTE: FromPort and ToPort may be absent or -1 for all-traffic rules
    "CidrIpv4": "0.0.0.0/0",
    "Description": None
}
```

### moto EC2 Security Group Test Pattern
```python
# Source: Established Phase 3 moto pattern (tests/test_ingestion/test_s3.py)
import boto3
import pytest
from moto import mock_aws

@pytest.fixture(autouse=True)
def _aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy AWS credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

def _create_sg_with_rules() -> str:
    """Create a security group with rules using sync boto3 inside mock_aws."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    # Create VPC first (SGs require a VPC in non-default setups)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    # Create SG
    sg = ec2.create_security_group(
        GroupName="test-sg",
        Description="Test security group",
        VpcId=vpc_id,
    )
    sg_id = sg["GroupId"]
    # Add inbound rule
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[{
            "IpProtocol": "tcp",
            "FromPort": 443,
            "ToPort": 443,
            "IpRanges": [{"CidrIp": "10.0.0.0/8", "Description": "HTTPS"}],
        }],
    )
    return sg_id
```

### CIDR Validation Using stdlib
```python
# Source: Python stdlib ipaddress module
import ipaddress

def is_valid_cidr(cidr: str) -> bool:
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except ValueError:
        return False

def is_wide_open(cidr: str) -> bool:
    return cidr in ("0.0.0.0/0", "::/0")
```

### Entry Point Registration in pyproject.toml
```toml
# Source: https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
[project.entry-points."policyfoundry.adapters"]
aws_sg = "policyfoundry.adapters.aws_sg:AwsSecurityGroupAdapter"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `describe_security_groups` (aggregated IpPermissions) | `describe_security_group_rules` (flat per-rule objects) | AWS API addition ~2021 | Flat per-rule output is better for 1:1 translation; each rule has unique ID |
| `pkg_resources` entry points | `importlib.metadata.entry_points()` | Python 3.10+ / PEP 451 | stdlib replacement for setuptools pkg_resources; faster, no extra dependency |
| moto decorators (`@mock_ec2`) | `mock_aws` unified decorator | moto 5.x | Single decorator replaces all per-service decorators |
| `moto[ec2]` separate install | moto includes all backends by default | moto 5.x | Extras only control optional dependencies; all backends available in base install |

**Deprecated/outdated:**
- `describe_security_groups` still works but `describe_security_group_rules` provides better granularity for rule-level operations
- `@mock_ec2` decorator replaced by `@mock_aws` in moto 5.x (both still work, but `mock_aws` is preferred)
- `pkg_resources` entry points are deprecated in favor of `importlib.metadata`

## Open Questions

1. **Rule count limit: 60 per direction or 60 total?**
   - What we know: AWS default quota is 60 inbound rules AND 60 outbound rules per security group (separate quotas). This can be increased via support request. Prefix list references count as the prefix list weight (e.g., 10 entries = 10 rules).
   - What's unclear: Whether the project should hardcode 60 as the limit or make it configurable on AdapterCapabilities.
   - Recommendation: Use 60 as the default `max_rules_per_direction` on AdapterCapabilities. Validate per-direction (inbound count vs 60, outbound count vs 60). This matches actual AWS behavior.

2. **Handling prefix list references in rules**
   - What we know: AWS SG rules can reference prefix lists (e.g., `com.amazonaws.us-east-1.s3`). These appear as `PrefixListId` in the API response.
   - What's unclear: Whether NetworkEndpoint should have a `prefix_list_id` field.
   - Recommendation: Add `prefix_list_id: str | None = None` to NetworkEndpoint. This preserves the information without resolving it, consistent with the "preserve as-is" decision for SG references. If not added now, rules referencing prefix lists would lose information.

3. **IPv6 CIDR support in NetworkEndpoint**
   - What we know: AWS SG rules can have CidrIpv6 (e.g., "2001:db8::/32"). The current UniversalRule uses `cidr` field on NetworkEndpoint.
   - What's unclear: Whether a single `cidr` field handles both IPv4 and IPv6.
   - Recommendation: A single `cidr: str | None` field works fine -- `ipaddress.ip_network()` handles both IPv4 and IPv6 CIDR notation transparently. No separate field needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0 with pytest-asyncio >= 1.3.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (exists) |
| Quick run command | `uv run pytest tests/test_adapters/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADAPT-01 | Fetch SG rules and view in universal format | integration | `uv run pytest tests/test_adapters/test_aws_sg_adapter.py::TestGetRules -x` | No -- Wave 0 |
| ADAPT-01 | Translator converts AWS rule dict to UniversalRule | unit | `uv run pytest tests/test_adapters/test_aws_sg_translator.py -x` | No -- Wave 0 |
| ADAPT-02 | UniversalRule schema with NetworkEndpoint, all RuleActions, zone, tags | unit | `uv run pytest tests/test_adapters/test_schema.py -x` | No -- Wave 0 |
| ADAPT-02 | AdapterCapabilities declares vendor constraints | unit | `uv run pytest tests/test_adapters/test_schema.py::TestAdapterCapabilities -x` | No -- Wave 0 |
| ADAPT-03 | Reject DENY action for AWS SG | unit | `uv run pytest tests/test_adapters/test_validation.py::TestDenyRejection -x` | No -- Wave 0 |
| ADAPT-03 | Reject 0.0.0.0/0 without allow_wide_open flag | unit | `uv run pytest tests/test_adapters/test_validation.py::TestWideOpenRejection -x` | No -- Wave 0 |
| ADAPT-03 | Reject when rule count exceeds 60-rule limit | unit | `uv run pytest tests/test_adapters/test_validation.py::TestRuleLimitExceeded -x` | No -- Wave 0 |
| ADAPT-03 | Validate protocol, port range, CIDR notation | unit | `uv run pytest tests/test_adapters/test_validation.py::TestFieldValidation -x` | No -- Wave 0 |
| N/A | Entry-point plugin discovery loads AWS SG adapter | unit | `uv run pytest tests/test_adapters/test_registry.py -x` | No -- Wave 0 |
| N/A | Error handling for AWS API failures | integration | `uv run pytest tests/test_adapters/test_aws_sg_adapter.py::TestErrorHandling -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_adapters/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_adapters/__init__.py` -- package init
- [ ] `tests/test_adapters/conftest.py` -- shared fixtures (moto AWS credentials, SG setup helpers)
- [ ] `tests/test_adapters/test_schema.py` -- enriched UniversalRule, NetworkEndpoint, ValidationResult, AdapterCapabilities
- [ ] `tests/test_adapters/test_aws_sg_translator.py` -- AWS rule dict to/from UniversalRule translation
- [ ] `tests/test_adapters/test_aws_sg_adapter.py` -- integration tests with moto (get_rules, capabilities, error handling)
- [ ] `tests/test_adapters/test_validation.py` -- constraint validation (DENY, wide-open, rule limit, protocol, ports, CIDRs)
- [ ] `tests/test_adapters/test_registry.py` -- entry-point plugin discovery
- [ ] Dev dependency update: `"moto[ec2,s3]>=5.1.22"` and `"boto3-stubs[s3,ec2]>=1.42.63"` in pyproject.toml
- [ ] Existing `tests/test_models/test_universal_rule.py` -- will need updates for enriched schema (new fields, new RuleAction values)
- [ ] Existing `tests/conftest.py` -- `valid_universal_rule_data` fixture needs updating for new schema shape

## Sources

### Primary (HIGH confidence)
- [boto3 describe_security_group_rules API](https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_group_rules.html) -- full response structure, filters, pagination
- [boto3 describe_security_groups API](https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_security_groups.html) -- IpPermissions structure comparison
- [boto3 authorize_security_group_ingress API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/authorize_security_group_ingress.html) -- IpPermission format, IpRanges, UserIdGroupPairs
- [moto EC2 implementation status](https://docs.getmoto.org/en/stable/docs/services/ec2.html) -- all SG APIs confirmed implemented in moto 5.1.22
- [AWS VPC quotas](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html) -- 60 inbound + 60 outbound rules per SG default
- [Python packaging: Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) -- entry_points() pattern
- Existing codebase: `src/policyfoundry/ingestion/s3.py` -- asyncio.to_thread + boto3 + moto pattern
- Existing codebase: `tests/test_ingestion/test_s3.py` -- moto mock_aws test structure

### Secondary (MEDIUM confidence)
- [AWS re:Post: Increase security group rule quota](https://repost.aws/knowledge-center/increase-security-group-rule-limit) -- quota increase process, prefix list weight counting
- [setuptools entry_point documentation](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) -- pyproject.toml syntax

### Tertiary (LOW confidence)
- None -- all findings verified against official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use or stdlib; versions verified against pyproject.toml
- Architecture: HIGH -- patterns established in Phase 3; ABC/translator/client structure from architecture plan; entry_points from Python packaging standard
- Pitfalls: HIGH -- verified against official AWS API docs (IpProtocol "-1", FromPort/ToPort semantics, response structure)
- Validation: HIGH -- AWS SG constraints well-documented (allow-only, 60-rule per direction, prefix list weights)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain -- AWS EC2 APIs and Python packaging standards change infrequently)