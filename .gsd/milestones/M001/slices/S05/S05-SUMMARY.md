---
id: S05
parent: M001
milestone: M001
provides:
  - Enriched UniversalRule with NetworkEndpoint source/destination
  - FirewallAdapter ABC (get_rules, validate, capabilities)
  - AdapterRegistry with entry_points plugin discovery
  - ValidationResult, ValidationIssue, AdapterCapabilities models
  - AwsSecurityGroupAdapter with boto3 client, rule translator, constraint validation
  - Stateless AwsSgTranslator for SG rule → UniversalRule conversion
requires: []
affects: []
key_files:
  - src/policyfoundry/adapters/schema.py
  - src/policyfoundry/adapters/base.py
  - src/policyfoundry/adapters/registry.py
  - src/policyfoundry/adapters/aws_sg/adapter.py
  - src/policyfoundry/adapters/aws_sg/translator.py
  - src/policyfoundry/adapters/aws_sg/client.py
key_decisions:
  - "Used bare [] and {} defaults instead of Field(default_factory=list/dict) for pyright strict compatibility"
  - "NetworkEndpoint uses model_validator(mode=after) for at-least-one-identifier constraint"
  - "Stateless translator pattern: AwsSgTranslator uses only static methods, no instance state"
  - "ICMP type/code mapped to None port_range (not PortRange) since they are not TCP/UDP ports"
  - "frozenset for auth error codes, valid protocols, and wide-open CIDRs for O(1) membership checks"
  - "Validation collects all errors (not short-circuit) so users see every issue at once"
patterns_established:
  - "Stateless translator class with static methods for vendor-specific rule conversion"
  - "ValidationResult with structured error codes for constraint checking"
  - "Entry-point plugin discovery with built-in fallback for development mode"
observability_surfaces: []
drill_down_paths: []
duration: 10min
verification_result: passed
completed_at: 2026-03-10
blocker_discovered: false
---
# S05: Firewall Adapter

## What Was Delivered

Enriched universal rule schema with NetworkEndpoint, FirewallAdapter ABC with async read+validate contract, AdapterRegistry with entry-point plugin discovery, and a complete AWS Security Group adapter (boto3 client, stateless translator, 6-constraint validation). 4/4 success criteria verified.

## Key Outcomes

- **T01**: Adapter contracts — enriched UniversalRule schema, FirewallAdapter ABC, AdapterRegistry with entry-point discovery, adapter exception subclasses. 26 adapter tests.
- **T02**: AWS SG adapter — boto3 client wrapping describe_security_group_rules, AwsSgTranslator for SG→UniversalRule conversion, 6-constraint validation (DENY, overly-permissive, rule-limit, protocol, port-range, CIDR). 21 validation tests with moto.

## Verification

All 4 success criteria passed: SG rules fetched in universal format, schema is vendor-neutral, constraint violations rejected, capabilities declared.

---
*Completed: 2026-03-10*
