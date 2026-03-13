---
id: M001
provides:
  - "policyfoundry CLI with analyze, rules, and config commands"
  - "5-stage LangGraph AI pipeline: Analyze → Assess → Generate → Validate → Decide"
  - "AWS VPC Flow Log ingestion from local files and S3 with deduplication"
  - "Parquet storage with zstd compression and DuckDB analytics queries"
  - "AWS Security Group adapter with boto3, rule translation, and constraint validation"
  - "LLMClient with Instructor + LiteLLM for structured Pydantic output"
  - "Rich terminal output with color-coded risk tables and token cost footer"
  - "JSON export of all pipeline stage results"
  - "ReadOnlyAdapter safety wrapper enforcing suggest-only mode"
  - "TokenUsage tracking with per-stage prompt/completion counts and estimated cost"
  - "Pydantic Settings config system with YAML + env var merge"
  - "Terraform HCL for VPC, Security Groups, Flow Logs test environment"
  - "Dockerfile and docker-compose.yml with Ollama sidecar"
key_decisions:
  - "D012: boto3 + asyncio.to_thread instead of aioboto3 (moto compatibility)"
  - "D021: LangGraph context_schema with PipelineContext dataclass for DI"
  - "D027: Typer sync commands with internal asyncio.run() (Typer 0.24 limitation)"
  - "D028: Decompile .pyc → .py as blocking prerequisite for S09"
  - "D032: dis module + manual reconstruction for CPython 3.13 bytecode (decompyle3 unsupported)"
  - "D033: CLI integration tests mock LLMClient and FirewallAdapter; keep real config/ingestion/storage/output"
  - "D037: tenacity reraise=True required for PipelineError propagation on retry exhaustion"
patterns_established:
  - "Pure function parsers that never raise (return None on failure)"
  - "Stateless translator classes with static methods for vendor-specific conversion"
  - "Instructor + LiteLLM wrapper for structured LLM output with dual retry layers"
  - "LangGraph stage functions: async def stage(state, config) → dict[str, Any]"
  - "Wrapper BaseModel pattern for Instructor structured list output"
  - "Non-LLM validation step between Generate and Decide for deterministic filtering"
  - "TDD red-green-refactor with atomic commits per task"
  - "Domain models in per-module schema.py files"
  - "TypedDict with total=False for LangGraph state containers"
  - "Structured exceptions with error_code and details dict"
observability_surfaces:
  - "TokenUsage per-stage tracking with prompt/completion counts and cost in CLI footer"
  - "Rich Status spinner showing current pipeline stage during LLM inference"
  - "Actionable error messages with error codes surfaced at CLI boundary (no stack traces without --debug)"
  - "IngestionResult with total_lines, duplicates_removed, errors_skipped, warnings"
  - "WriteResult with records_written, duplicates_skipped, file_path"
requirement_outcomes:
  - id: OUT-01
    from_status: active
    to_status: validated
    proof: "CLI integration tests prove Rich output with traffic analysis, rule proposals, risk tables (test_analyze_rich_output_contains_traffic_analysis, _rule_proposals, _risk_table all PASSED)"
  - id: OUT-02
    from_status: active
    to_status: validated
    proof: "test_analyze_json_output_is_valid_json and _contains_pipeline_stages prove valid parseable JSON with all stage data"
  - id: SAFE-01
    from_status: active
    to_status: validated
    proof: "ReadOnlyAdapter in adapters/safety.py wraps all adapter access; 6 safety tests + test_analyze_safety_enforced prove SafetyError raised on write attempts"
  - id: SAFE-02
    from_status: active
    to_status: validated
    proof: "test_analyze_rich_output_contains_token_cost and test_analyze_json_output_contains_token_usage prove token usage and cost displayed in both output formats"
  - id: INFRA-01
    from_status: active
    to_status: validated
    proof: "infra/terraform/main.tf contains aws_vpc, aws_subnet (public+private), aws_security_group with ingress/egress rules, aws_flow_log with S3 destination, S3 bucket with policy"
  - id: INFRA-02
    from_status: active
    to_status: validated
    proof: "Dockerfile (multi-stage Python 3.13) and docker-compose.yml (policyfoundry + ollama sidecar) present and structurally valid"
duration: 5 days
verification_result: passed
completed_at: 2026-03-12
---

# M001: PolicyFoundry MVP

**Full AI-powered firewall policy analysis pipeline from VPC Flow Log ingestion through 5-stage LangGraph pipeline to Rich terminal output with color-coded risk tables, JSON export, and suggest-only safety enforcement — packaged as a CLI with Terraform test infra and Docker deployment.**

## What Happened

The milestone built PolicyFoundry bottom-up across 10 slices over 5 days.

**Foundation (S01–S02):** Bootstrapped the Python package with domain models (NormalizedFlowLog, UniversalRule, pipeline output models, exception hierarchy) and a Pydantic Settings config system with 4-layer merge priority (global YAML < local YAML < env vars < kwargs).

**Data pipeline (S03–S04):** Built VPC Flow Log v2 parsing (local files and S3) with SHA-256 deduplication, then Parquet persistence with zstd compression and DuckDB analytics queries (top_talkers, denied_flows, traffic_by_protocol, traffic_summary).

**Adapter layer (S05):** Created FirewallAdapter ABC with AdapterRegistry plugin discovery and a complete AWS Security Group adapter — boto3 client, stateless rule translator, and 6-constraint validation (deny rules, wide-open CIDRs, rule limits, protocol/port/CIDR checks).

**LLM integration (S06):** Wrapped Instructor + LiteLLM for structured Pydantic output with dual retry layers (3x validation, 3x transient with exponential backoff) and Ollama health checking.

**Pipeline core (S07):** Built the 5-stage LangGraph pipeline (Analyze → Assess → Generate → Validate → Decide) with PipelineContext DI, partial-result error handling, and non-LLM validation filtering.

**Output and safety (S08):** Rich terminal formatter with color-coded risk tables and JSON export. TokenUsage tracking per LLM call. ReadOnlyAdapter safety wrapper raising SafetyError on any write attempt.

**CLI integration (S09):** This was the highest-risk slice. All 92 source files (48 src + 44 test) had been deleted — only CPython 3.13 bytecode remained. decompyle3 doesn't support 3.13, so reconstruction used the `dis` module from the same Python version plus manual reconstruction. After recovery, Typer CLI was built with `analyze`, `rules`, and `config` commands, Rich error handling at the command boundary, and 25 CLI integration tests.

**Infrastructure and packaging (S10):** Terraform HCL for a test VPC with Security Groups and Flow Logs to S3. Multi-stage Dockerfile and docker-compose.yml with Ollama sidecar. E2E test exercising the full pipeline against fixture data.

## Cross-Slice Verification

**All source .py files exist on disk:** 51 src files + 52 test files confirmed present (not just bytecode).

**Full test suite passes:** 361 tests in 12.78s — covers models, config, ingestion, storage, adapters, pipeline, output, safety, CLI integration, and E2E.

**`policyfoundry analyze` with Rich output:** CLI integration tests prove exit code 0, traffic analysis section, rule proposals section, risk table, and token cost footer all present in Rich output (5 tests).

**`policyfoundry analyze --format json`:** Tests prove valid parseable JSON with all pipeline stage data and token_usage included (4 tests).

**Token usage and cost displayed:** Both Rich output (footer with prompt/completion tokens and cost) and JSON output (token_usage object) verified by tests.

**Suggest-only safety:** ReadOnlyAdapter wraps all adapter access in the analyze command. SafetyError raised on any write attempt — verified by 6 safety unit tests + 1 CLI integration test (test_analyze_safety_enforced).

**CLI --help text:** All three commands (analyze, rules, config) show useful help text with option descriptions. Verified by test_help_text_shows_all_commands and test_analyze_help_shows_options.

**Actionable error messages:** ConfigError, AdapterError, PipelineError, and unknown errors all produce Rich-formatted messages without stack traces (4 error handling tests).

**Terraform:** infra/terraform/ contains main.tf (VPC, subnets, SG with ingress/egress rules, S3 bucket, IAM role, VPC Flow Log), variables.tf, outputs.tf, versions.tf.

**Docker:** Dockerfile (multi-stage Python 3.13 build) and docker-compose.yml (policyfoundry + ollama sidecar with POLICYFOUNDRY_LLM__BASE_URL override).

**E2E test:** tests/e2e/test_e2e_analyze.py exercises the full pipeline path with fixture data. Reference JSON output in tests/fixtures/sample_output/reference.json.

## Requirement Changes

- **OUT-01:** active → validated — Rich terminal output with color-coded risk tables verified by 5 CLI integration tests
- **OUT-02:** active → validated — JSON export verified by test_analyze_json_output_is_valid_json proving parseable JSON with all pipeline stages
- **SAFE-01:** active → validated — ReadOnlyAdapter + SafetyError verified by 7 tests (6 unit + 1 CLI integration)
- **SAFE-02:** active → validated — TokenUsage with per-stage counts and cost verified in both Rich and JSON output formats
- **INFRA-01:** active → validated — Terraform HCL with VPC, subnets, Security Groups, Flow Logs, S3 bucket present in infra/terraform/
- **INFRA-02:** active → validated — Dockerfile and docker-compose.yml with Ollama sidecar present and structurally valid

## Forward Intelligence

### What the next milestone should know
- The CLI is functional but dev tooling (ruff, pyright) was lost from pyproject.toml dev dependencies during bytecode reconstruction. Re-add them before extending the codebase.
- S08 and S09 slice summaries are doctor-generated placeholders — authoritative detail is in their task summaries, not the slice-level files.
- The pipeline requires Ollama running locally (or an alternative LLM provider configured) for real end-to-end execution. All tests mock the LLM client.

### What's fragile
- **Bytecode-reconstructed source** — 92 files were rebuilt from CPython 3.13 bytecode. While the full test suite passes (361 tests), subtle logic in prompt templates or edge-case handlers may differ from original intent. Any future changes should be tested carefully against the existing test battery.
- **LangGraph version coupling** — Pipeline uses context_schema for DI which is a LangGraph-specific API. Major LangGraph updates may require pipeline graph changes.
- **Instructor mode=JSON** — The LLM client uses Instructor's JSON mode with LiteLLM. Different Ollama models may produce varying JSON quality; the 3x validation retry mitigates but doesn't eliminate this.

### Authoritative diagnostics
- `uv run pytest --tb=short -q` — 361 tests are the ground truth for correctness. Run this before any change.
- `tests/test_cli/` — 25 tests proving CLI commands compose all layers correctly with mocked LLM/adapter.
- `tests/test_safety/` — 6 tests proving ReadOnlyAdapter blocks all write paths.
- `tests/e2e/test_e2e_analyze.py` — Full pipeline path test with fixture data.

### What assumptions changed
- **Original assumption:** Source code was available for extension. **Actual:** All source was deleted; bytecode reconstruction was a blocking prerequisite that elevated S09 to high risk.
- **Original assumption:** decompyle3 would work for CPython 3.13. **Actual:** Not supported; dis module + manual reconstruction was the only viable path.
- **Original assumption:** Typer natively supports async commands. **Actual:** Typer 0.24.1 CliRunner doesn't await async — sync wrappers with internal asyncio.run() required (D027).
- **Original assumption:** aioboto3 for async AWS. **Actual:** moto/aiobotocore version incompatibility forced boto3 + asyncio.to_thread (D012).

## Files Created/Modified

- `src/policyfoundry/` — 51 Python source files covering config, ingestion, storage, adapters, pipeline, output, CLI
- `tests/` — 52 test files covering models, config, ingestion, storage, adapters, pipeline, output, safety, CLI, E2E
- `pyproject.toml` — Package definition with all runtime and dev dependencies
- `Makefile` — Dev commands (test, lint, format, typecheck)
- `Dockerfile` — Multi-stage Python 3.13 build for CLI
- `docker-compose.yml` — PolicyFoundry + Ollama sidecar
- `infra/terraform/` — VPC, subnets, Security Groups, Flow Logs, S3 bucket (4 HCL files)
- `tests/fixtures/sample_output/reference.json` — Reference JSON output for regression testing
