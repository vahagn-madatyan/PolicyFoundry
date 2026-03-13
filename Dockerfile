# ---------- builder ----------
FROM python:3.13-slim AS builder

# Install uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests and readme (layer cache)
COPY pyproject.toml uv.lock README.md ./

# Copy source tree
COPY src/ src/

# Install the project into the system Python.
RUN uv pip install --system .

# ---------- runtime ----------
FROM python:3.13-slim AS runtime

# Copy installed packages and entry-point scripts from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/policyfoundry /usr/local/bin/policyfoundry

ENTRYPOINT ["policyfoundry"]
