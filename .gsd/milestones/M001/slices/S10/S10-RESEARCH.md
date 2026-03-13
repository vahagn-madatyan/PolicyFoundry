# S10 ("Infrastructure And Packaging") — Research

**Date:** 2026-03-11

## Summary

S10 is the terminal slice of M001, responsible for delivering Terraform infrastructure (INFRA-01), Docker packaging (INFRA-02), E2E tests, and reference fixture output. The work decomposes into three independent workstreams: (1) Terraform HCL for an AWS test VPC with Security Groups and Flow Logs to S3, (2) a multi-stage Dockerfile using `uv` with an Ollama sidecar in `docker-compose.yml`, and (3) E2E tests exercising `policyfoundry analyze` against fixture data.

**However, a critical blocker exists:** No `.py` source files are on disk — only `.pyc` bytecode in `__pycache__/` directories. The `pyproject.toml` is also absent (only exists as installed dist-info metadata). No `uv.lock` exists. S09's summary is a doctor-created placeholder, and the source reconstruction prerequisite (D028) appears incomplete despite tasks being marked done. S10 cannot build a Docker image or run E2E tests against a codebase that has no importable source. **Before any S10 task begins, source files and `pyproject.toml` must exist on disk and the test suite must pass.** This is either a prerequisite fixup task within S10 or evidence that S09 is not truly complete.

The infrastructure and packaging work itself is straightforward once source exists. Terraform HCL for a test VPC is ~150 lines across 3-4 files. The Docker build follows the official `uv` Docker pattern from Astral. The Ollama sidecar is a standard `docker-compose` service with health checking.

## Recommendation

**Approach: Source Recovery First, Then Three Parallel Workstreams**

1. **T01: Verify/Recover Source** — Before anything else, confirm whether `.py` source files exist (perhaps uncommitted or in another branch). If not, reconstruct from `.pyc` bytecode using the `dis` module approach established in D032. Reconstruct `pyproject.toml` from the installed metadata (all dependency info is in `.venv/lib/python3.13/site-packages/policyfoundry-0.1.0.dist-info/METADATA`). Generate `uv.lock`. Run the full test suite to confirm zero regressions.

2. **T02: Terraform Infrastructure** — Write HCL in `infra/terraform/` with `main.tf`, `variables.tf`, `outputs.tf`. Create: VPC (10.0.0.0/16), public/private subnets, Internet Gateway, Security Groups with intentionally varied rules (some overly permissive for PolicyFoundry to catch), VPC Flow Logs to S3 in plain-text v2 format (matches the ingestion parser). Use `terraform plan` validation — do not require actual AWS credentials for CI.

3. **T03: Docker Packaging** — Multi-stage Dockerfile using `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` base. `docker-compose.yml` with two services: `policyfoundry` (the CLI) and `ollama` (sidecar). Health check on Ollama port 11434. Shared volume for flow log data. Config overrides via environment variables.

4. **T04: E2E Tests + Fixtures** — Create `tests/e2e/test_e2e_analyze.py` exercising the real CLI entrypoint with fixture flow log data and mocked LLM/adapter. Save reference Rich and JSON output to `tests/fixtures/sample_output/`. E2E tests prove the full pipeline from ingestion to formatted output in a single command invocation.

**Why this order:** T01 unblocks everything. T02-T04 are then independent and can be verified separately. T03 depends on `pyproject.toml` + `uv.lock` from T01. T04 depends on importable source from T01.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Python Docker builds with uv | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` base image | Official Astral image with uv pre-installed; follows Docker best practices for layer caching; `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy` optimizations built-in |
| Ollama in Docker | `ollama/ollama` image from Docker Hub | 50M+ pulls; exposes port 11434; volume mount for model persistence; CPU and GPU variants available |
| Terraform AWS VPC module | `hashicorp/terraform-provider-aws` resources | Direct use of `aws_vpc`, `aws_security_group`, `aws_flow_log`, `aws_s3_bucket` resources — simple enough to not need a module wrapper |
| VPC Flow Log sample data | Craft from AWS v2 format spec | The parser expects space-delimited v2 format (`version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status`); must match exactly |

## Existing Code and Patterns

- `src/policyfoundry/__pycache__/main.cpython-313.pyc` — Typer CLI with `analyze`, `rules`, `config` commands. Entry point is `policyfoundry.__main__:main`. Uses `asyncio.run()` internally (D027).
- `src/policyfoundry/__pycache__/exceptions.cpython-313.pyc` — `PolicyFoundryError` hierarchy with `SafetyError`, `ConfigError`, `IngestionError`, etc.
- `src/policyfoundry/adapters/__pycache__/safety.cpython-313.pyc` — `ReadOnlyAdapter` wrapping real adapters; raises `SafetyError` on writes.
- `tests/test_cli/__pycache__/conftest.cpython-313-pytest-9.0.2.pyc` — CLI test fixtures: `cli_runner`, `mock_llm_client`, `mock_llm_client_factory`, `mock_adapter`, `mock_adapter_factory`. E2E tests should reuse this mock boundary pattern (D033).
- `tests/test_output/__pycache__/conftest.cpython-313-pytest-9.0.2.pyc` — `sample_pipeline_state`, `sample_pipeline_state_no_tokens`, `sample_pipeline_state_empty` fixtures. Reuse for reference output generation.
- `tests/__pycache__/conftest.cpython-313-pytest-9.0.2.pyc` — Root fixtures: `valid_flow_log_data` dict, `valid_universal_rule_data` dict.
- `.venv/lib/python3.13/site-packages/policyfoundry-0.1.0.dist-info/METADATA` — Authoritative dependency list for reconstructing `pyproject.toml`.
- `.venv/lib/python3.13/site-packages/policyfoundry-0.1.0.dist-info/entry_points.txt` — Console script entry point and adapter plugin registration.

## Constraints

- **No `.py` source files on disk.** All 48 src files and 44 test files exist only as `.pyc` bytecode in `__pycache__/`. This is a hard blocker for Docker builds (which `COPY . /app`) and for any E2E test execution.
- **No `pyproject.toml` on disk.** Metadata exists in installed dist-info but the actual project file must be reconstructed. Required for `uv sync`, `uv lock`, and the Docker build.
- **No `uv.lock` file.** Must be generated after `pyproject.toml` is restored. The Docker build pattern mounts `uv.lock` for reproducible installs.
- **Python 3.13.12 in .venv** but `pyproject.toml` metadata says `>=3.12`. Docker image should target Python 3.12 (more widely tested/stable) per the stack research recommendation.
- **Terraform not installed locally.** `terraform` binary is not on PATH. Terraform HCL can be validated syntactically without it, but `terraform init/plan` requires installation. This is fine — S10 validation can defer actual `plan` to users with Terraform installed.
- **Docker and docker-compose are available.** Docker 29.2.1 and Docker Compose v5.0.2 are installed locally.
- **`instructor[litellm]>=1.14.5` is the LLM dependency** (D031), NOT `langchain-litellm`. The Dockerfile must install this, not the langchain variant from the original stack research.
- **Ollama Docker image is CPU-only by default.** GPU support requires `--gpus=all` flag and NVIDIA Container Toolkit. Docker Compose should document GPU as optional.
- **VPC Flow Log format must be v2 plain text** to match the existing parser. The parser expects 14 space-delimited fields: `version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status`. Terraform's `file_format` should default to `plain-text` (NOT `parquet`).
- **S09 mock boundary (D033):** E2E tests mock `LLMClient` and `FirewallAdapter` but exercise real config, ingestion, storage, and output modules. This pattern must be maintained in `tests/e2e/`.

## Common Pitfalls

- **Terraform Flow Logs in Parquet vs. plain-text.** The Terraform provider docs show a Parquet format example, but the PolicyFoundry ingestion parser expects plain-text v2 format (space-delimited). Using Parquet in Terraform would require a different ingestion path. **Use plain-text format** or omit `destination_options` entirely (defaults to plain-text).
- **Docker COPY before source exists.** If the Dockerfile assumes `src/` contains `.py` files, it will only copy `__pycache__/` directories with `.pyc` files, which won't work as an installed package. Source recovery is a strict prerequisite.
- **Missing `uv.lock` in Docker build.** The `uv sync --locked` pattern in the Dockerfile requires `uv.lock` to exist. Without it, the build fails. Must generate lockfile before first Docker build.
- **Ollama model not pre-pulled.** The Ollama sidecar starts empty — no models installed. Users need to `docker exec ollama ollama pull <model>` before running PolicyFoundry. Document this in a startup script or README, or add an entrypoint script that pulls a default model.
- **VPC Flow Log delivery delay.** Real AWS Flow Logs take 10-15 minutes after VPC creation to start appearing in S3. E2E tests against real AWS infra need this delay tolerance. Fixture-based E2E tests avoid this issue entirely.
- **S3 bucket naming collision.** Terraform S3 bucket names are globally unique. Use a random suffix or variable prefix to avoid `BucketAlreadyExists` errors.
- **Docker Compose `depends_on` vs. health check.** Using `depends_on` alone doesn't wait for Ollama to be ready — only for the container to start. Must use `depends_on.condition: service_healthy` with a health check on `http://localhost:11434`.
- **Editable install in Docker.** The current pip install is editable (`"editable": true` in direct_url.json). Docker builds should use `uv sync` with non-editable install (default for `uv sync` in Docker context).

## Open Risks

- **Source reconstruction fidelity.** If `.pyc` → `.py` reconstruction introduces subtle bugs, all downstream Docker/E2E work may fail in non-obvious ways. The test suite is the safety net, but it must pass first.
- **Docker image size.** The dependency tree (`instructor[litellm]`, `langgraph`, `boto3`, `pyarrow`, `duckdb`) is heavy. The final image could be 1-2 GB. Consider whether `--slim` variants or multi-stage pruning can reduce this.
- **E2E test flakiness with mock boundary.** E2E tests that mock LLM and adapter but exercise real ingestion and storage depend on correct fixture data format. If the flow log fixture doesn't match the parser's expectations, the test fails at ingestion, not at the point being tested.
- **Terraform state management.** The `infra/terraform/` directory needs a clear `terraform.tfstate` gitignore strategy and documentation about remote state backends for shared use.
- **Ollama sidecar startup time.** Pulling a model on first run can take 5-30 minutes depending on model size and network speed. First-run experience needs documentation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Terraform | (search timed out) | none found — low impact; Terraform HCL is self-documenting |
| Docker | no relevant skills | none found — standard Docker patterns apply |
| Ollama | `yoanbernabeu/grepai-skills@grepai-ollama-setup` (212 installs) | available — focused on Ollama setup/config, potentially useful for sidecar patterns |
| Ollama | `rawveg/skillsforge-marketplace@ollama` (77 installs) | available — general Ollama skill |

No skills are directly critical for this slice. Terraform HCL, Docker multi-stage builds, and docker-compose with sidecars are standard patterns well-covered by official documentation.

## Sources

- Package dependency list from installed metadata: `policyfoundry-0.1.0.dist-info/METADATA` — authoritative source for `pyproject.toml` reconstruction
- Entry points from `policyfoundry-0.1.0.dist-info/entry_points.txt` — `policyfoundry.__main__:main` console script and `aws_sg` adapter plugin
- Terraform AWS provider docs for `aws_flow_log`, `aws_vpc`, `aws_security_group` (source: [terraform-provider-aws](https://github.com/hashicorp/terraform-provider-aws))
- Official uv Docker guide and example Dockerfile (source: [docs.astral.sh/uv/guides/integration/docker/](https://docs.astral.sh/uv/guides/integration/docker/))
- Astral uv-docker-example reference Dockerfile (source: [github.com/astral-sh/uv-docker-example](https://github.com/astral-sh/uv-docker-example))
- Ollama Docker Hub image docs (source: [hub.docker.com/r/ollama/ollama](https://hub.docker.com/r/ollama/ollama))
- D027: Typer async strategy — sync commands with `asyncio.run()`
- D031: LLM dependency is `instructor[litellm]`, not `langchain-litellm`
- D032: Bytecode reconstruction method — `dis` module via same-version Python
- D033: CLI integration test mock boundary — mock LLM and adapter, keep real everything else
- Stack research (`.planning/research/STACK.md`) — Terraform HCL recommended, CDKTF deprecated Dec 2025, AWS CDK incompatible with Python 3.12+
