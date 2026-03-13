# S10: Infrastructure And Packaging — Research

**Date:** 2026-03-12

## Summary

S10 is the terminal slice delivering three distinct deliverables: Terraform HCL for a test AWS environment, Docker/Compose packaging, and E2E tests with reference output fixtures. All S09 outputs are confirmed present and the 349-test suite passes. No source files, Docker artifacts, Terraform configs, E2E tests, or fixture files exist yet — this is a clean-room build.

The slice is genuinely low-risk. All three deliverables are standard infrastructure patterns with no novel integration challenges. The Terraform resources (VPC, subnets, SGs, Flow Logs → S3) are well-documented with the AWS provider. The Dockerfile is a standard multi-stage Python build using hatchling. Docker Compose wires PolicyFoundry to an Ollama sidecar. The E2E test exercises the CLI against local fixture data with mocked LLM — same pattern as the existing `tests/test_cli/` integration tests but with real file I/O through the full ingestion → storage → pipeline → output path.

The main constraint is that E2E tests cannot require a running Ollama instance or AWS credentials in CI. The existing test suite already solved this with mocks at the LLM and adapter boundaries. The E2E test follows the same pattern: real ingestion + storage + output, mocked LLM + adapter.

## Recommendation

Build in this order: (1) sample flow log fixture files, (2) E2E test exercising the CLI end-to-end against fixtures with mocked LLM, (3) reference output capture (Rich text + JSON), (4) Dockerfile with multi-stage build, (5) docker-compose.yml with Ollama sidecar, (6) Terraform HCL for test VPC.

Rationale: Fixtures are needed by E2E tests. E2E tests validate the CLI works before we package it. Docker packages a known-working CLI. Terraform is independent and can be built last.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Multi-stage Python Docker build | `python:3.13-slim` + `uv` for fast installs | Standard pattern; uv is 10-100x faster than pip in container builds |
| Ollama sidecar | `ollama/ollama:latest` official image | Well-maintained, GPU-aware, standard compose sidecar pattern |
| VPC Flow Log fixture data | Existing format from `tests/test_ingestion/conftest.py` | Already has valid v2 lines with ACCEPT/NODATA/malformed cases |
| CLI testing pattern | `tests/test_cli/` uses `typer.testing.CliRunner` + mock boundaries | Proven pattern from S09; E2E extends it with real file I/O |
| Pipeline state fixtures | `tests/test_cli/conftest.py::sample_pipeline_state` and `tests/test_output/conftest.py::sample_pipeline_state` | Both provide complete PipelineState dicts matching real pipeline output shape |

## Existing Code and Patterns

- `tests/test_cli/conftest.py` — `_make_mocks(sample_state)` creates coordinated mock set for LLM + adapter + config. E2E test should follow this mock boundary: mock LLMClient and FirewallAdapter, keep real config/ingestion/storage/output (D033).
- `tests/test_cli/test_analyze.py` — 14 tests exercising analyze command through CliRunner. E2E test adds real file ingestion + Parquet write + DuckDB query on top of this pattern.
- `tests/test_output/conftest.py` — `sample_pipeline_state` fixture with realistic TrafficAnalysis, SecurityAssessment, PolicyProposal, and RuleDecision data. Use this as the reference output fixture source.
- `tests/test_ingestion/conftest.py` — `valid_vpc_v2_line` and multi-line flow log fixtures. Use these as the basis for `tests/fixtures/sample_flowlogs/`.
- `src/policyfoundry/pipeline/llm.py` — `_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"`. Docker Compose needs to override this to `http://ollama:11434` via `POLICYFOUNDRY_LLM__BASE_URL` env var.
- `src/policyfoundry/config/models.py` — `PolicyFoundryConfig` with env prefix `POLICYFOUNDRY_` and nested delimiter `__`. All Docker env vars must use this prefix.
- `pyproject.toml` — Entry point is `policyfoundry.__main__:main`. Build backend is `hatchling`. The wheel packages `src/policyfoundry`. 11 runtime dependencies.
- `src/policyfoundry/main.py` — `analyze` command takes `--source`, `--format`, `--sg-ids`, `--config`, `--debug`. E2E tests should exercise both `--format rich` and `--format json`.

## Constraints

- **Python 3.13.12** — The venv and all bytecode is CPython 3.13. Docker base image must be `python:3.13-slim` (not 3.12).
- **hatchling build backend** — `pyproject.toml` uses hatchling, not setuptools or poetry. Docker build must use `pip install .` or `uv pip install .` which invokes the hatchling backend.
- **No AWS credentials in CI** — E2E tests must not require real AWS credentials. Use the same mock pattern as existing CLI tests (mocked adapter).
- **No running Ollama in CI** — E2E tests must not require a running Ollama instance. Mock at the LLM client boundary.
- **uv.lock exists** — The project has a `uv.lock` file. Docker build should use `uv` for reproducible installs from the lock file.
- **src/ layout** — Package lives in `src/policyfoundry/`. Hatch config: `packages = ["src/policyfoundry"]`. Docker COPY must include `src/`.
- **Terraform >= 1.9** — Research specifies plain HCL, NOT CDKTF (deprecated Dec 2025). AWS provider resources: `aws_vpc`, `aws_subnet`, `aws_security_group`, `aws_vpc_security_group_ingress_rule`, `aws_vpc_security_group_egress_rule`, `aws_flow_log`, `aws_s3_bucket`, `aws_iam_role` (for Flow Log delivery).
- **349 existing tests must not regress** — All new tests are additive. Run full suite as verification.
- **Terraform best practice** — Use separate `aws_vpc_security_group_ingress_rule` / `aws_vpc_security_group_egress_rule` resources instead of inline `ingress`/`egress` blocks on `aws_security_group` (per current AWS provider docs).

## Common Pitfalls

- **Docker: PyArrow/DuckDB binary wheels** — These have large native binaries. Using `python:3.13-slim` (not `alpine`) avoids the need to compile from source. The slim image has the glibc these wheels need. Don't use Alpine — it uses musl and PyArrow/DuckDB prebuilt wheels won't work.
- **Docker: .dockerignore missing** — Without `.dockerignore`, the build context includes `.venv/`, `__pycache__/`, `.git/`, `.gsd/`, and test data. This bloats the build and can leak secrets. Create a `.dockerignore` that excludes these.
- **Docker Compose: Ollama model not pulled** — The Ollama sidecar starts empty. PolicyFoundry's health check (`_check_ollama_health`) will fail with `LLM_MODEL_NOT_FOUND` unless the model is pulled first. Add a `command` or entrypoint script that pulls the configured model on startup, or document it as a manual step.
- **Terraform: Flow Log IAM role** — VPC Flow Logs to S3 require an IAM role with `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` permissions. The S3 bucket also needs a bucket policy allowing `delivery.logs.amazonaws.com` to write. Missing this is the #1 Terraform Flow Log failure.
- **Terraform: S3 bucket naming** — S3 bucket names are globally unique. Use a random suffix or the AWS account ID to avoid collisions.
- **E2E test: tmp_path isolation** — E2E tests must write flow log fixtures to `tmp_path` and point `--config` to a temp config file that sets `sources.log_paths` and `output.data_dir` to temp directories. Don't write to the repo or home directory.
- **Reference output stability** — Rich terminal output includes ANSI escape codes and dynamic widths. Reference output fixtures for Rich should either strip ANSI or assert on content patterns, not exact byte-for-byte output. JSON reference output is stable and can be compared structurally.

## Open Risks

- **Terraform apply requires real AWS account** — The Terraform HCL can be validated (`terraform validate`, `terraform plan` with mock) but actual `terraform apply` requires an AWS account with billing. This is expected and documented in the milestone success criteria. The slice can be verified via `terraform validate` + `terraform plan` review.
- **Ollama model availability in Docker** — The compose stack requires pulling an Ollama model (e.g., `llama3.2`) which is ~2GB. First-run experience includes this download. Not a code risk but a UX friction point to document.
- **pyarrow 23.x wheel size** — The PyArrow wheel is ~30MB. Combined with DuckDB (~25MB), the Docker image will be ~500-700MB. This is acceptable for a CLI tool but worth noting.

## Requirements Owned

| Requirement | Deliverable | Verification |
|-------------|-------------|-------------|
| INFRA-01 — Terraform bootstraps AWS test environment | `infra/terraform/` with VPC, subnets, SGs, Flow Logs → S3 | `terraform validate` passes; `terraform plan` produces expected resource set |
| INFRA-02 — Dockerfile and docker-compose.yml | `Dockerfile` + `docker-compose.yml` | `docker build` succeeds; `docker-compose config` validates; container runs `policyfoundry --help` |

Additionally, the milestone DoD requires:
- E2E test proving full pipeline from ingestion to output (`tests/e2e/`)
- Reference output fixtures (`tests/fixtures/sample_output/`)

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Terraform | `hashicorp/agent-skills@terraform-style-guide` (1.7K installs) | available — HashiCorp official style guide |
| Terraform | `hashicorp/agent-skills@terraform-test` (972 installs) | available — HashiCorp test patterns |
| Docker | `github/awesome-copilot@multi-stage-dockerfile` (7.3K installs) | available — multi-stage build patterns |
| Docker | `sickn33/antigravity-awesome-skills@docker-expert` (5.7K installs) | available — general Docker expertise |

None installed. The `hashicorp/agent-skills@terraform-style-guide` and `github/awesome-copilot@multi-stage-dockerfile` are worth considering given they're from official/high-install sources and directly relevant.

## Sources

- Terraform AWS provider docs for `aws_flow_log` — Parquet format with S3 destination and per-hour partitions (source: context7 /hashicorp/terraform-provider-aws)
- Terraform AWS provider docs for `aws_security_group` — Separate ingress/egress rule resources recommended over inline blocks (source: context7 /hashicorp/terraform-provider-aws)
- Existing test patterns in `tests/test_cli/` — CliRunner + mock boundary pattern for E2E testing (source: codebase)
- D027 (Typer async strategy) — sync commands with internal `asyncio.run()` (source: DECISIONS.md)
- D033 (CLI integration test mock boundary) — mock LLMClient and FirewallAdapter; keep real config, ingestion, storage, output (source: DECISIONS.md)
- M001 Research — Terraform HCL >= 1.9, NOT CDKTF (deprecated Dec 2025), NOT AWS CDK (Python <=3.11) (source: M001-RESEARCH.md)
