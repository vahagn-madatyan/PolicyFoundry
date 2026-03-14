---
id: T02
parent: S10
milestone: M001
provides:
  - Multi-stage Dockerfile producing lean runtime image with policyfoundry entrypoint
  - docker-compose.yml wiring PolicyFoundry + Ollama sidecar
  - .dockerignore keeping build context clean
key_files:
  - Dockerfile
  - docker-compose.yml
  - .dockerignore
key_decisions:
  - Used COPY --from for uv binary instead of curl install (simpler, cached layer)
  - Dropped --frozen from uv pip install (flag only valid for uv sync, not pip interface)
  - Included README.md in COPY for hatchling build metadata validation
patterns_established:
  - Docker multi-stage: builder with uv → runtime with only site-packages and entrypoint script
observability_surfaces:
  - none
duration: 10m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Dockerfile, docker-compose, and .dockerignore

**Packaged PolicyFoundry as a multi-stage Docker image with Ollama sidecar composition and clean build context.**

## What Happened

Created three files delivering INFRA-02. The Dockerfile uses a two-stage build: builder stage copies uv from the official ghcr image, installs the project with `uv pip install --system .`, then the runtime stage copies only site-packages and the entrypoint script from builder. Both stages use `python:3.13-slim` (not Alpine — PyArrow/DuckDB need glibc). The compose file wires PolicyFoundry with an Ollama sidecar, overriding `POLICYFOUNDRY_LLM__BASE_URL` to point at the container network hostname. The `.dockerignore` excludes venvs, caches, tests, infra, and dev files.

Two adjustments were needed during build verification: `--frozen` isn't valid for `uv pip install` (it's a `uv sync` flag), and `README.md` must be copied because hatchling validates the readme field during wheel build.

## Verification

- `docker build -t policyfoundry:test .` — builds successfully (85 packages installed, image produced)
- `docker run --rm policyfoundry:test --help` — CLI runs correctly inside container, shows all commands
- `docker compose config` — validates, shows correct service wiring and env override
- `.venv/bin/python -m pytest tests/e2e/ -v` — 12/12 E2E tests pass
- `.venv/bin/python -m pytest --tb=short -q` — 361 tests pass, 0 failures

## Diagnostics

None — infrastructure files only. Failures surface through `docker build` exit code and `docker compose config` validation output.

## Deviations

- Removed `--frozen` flag from `uv pip install` (not supported in pip interface, only in `uv sync`)
- Added `README.md` to COPY step (hatchling requires it for wheel metadata validation)

## Known Issues

None.

## Files Created/Modified

- `Dockerfile` — multi-stage build: builder with uv install, runtime with python:3.13-slim
- `docker-compose.yml` — PolicyFoundry + Ollama sidecar, POLICYFOUNDRY_LLM__BASE_URL override
- `.dockerignore` — excludes .venv, __pycache__, .git, .gsd, tests, infra, IDE files
