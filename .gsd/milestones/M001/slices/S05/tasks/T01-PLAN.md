# T01: 05-firewall-adapter 01

**Slice:** S05 — **Milestone:** M001

## Description

Enrich the universal rule schema with NetworkEndpoint, create the FirewallAdapter ABC, build the AdapterRegistry with entry-point plugin discovery, and establish test infrastructure for the adapter layer.

Purpose: Defines the contracts (schema, ABC, registry) that the AWS SG adapter in Plan 02 implements against. Without these contracts, Plan 02 has no types to import or ABC to subclass.
Output: Enriched schema.py, base.py ABC, registry.py, entry-point registration, adapter exception subclasses, test scaffolding.

## Must-Haves

- [ ] "UniversalRule uses list[NetworkEndpoint] for source/destination instead of list[str]"
- [ ] "RuleAction enum has all four values: ALLOW, DENY, DROP, REJECT"
- [ ] "AdapterCapabilities declares vendor constraints (supports_deny, max_rules_per_direction)"
- [ ] "FirewallAdapter ABC defines async get_rules(), validate(), and sync capabilities() methods"
- [ ] "AdapterRegistry discovers adapters via entry_points and falls back to direct import"
- [ ] "Entry point 'policyfoundry.adapters' group is registered in pyproject.toml for aws_sg"

## Files

- `src/policyfoundry/adapters/schema.py`
- `src/policyfoundry/adapters/base.py`
- `src/policyfoundry/adapters/registry.py`
- `src/policyfoundry/adapters/__init__.py`
- `src/policyfoundry/exceptions.py`
- `pyproject.toml`
- `tests/conftest.py`
- `tests/test_adapters/__init__.py`
- `tests/test_adapters/conftest.py`
- `tests/test_adapters/test_schema.py`
- `tests/test_adapters/test_registry.py`
- `tests/test_models/test_universal_rule.py`
