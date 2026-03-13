# S10: Infrastructure And Packaging

**Goal:** PolicyFoundry is packaged for Docker, backed by Terraform-provisioned AWS test infrastructure, and proven end-to-end by an E2E test exercising the real CLI against fixture data.
**Demo:** `docker build` succeeds, `docker-compose config` validates, `terraform validate` passes, and `tests/e2e/test_e2e_analyze.py` exercises the full ingestion → storage → pipeline → output path through the real CLI entrypoint.

## Must-Haves

- E2E test exercising `policyfoundry analyze` through CliRunner with real file I/O (ingestion + storage + output) and mocked LLM/adapter
- Sample flow log fixture files in `tests/fixtures/sample_flowlogs/`
- Reference output fixtures in `tests/fixtures/sample_output/` (Rich content patterns + structural JSON)
- Multi-stage Dockerfile using `python:3.13-slim` + `uv` for fast reproducible builds
- `.dockerignore` excluding `.venv/`, `__pycache__/`, `.git/`, `.gsd/`, tests
- `docker-compose.yml` with PolicyFoundry service + Ollama sidecar, `POLICYFOUNDRY_LLM__BASE_URL=http://ollama:11434`
- Terraform HCL in `infra/terraform/` for VPC, subnets, Security Groups (with sample rules), VPC Flow Logs → S3
- All 349 existing tests still pass after additions

## Verification

- `.venv/bin/python -m pytest tests/e2e/ -v` — E2E tests pass, exercising both `--format rich` and `--format json`
- `.venv/bin/python -m pytest --tb=short -q` — full 349+ test suite passes (no regressions)
- `docker build -t policyfoundry:test .` — image builds successfully (if Docker available, otherwise `cat Dockerfile` review)
- `docker compose config` — compose file validates (if Docker available)
- `cd infra/terraform && terraform init -backend=false && terraform validate` — Terraform HCL is valid (if terraform available, otherwise HCL review)

## Tasks

- [x] **T01: E2E test with flow log fixtures and reference output** `est:45m`
  - Why: Proves the full CLI pipeline works end-to-end against realistic data before packaging. Creates the fixture files that the reference output captures depend on.
  - Files: `tests/fixtures/sample_flowlogs/vpc_flow_sample.log`, `tests/fixtures/sample_output/reference.json`, `tests/e2e/__init__.py`, `tests/e2e/conftest.py`, `tests/e2e/test_e2e_analyze.py`
  - Do: Create sample flow log fixture with valid v2 lines (reuse patterns from `tests/test_ingestion/conftest.py`). Write E2E test that uses CliRunner with real config → real ingestion → real storage → mocked LLM/adapter (D033), verifying both Rich and JSON output. Capture reference JSON output fixture for structural regression testing. Rich reference uses content pattern assertions (not byte-exact).
  - Verify: `.venv/bin/python -m pytest tests/e2e/ -v` passes; `.venv/bin/python -m pytest --tb=short -q` shows 349+ tests, 0 failures
  - Done when: E2E test exercises analyze command through real file I/O path and both output formats produce expected content

- [ ] **T02: Dockerfile, docker-compose, and .dockerignore** `est:30m`
  - Why: Packages PolicyFoundry for containerized usage (INFRA-02). Multi-stage build keeps image lean; Compose wires Ollama sidecar.
  - Files: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
  - Do: Multi-stage Dockerfile — builder stage copies `pyproject.toml`, `uv.lock`, `src/` and installs with `uv pip install`; runtime stage uses `python:3.13-slim` with only the installed package. Compose defines `policyfoundry` service (build context `.`) and `ollama` sidecar (`ollama/ollama:latest`) with `POLICYFOUNDRY_LLM__BASE_URL=http://ollama:11434`. `.dockerignore` excludes `.venv`, `__pycache__`, `.git`, `.gsd`, `tests`, `infra`.
  - Verify: `docker build -t policyfoundry:test .` succeeds (or Dockerfile review if Docker unavailable); `docker compose config` validates
  - Done when: Dockerfile builds a working image, compose config validates, .dockerignore excludes build artifacts

- [ ] **T03: Terraform HCL for test VPC with Security Groups and Flow Logs** `est:30m`
  - Why: Delivers INFRA-01 — bootstraps an AWS test environment users can `terraform apply` against a real account.
  - Files: `infra/terraform/main.tf`, `infra/terraform/variables.tf`, `infra/terraform/outputs.tf`, `infra/terraform/versions.tf`
  - Do: Write Terraform >= 1.9 HCL with AWS provider. Resources: VPC, 2 subnets (public/private), Security Group with sample ingress/egress rules (separate `aws_vpc_security_group_ingress_rule`/`aws_vpc_security_group_egress_rule` resources per AWS best practice), S3 bucket with random suffix for Flow Log delivery, IAM role + bucket policy for `delivery.logs.amazonaws.com`, VPC Flow Log to S3 in Parquet format. Variables for region, CIDR, and naming prefix. Outputs for VPC ID, SG ID, S3 bucket name.
  - Verify: `cd infra/terraform && terraform init -backend=false && terraform validate` passes (or HCL review if terraform unavailable)
  - Done when: `terraform validate` passes; plan would create expected resource set (VPC, SG, Flow Log, S3, IAM)

## Files Likely Touched

- `tests/fixtures/sample_flowlogs/vpc_flow_sample.log`
- `tests/fixtures/sample_output/reference.json`
- `tests/e2e/__init__.py`
- `tests/e2e/conftest.py`
- `tests/e2e/test_e2e_analyze.py`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `infra/terraform/main.tf`
- `infra/terraform/variables.tf`
- `infra/terraform/outputs.tf`
- `infra/terraform/versions.tf`
