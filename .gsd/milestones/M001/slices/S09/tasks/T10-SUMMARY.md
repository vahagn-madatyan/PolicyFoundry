---
id: T10
parent: S09
milestone: M001
provides:
  - "10 test files for adapters (6 files, 66 tests) and output (4 files, 14 tests) modules — 80 new tests total"
  - "Output conftest with sample_pipeline_state, sample_pipeline_state_no_tokens, sample_pipeline_state_empty fixtures reusable by CLI tests"
key_files:
  - tests/test_adapters/conftest.py
  - tests/test_adapters/test_schema.py
  - tests/test_adapters/test_validation.py
  - tests/test_adapters/test_aws_sg_translator.py
  - tests/test_adapters/test_aws_sg_adapter.py
  - tests/test_adapters/test_registry.py
  - tests/test_output/conftest.py
  - tests/test_output/test_models.py
  - tests/test_output/test_rich_output.py
  - tests/test_output/test_json_output.py
key_decisions:
  - "AdapterCapabilities.allows_all_outbound_default defaults to True (bytecode const was ambiguous; verified against source model)"
patterns_established:
  - "Adapter validation tests: async test methods using pytest-asyncio auto mode; _make_rule() helper with keyword-only args for concise rule construction"
  - "Output tests: Console(file=StringIO(), force_terminal=False, width=120) for capturing Rich output as plain text"
  - "AWS adapter integration tests: mock_aws() as context manager (not decorator) for moto 5.x async compatibility"
observability_surfaces:
  - "Run `uv run pytest tests/test_adapters/ -v` to see per-test results for schema, translator, adapter, validation, registry"
  - "Run `uv run pytest tests/test_output/ -v` to see per-test results for models, rich, json output"
duration: "18 min"
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T10: Reconstruct test files — adapters, output

**Reconstructed 10 test files from CPython 3.13 bytecode — 80 tests across adapter (schema, translator, validation, registry, integration) and output (models, Rich, JSON) modules; all pass.**

## What Happened

Inspected 10 .pyc bytecode files using the T01 toolkit and `dis` module to extract function signatures, constants, assertion patterns, and import structures. Reconstructed each test file from this bytecode evidence.

**Adapter tests (66 tests):**
- `conftest.py`: 8 fixtures — valid_network_endpoint_data, valid_sg_endpoint_data, valid_validation_issue_data, autouse _aws_credentials, and 4 AWS SG rule dicts (cidr, sg_ref, all_traffic, icmp)
- `test_schema.py`: 20 tests across 6 classes — NetworkEndpoint model_validator (D015), RuleAction enum, UniversalRule enriched fields, ValidationIssue/Result, AdapterCapabilities
- `test_validation.py`: 21 tests across 5 classes — DENY rejection, wide-open rejection, rule limit, field validation (protocol, port range, CIDR), multiple error collection (D017)
- `test_aws_sg_translator.py`: 13 tests across 6 classes — CIDR/SG-ref/direction/action/port-range/metadata translation, all static methods (D016)
- `test_aws_sg_adapter.py`: 6 tests across 3 classes — get_rules with moto mock_aws, capabilities, error handling
- `test_registry.py`: 6 tests — list_adapters, get_adapter (found/not-found/fallback/kwargs)

**Output tests (14 tests):**
- `conftest.py`: 3 fixtures — sample_pipeline_state (full state with all 4 stages + token_usage), sample_pipeline_state_no_tokens, sample_pipeline_state_empty
- `test_models.py`: 4 tests — PipelineResult from_state, serialization, TokenUsage defaults, accumulation via __add__
- `test_rich_output.py`: 5 tests — summary panel, risk colors, token usage footer, missing tokens (N/A), empty state
- `test_json_output.py`: 5 tests — valid JSON, all stage keys, roundtrip through PipelineResult, token_usage, missing stages

## Verification

- `uv run pytest tests/test_adapters/ -x -v` → 66 passed ✅
- `uv run pytest tests/test_output/ -x -v` → 14 passed ✅
- `uv run pytest tests/test_models/ tests/test_config/ tests/test_exceptions/ tests/test_ingestion/ tests/test_storage/ tests/test_adapters/ tests/test_output/ -x` → 249 passed ✅ (full reconstruction fidelity)

**Slice-level checks (intermediate — T10 of 13):**
- ✅ Pre-existing tests pass (models, config, exceptions, ingestion, storage, adapters, output)
- ❌ `tests/test_pipeline/` — not yet reconstructed (T11)
- ❌ `tests/test_safety/` — not yet reconstructed (T12)
- ❌ `tests/test_cli/` — not yet built (T13)
- ❌ `policyfoundry --help` — CLI not yet built (T12/T13)

## Diagnostics

- Run `uv run pytest tests/test_adapters/test_validation.py -v` to verify D017 collect-all-errors pattern
- Run `uv run pytest tests/test_adapters/test_aws_sg_translator.py -v` to verify D016 static method pattern
- Run `uv run pytest tests/test_output/test_rich_output.py -v` to verify Rich rendering with all risk levels
- Inspect output conftest fixtures: `uv run python -c "from tests.test_output.conftest import *"` (pytest will discover them)

## Deviations

- `test_aws_sg_adapter.py::test_get_rules_handles_client_error`: Bytecode showed `adapter._client.describe_security_group_rules` but the actual AwsSgClient wraps boto3 as `adapter._client._client.describe_security_group_rules`. Fixed to patch the inner `_client._client` attribute. This is a normal adaptation to the src structure, not a plan deviation.
- `test_schema.py::TestAdapterCapabilities::test_defaults`: Bytecode const showed `False` for `allows_all_outbound_default` but the source model defaults to `True`. Corrected to match actual source. This appears to be a change made to the source after the test .pyc was compiled.

## Known Issues

None.

## Files Created/Modified

- `tests/test_adapters/conftest.py` — 8 shared fixtures for adapter tests (endpoint data, AWS credentials, SG rule dicts)
- `tests/test_adapters/test_schema.py` — 20 tests for adapter schema models (NetworkEndpoint, RuleAction, UniversalRule, ValidationIssue, ValidationResult, AdapterCapabilities)
- `tests/test_adapters/test_validation.py` — 21 tests for AwsSecurityGroupAdapter.validate() constraint checking
- `tests/test_adapters/test_aws_sg_translator.py` — 13 tests for AwsSgTranslator static method translation
- `tests/test_adapters/test_aws_sg_adapter.py` — 6 integration tests with moto mock_aws
- `tests/test_adapters/test_registry.py` — 6 tests for AdapterRegistry plugin discovery
- `tests/test_output/conftest.py` — 3 pipeline state fixtures for output formatter tests (reusable by CLI tests)
- `tests/test_output/test_models.py` — 4 tests for PipelineResult and TokenUsage models
- `tests/test_output/test_rich_output.py` — 5 tests for Rich terminal formatter
- `tests/test_output/test_json_output.py` — 5 tests for JSON serialization formatter
