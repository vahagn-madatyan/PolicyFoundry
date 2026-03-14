# M001: PolicyFoundry MVP

**Vision:** PolicyFoundry is an AI-powered firewall policy management CLI tool that ingests VPC Flow Logs, analyzes traffic patterns through a multi-stage LLM pipeline, queries existing firewall rules, and suggests justified rule changes — all from a polished terminal interface. The MVP delivers the full pipeline from log ingestion to risk-scored recommendations, operating in suggest-only mode with Ollama as the default local LLM provider.

## Success Criteria

- User can run `policyfoundry analyze` with local flow log files and see a Rich terminal report with color-coded risk tables, traffic summary, and justified rule proposals
- User can run `policyfoundry analyze --format json` and receive a complete JSON document containing all pipeline stage results suitable for piping to other tools
- The tool never modifies firewall rules — every operation is read-only, and any attempt to apply changes raises a clear `SafetyError`
- Each pipeline run displays token usage (prompt/completion tokens per stage) and estimated cost in the output footer
- All CLI commands show useful `--help` text and surface actionable error messages (not stack traces) on failure
- User can bootstrap an AWS test environment via `terraform apply` in the `infra/` directory and run PolicyFoundry against it end-to-end
- PolicyFoundry runs in a Docker container via `docker-compose up` with Ollama sidecar

## Key Risks / Unknowns

- **Source code deleted — only bytecode remains.** All 48 src `.py` files and 44 test `.py` files have been deleted from disk. Only `.pyc` bytecode exists in `__pycache__/` directories. `pyproject.toml` is also missing. Source must be reconstructed from bytecode before any new code can be written or tests can run. Decompiler support for CPython 3.13 bytecode is uncertain.
- **CLI integration surfaces hidden coupling.** Wiring config → ingestion → storage → adapter → pipeline → output through a single CLI command is where latent integration bugs appear. Each layer was tested in isolation with mocks; the real composition hasn't been exercised.
- **Terraform + Docker require external service dependencies.** E2E tests need a real AWS account (Terraform) and Ollama running (Docker). CI environments may not have these, requiring careful test isolation.

## Proof Strategy

- **Source reconstruction reliability** → Retire in S09 by decompiling all `.pyc` files, running the full test suite (300+ tests from S01–S08), and confirming zero regressions before writing any new code.
- **CLI integration coupling** → Retire in S09 by building integration tests that exercise the real CLI entrypoint (`policyfoundry analyze`) against fixture data with mocked LLM/adapter, proving all layers compose without error.
- **E2E in real environment** → Retire in S10 by running the full Docker-composed stack against Terraform-provisioned AWS resources or realistic fixture data.

## Verification Classes

- **Contract verification:** pytest unit/integration tests for all modules (300+ tests through S08, growing with S09), pyright strict on src/, ruff linting
- **Integration verification:** S09 CLI integration tests composing real modules (config → ingestion → storage → pipeline → output) with mocked LLM; S10 E2E tests against real or fixture data
- **Operational verification:** S10 Docker container lifecycle (build, run, produce output); Terraform plan/apply/destroy cycle
- **UAT / human verification:** S09 UAT: user runs `policyfoundry analyze` with sample data and visually confirms Rich output quality; S10 UAT: user runs Docker stack and Terraform provisioning

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 10 slices are complete with passing verification
- All source `.py` files exist on disk (not just bytecode) and the full test suite passes
- `policyfoundry analyze` with sample data produces a Rich report showing traffic analysis, security assessment, proposals, and decisions with color-coded risk levels
- `policyfoundry analyze --format json` produces valid, parseable JSON with all pipeline stage data
- Token usage and estimated cost are displayed in every pipeline run output
- No code path exists that can modify firewall rules — `ReadOnlyAdapter` wraps all adapter access and `SafetyError` is raised on any write attempt
- Terraform in `infra/` can provision a test VPC with Security Groups and Flow Logs
- `docker-compose up` launches PolicyFoundry with Ollama sidecar and produces analysis output
- All success criteria are re-verified against the live CLI (not just test assertions)

## Requirement Coverage

- **Covers:** OUT-01 (S09 primary), OUT-02 (S09 primary), SAFE-01 (S09 primary), SAFE-02 (S09 primary — token usage surfaced through CLI), INFRA-01 (S10 primary), INFRA-02 (S10 primary)
- **Validated (delivered by S01–S08):** INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, ADAPT-01, ADAPT-02, ADAPT-03, PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, CONF-01, CONF-02
- **Leaves for later:** None
- **Orphan risks:** None — all Active requirements are mapped to S09 or S10

## Slices

- [x] **S01: Project Foundation** `risk:medium` `depends:[]`
  > After this: Python project bootstrapped with src/ layout, domain models (NormalizedFlowLog, UniversalRule), dev tooling (Ruff, Pyright, pytest), and all validation tests passing. Verified by 300+ tests through S08 bytecode.

- [x] **S02: Configuration System** `risk:medium` `depends:[S01]`
  > After this: Pydantic Settings configuration loads from YAML files and environment variables with proper merge priority, verified by config round-trip tests.

- [x] **S03: Log Ingestion** `risk:medium` `depends:[S02]`
  > After this: VPC Flow Log v2 parser ingests local files and S3 objects, normalizes to 10-field schema, deduplicates records, verified by ingestion tests against sample logs.

- [x] **S04: Storage Layer** `risk:medium` `depends:[S03]`
  > After this: Normalized logs persist as zstd-compressed Parquet files, DuckDB analytics queries (top_talkers, traffic_summary, denied_flows, traffic_by_protocol) return results, verified by storage round-trip tests.

- [x] **S05: Firewall Adapter** `risk:medium` `depends:[S04]`
  > After this: AWS SG adapter fetches rules via boto3, translates to UniversalRule format, validates proposals against SG constraints (allow-only, 60-rule limit, wide-open CIDR rejection), verified by adapter tests with moto mocks.

- [x] **S06: LLM Integration** `risk:medium` `depends:[S05]`
  > After this: LLMClient produces validated Pydantic models from LLM calls via Instructor + LiteLLM, with Ollama health checking and retry logic, verified by unit tests with mocked Instructor client.

- [x] **S07: Pipeline Core** `risk:medium` `depends:[S06]`
  > After this: 5-stage LangGraph pipeline (Analyze → Assess → Generate → Validate → Decide) executes end-to-end with PipelineContext DI and partial-result error handling, verified by 62 pipeline tests including 7 full integration tests.

- [x] **S08: Output And Safety** `risk:medium` `depends:[S07]`
  > After this: Pipeline results render as Rich terminal tables with color-coded risk levels or export as structured JSON. LLMClient tracks token usage and cost per stage. Verified by formatter and safety tests against realistic pipeline output fixtures.

- [x] **S09: CLI Integration** `risk:high` `depends:[S08]`
  > After this: User runs `policyfoundry analyze --source local --format rich` and sees a complete Rich report with traffic analysis, rule proposals, risk tables, and cost summary. `--format json` outputs machine-readable JSON. `policyfoundry rules` displays current SG rules. ReadOnlyAdapter enforces suggest-only mode. All commands have `--help` text and show actionable errors on failure. Source code recovered from bytecode and full test suite passing.

- [x] **S10: Infrastructure And Packaging** `risk:low` `depends:[S09]`
  > After this: User runs `terraform apply` in `infra/` to create a test VPC with Security Groups and Flow Logs. `docker-compose up` launches PolicyFoundry with Ollama sidecar. E2E test proves the full pipeline from ingestion to Rich output against realistic fixture data.

## Boundary Map

### S01–S08 (completed) → S09

Produces (available as `.pyc` bytecode — source files must be reconstructed):

- `config/loader.py` → `load_config(**overrides) -> PolicyFoundryConfig` — config entry point reading YAML + env vars
- `config/models.py` → `PolicyFoundryConfig(BaseSettings)` with nested `LLMConfig`, `SourcesConfig`, `TargetsConfig`, `OutputConfig`
- `pipeline/runner.py` → `async run_pipeline(llm_client: LLMClient, adapter: FirewallAdapter, data_dir: str, sg_ids: list[str]) -> PipelineState`
- `pipeline/llm.py` → `create_llm_client(config: LLMConfig) -> LLMClient` (factory with Ollama health check), `LLMClient.get_usage() -> TokenUsage`
- `pipeline/graph.py` → `PipelineContext(llm_client, adapter, data_dir)` dataclass, `build_pipeline() -> CompiledGraph`
- `pipeline/state.py` → `PipelineState` TypedDict (total=False) with: `run_id`, `started_at`, `current_stage`, `flow_log_path`, `sg_ids`, `analysis`, `assessment`, `proposals`, `decisions`, `token_usage`
- `pipeline/schema.py` → `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision` Pydantic models
- `adapters/base.py` → `FirewallAdapter` ABC: `get_rules()`, `validate()`, `capabilities()`
- `adapters/registry.py` → `AdapterRegistry.get_adapter(name, **kwargs) -> FirewallAdapter` (static, entry_points + built-in aws_sg)
- `adapters/aws_sg/adapter.py` → `AwsSecurityGroupAdapter(security_group_id, *, region=None)`
- `adapters/schema.py` → `RiskLevel` StrEnum, `UniversalRule`, `ValidationResult`, `AdapterCapabilities`, `Direction`, `RuleAction`, `PortRange`, `NetworkEndpoint`
- `output/rich_output.py` → `format_rich(state: PipelineState, *, console=None) -> None` — full Rich terminal report
- `output/json_output.py` → `format_json(state: PipelineState) -> str` — JSON serialization via PipelineResult
- `output/models.py` → `TokenUsage` (dataclass), `PipelineResult` (Pydantic with `from_state` classmethod)
- `ingestion/local.py` → `async ingest_local_files(paths) -> IngestionResult`
- `storage/writer.py` → `async write_records(records, data_dir, source_files) -> WriteResult`
- `exceptions.py` → `PolicyFoundryError` hierarchy: `ConfigError`, `IngestionError`, `StorageError`, `AdapterError`, `PipelineError`, `OutputError` (each with `error_code`, `details`)
- `tests/test_safety/test_readonly_adapter.py` (.pyc) → 6 pre-existing tests importing `ReadOnlyAdapter` from `policyfoundry.adapters.safety` and `SafetyError` from `policyfoundry.exceptions`
- `tests/test_output/conftest.py` (.pyc) → `sample_pipeline_state`, `sample_pipeline_state_no_tokens`, `sample_pipeline_state_empty` fixtures

Consumes:
- nothing (all upstream)

### S09 → S10

Produces:
- `main.py` → Typer `app` with commands: `analyze` (run pipeline + format output), `rules` (fetch and display SG rules), `config` (show resolved config)
- `__main__.py` → entry point calling `main` function (matches `policyfoundry.__main__:main` in entry_points.txt)
- `adapters/safety.py` → `ReadOnlyAdapter(wrapped: FirewallAdapter)` — delegates reads, raises `SafetyError` on writes
- `exceptions.py` (modified) → `SafetyError(PolicyFoundryError)` added to hierarchy
- `pyproject.toml` (reconstructed) → package definition with all dependencies including `typer>=0.24.1`, entry points, dev deps
- Error handling middleware catching `PolicyFoundryError` subtypes → Rich-formatted actionable messages
- Progress display during LLM inference → Rich `Status` spinner with stage name
- Integration tests in `tests/test_cli/` → CliRunner-based tests exercising analyze/rules/config commands with mocked LLM

Consumes from S01–S08:
- Every module listed above (all `.pyc` bytecode reconstructed to `.py` source)

### S10 (terminal slice)

Produces:
- `infra/terraform/` → Terraform HCL: VPC, subnets, Security Groups with sample rules, VPC Flow Logs to S3
- `Dockerfile` → multi-stage build for PolicyFoundry CLI
- `docker-compose.yml` → PolicyFoundry + Ollama sidecar
- `tests/e2e/` → E2E test exercising `policyfoundry analyze` against fixture or real data
- `tests/fixtures/sample_output/` → Reference Rich and JSON output for regression testing

Consumes from S09:
- `policyfoundry` CLI command (the real entrypoint being packaged and tested)
- All reconstructed source files and passing test suite
