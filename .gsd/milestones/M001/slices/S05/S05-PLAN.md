# S05: Firewall Adapter

**Goal:** Enrich the universal rule schema with NetworkEndpoint, create the FirewallAdapter ABC, build the AdapterRegistry with entry-point plugin discovery, and establish test infrastructure for the adapter layer.
**Demo:** Enrich the universal rule schema with NetworkEndpoint, create the FirewallAdapter ABC, build the AdapterRegistry with entry-point plugin discovery, and establish test infrastructure for the adapter layer.

## Must-Haves


## Tasks

- [x] **T01: 05-firewall-adapter 01** `est:5min`
  - Enrich the universal rule schema with NetworkEndpoint, create the FirewallAdapter ABC, build the AdapterRegistry with entry-point plugin discovery, and establish test infrastructure for the adapter layer.

Purpose: Defines the contracts (schema, ABC, registry) that the AWS SG adapter in Plan 02 implements against. Without these contracts, Plan 02 has no types to import or ABC to subclass.
Output: Enriched schema.py, base.py ABC, registry.py, entry-point registration, adapter exception subclasses, test scaffolding.
- [x] **T02: 05-firewall-adapter 02** `est:5min`
  - Implement the AWS Security Group adapter: a thin boto3 client, a stateless rule translator, and the adapter class that ties them together with constraint validation. This delivers the ability to fetch real SG rules and validate proposed changes against AWS constraints.

Purpose: Makes ADAPT-01 (fetch SG rules in universal format) and ADAPT-03 (validate proposed rules) functional. Phase 7 pipeline stages will call get_rules() and validate() on this adapter.
Output: aws_sg/ subpackage with client.py, translator.py, adapter.py, plus comprehensive tests using moto.

## Files Likely Touched

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
- `src/policyfoundry/adapters/aws_sg/__init__.py`
- `src/policyfoundry/adapters/aws_sg/client.py`
- `src/policyfoundry/adapters/aws_sg/translator.py`
- `src/policyfoundry/adapters/aws_sg/adapter.py`
- `pyproject.toml`
- `tests/test_adapters/conftest.py`
- `tests/test_adapters/test_aws_sg_translator.py`
- `tests/test_adapters/test_aws_sg_adapter.py`
- `tests/test_adapters/test_validation.py`
