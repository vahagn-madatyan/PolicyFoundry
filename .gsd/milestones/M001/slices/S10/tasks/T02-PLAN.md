---
estimated_steps: 4
estimated_files: 3
---

# T02: Dockerfile, docker-compose, and .dockerignore

**Slice:** S10 — Infrastructure And Packaging
**Milestone:** M001

## Description

Package PolicyFoundry for containerized usage with a multi-stage Dockerfile, a docker-compose.yml wiring PolicyFoundry with an Ollama sidecar, and a .dockerignore to keep the build context clean. Delivers INFRA-02.

## Steps

1. Create `.dockerignore` excluding `.venv/`, `__pycache__/`, `.git/`, `.gsd/`, `tests/`, `infra/`, `*.pyc`, `.ruff_cache/`, `.pytest_cache/`.
2. Create `Dockerfile` with multi-stage build: **builder** stage uses `python:3.13-slim`, installs `uv`, copies `pyproject.toml`, `uv.lock`, and `src/`, runs `uv pip install --system .`; **runtime** stage uses `python:3.13-slim`, copies installed packages from builder, sets entrypoint to `policyfoundry`. Do NOT use Alpine (PyArrow/DuckDB need glibc).
3. Create `docker-compose.yml` with two services: `policyfoundry` (build context `.`, depends_on `ollama`, env `POLICYFOUNDRY_LLM__BASE_URL=http://ollama:11434`) and `ollama` (`ollama/ollama:latest`, exposes 11434). Include a comment noting that the Ollama model must be pulled before first use (`docker compose exec ollama ollama pull llama3.2`).
4. Verify: `docker build -t policyfoundry:test .` succeeds if Docker is available; otherwise review Dockerfile for correctness. `docker compose config` validates compose file.

## Must-Haves

- [ ] Multi-stage Dockerfile with `python:3.13-slim` base (not Alpine)
- [ ] `uv` used for package installation in builder stage
- [ ] `.dockerignore` excludes build artifacts, tests, and dev files
- [ ] `docker-compose.yml` includes PolicyFoundry + Ollama sidecar
- [ ] Ollama base URL overridden via `POLICYFOUNDRY_LLM__BASE_URL` env var
- [ ] Entrypoint runs `policyfoundry` CLI

## Verification

- `docker build -t policyfoundry:test .` succeeds (or Dockerfile review if Docker unavailable)
- `docker compose config` validates (or compose file review)
- `.dockerignore` exists and excludes expected patterns

## Inputs

- `pyproject.toml` — build backend (hatchling), dependencies, entry point
- `uv.lock` — lock file for reproducible installs
- `src/policyfoundry/config/models.py` — env prefix `POLICYFOUNDRY_`, nested delimiter `__`
- `src/policyfoundry/pipeline/llm.py` — `_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"`

## Expected Output

- `Dockerfile` — multi-stage build producing lean runtime image
- `docker-compose.yml` — PolicyFoundry + Ollama sidecar composition
- `.dockerignore` — clean build context
