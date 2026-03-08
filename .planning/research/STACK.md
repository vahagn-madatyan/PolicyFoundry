# Technology Stack

**Project:** PolicyFoundry
**Researched:** 2026-03-07
**Overall Confidence:** HIGH

## Recommended Stack

### Core Language & Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Core language | Rich LLM ecosystem, LangChain/LangGraph native, type hint maturity. 3.12 is the sweet spot -- 3.13 works but free-threading is still beta. Pin `>=3.12,<3.14`. | HIGH |
| uv | latest | Package manager | 10-100x faster than pip/poetry. Drop-in pip replacement. Uses standard `pyproject.toml`. The 2026 default for new Python projects -- no reason to start with pip or poetry anymore. | HIGH |

### CLI Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Typer | >=0.24.1 | CLI framework | Click-based, auto-help, type-hint-driven commands. As of 0.22.0, `typer-slim` is gone -- Rich and Shellingham are mandatory dependencies, so no extra install needed. | HIGH |
| Rich | >=14.3 | Terminal formatting | Tables, panels, progress bars, Markdown rendering. Bundled with Typer. Use `rich_markup_mode="rich"` on the Typer app for help text formatting. | HIGH |

### Data Validation & Configuration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pydantic | >=2.12 | Domain models, LLM structured output | Type-safe validation, JSON Schema generation for LLM structured output, `.model_dump()` / `.model_validate()` API. V2 is required -- V1 is incompatible with Python 3.14+ and deprecated across LangChain. | HIGH |
| pydantic-settings | >=2.13 | Configuration management | YAML + env var layered config. `BaseSettings` with `yaml_file` support. Replaces hand-rolled config loading. | HIGH |

### LLM Orchestration (LangChain Ecosystem)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LangGraph | >=1.0.10 | Agentic pipeline orchestration | StateGraph for the 4-stage pipeline, checkpointing, `interrupt_before` for human-in-the-loop. v1.0 is the first stable release -- production-proven at Uber, LinkedIn, Klarna. | HIGH |
| langgraph-checkpoint-sqlite | >=3.0.3 | Pipeline state persistence | Separate package from LangGraph core. Provides `SqliteSaver` and `AsyncSqliteSaver`. Import: `from langgraph.checkpoint.sqlite import SqliteSaver`. Must be explicitly installed. | HIGH |
| LangChain | >=1.2 | Foundation: tools, prompts, structured output | `with_structured_output()` for Pydantic model binding. v1.0+ deprecated `langgraph.prebuilt` -- use `langchain.agents.create_agent` if needed, though PolicyFoundry uses custom StateGraph nodes so this is informational only. | HIGH |
| langchain-litellm | >=0.6.1 | LangChain <> LiteLLM bridge | **Use this, NOT `langchain-community` ChatLiteLLM.** The community version was deprecated in v0.3.24 with removal planned for 1.0. `langchain-litellm` is the official replacement package. Provides `ChatLiteLLM` and `ChatLiteLLMRouter`. | HIGH |
| langchain-ollama | >=1.0.1 | Direct Ollama integration | For development, use `ChatOllama` directly (faster, no proxy overhead). In production config, route through LiteLLM. `with_structured_output()` works natively via Ollama's JSON schema mode. | MEDIUM |
| langchain-aws | >=1.3.1 | AWS Bedrock integration | `ChatBedrock` for Claude on Bedrock. Needed for future cloud provider support. Not required for Phase 1 (Ollama-only), but pin it now. | HIGH |
| LangSmith | >=0.7.14 | Observability & eval | Execution traces, prompt debugging, eval datasets. Optional but strongly recommended -- set `LANGCHAIN_TRACING_V2=true`. Free tier sufficient for development. | MEDIUM |

### LLM Routing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LiteLLM | >=1.82 | Multi-provider LLM proxy/router | 100+ providers via unified OpenAI-compatible interface. Cost tracking, fallback chains, budget limits. Use as the routing layer -- individual `langchain-*` packages handle the actual model communication. For Ollama: model format is `ollama/modelname`. | HIGH |

### Storage

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| DuckDB | >=1.4.4 | Embedded columnar analytics | Multi-GB flow log analytics on a laptop. Direct Parquet file querying without ETL. v1.4.0 is LTS with AES-256 encryption. **Note: No native async support.** Use `asyncio.to_thread()` or `aioduckdb` wrapper for async contexts. | HIGH |
| PyArrow | >=23.0 | Parquet read/write | Required for Parquet file I/O. DuckDB reads Parquet natively, but PyArrow is needed for writing normalized logs. **Breaking change: >=23.0 requires Python >=3.10** (fine for our 3.12+ target). Use zstd compression. | HIGH |
| SQLite (stdlib) | built-in | State, audit, checkpoints | LangGraph `SqliteSaver` uses it. Audit event store uses it. Zero-config, embedded, ACID. Use `aiosqlite` for async access. | HIGH |

### AWS Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| boto3 | >=1.42 | AWS SDK | Security Group CRUD, VPC Flow Log S3 access, future Bedrock. Pin `>=1.42` -- releases weekly, so don't pin exact version. Uses IAM credentials from environment/config. | HIGH |

### HTTP Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| httpx | >=0.28.1 | Async HTTP client | For threat intel API calls, future Palo Alto REST adapter. Native async, HTTP/2 support. v1.0 is in dev preview but not yet stable -- stick with 0.28.x. | HIGH |

### Test Infrastructure (AWS)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Terraform (HCL) | >=1.9 | Test AWS infrastructure | VPC, Security Groups, EC2 instances, VPC Flow Logs. Use plain HCL, **NOT CDKTF** -- HashiCorp deprecated CDKTF on December 10, 2025. Repository archived, no updates. | HIGH |

**Important: Do NOT use CDKTF (Terraform CDK) or AWS CDK for this project.**

- **CDKTF:** Deprecated December 2025. Archived. Dead. Do not adopt.
- **AWS CDK:** Tempting since the project is Python, but `aws-cdk-lib` only supports Python <=3.11 (incompatible with our 3.12+ requirement). Also adds massive dependency tree (jsii, Node.js runtime) for what amounts to ~100 lines of infrastructure code.
- **Terraform HCL:** Simple, well-documented, zero Python dependency conflicts. A `infra/` directory with 3-4 `.tf` files is all that's needed for the test environment.

### Utilities

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyYAML | >=6.0 | YAML config parsing | pydantic-settings YAML support. Lightweight, battle-tested. | HIGH |
| python-dotenv | >=1.0 | .env file loading | Development convenience for env vars. Not needed in production (env vars set directly). | HIGH |
| aiosqlite | >=0.21 | Async SQLite access | Required for `AsyncSqliteSaver` in LangGraph and async audit event storage. | HIGH |

## Development Dependencies

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | >=9.0 | Test framework | Standard Python test runner. v9.0 is current stable. | HIGH |
| pytest-asyncio | >=1.3 | Async test support | Required for testing async adapter/pipeline code. Use `asyncio_mode = "auto"` in pyproject.toml. | HIGH |
| pytest-cov | >=6.0 | Coverage reporting | Standard coverage plugin. | HIGH |
| moto | >=5.1 | AWS service mocking | Mock EC2, S3, IAM for adapter tests. Use `@mock_aws` decorator or `mock_aws()` context manager. Install with `moto[ec2,s3]` extras. | HIGH |
| ruff | >=0.15 | Linting + formatting | Replaces flake8, black, isort in a single Rust-powered tool. 10-100x faster than alternatives. The 2026 standard for Python projects. | HIGH |
| mypy | >=1.14 | Type checking | Static type analysis. Critical for Pydantic model correctness. Use `--strict` mode. | HIGH |
| pre-commit | >=4.0 | Git hook management | Run ruff + mypy on commit. Catches issues before CI. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI Framework | Typer + Rich | Click (raw) | Typer IS Click with type hints. No reason to use raw Click. |
| CLI Framework | Typer + Rich | argparse | No Rich integration, verbose boilerplate, poor DX. |
| LLM Orchestration | LangGraph | CrewAI | CrewAI abstracts too much. PolicyFoundry needs fine-grained control over pipeline state, checkpointing, and tool routing. LangGraph's StateGraph is the right abstraction level. |
| LLM Orchestration | LangGraph | AutoGen | Microsoft's framework. Good for multi-agent chat but wrong paradigm for a deterministic 4-stage pipeline. |
| LLM Routing | LiteLLM | Direct provider SDKs | Vendor lock-in. LiteLLM provides unified interface + cost tracking + fallback chains. Worth the dependency. |
| LLM Routing | LiteLLM | LangChain `init_chat_model` | `init_chat_model` works for simple cases but lacks LiteLLM's budget tracking, rate limiting, and 100+ provider support. Use both: LiteLLM for routing, `langchain-litellm` for LangChain integration. |
| Data Validation | Pydantic v2 | dataclasses | No validation, no JSON Schema generation, no `with_structured_output()` support. |
| Data Validation | Pydantic v2 | attrs | Good library but no LangChain integration for structured output. Pydantic is the ecosystem standard. |
| Storage (Analytics) | DuckDB | Polars | Polars is great for DataFrames but DuckDB provides SQL interface (better for LLM tool-calling -- LLMs write SQL, not DataFrame operations). |
| Storage (Analytics) | DuckDB | SQLite | SQLite is row-oriented. Flow log analytics (aggregations, group-bys over millions of rows) need columnar storage. DuckDB is 100x+ faster for these queries. |
| Package Manager | uv | Poetry | Poetry is slower, heavier, and uses non-standard lock format. uv is the 2026 default. |
| Package Manager | uv | pip | uv is a drop-in pip replacement that's 10-100x faster. No reason to use pip for a new project. |
| Linting | ruff | flake8 + black + isort | Three tools vs one. Ruff is faster and covers all three use cases. |
| Test Infra | Terraform HCL | CDKTF | **Deprecated December 2025.** Repository archived by HashiCorp. |
| Test Infra | Terraform HCL | AWS CDK | Python support stops at 3.11 (our project requires 3.12+). Adds Node.js/jsii dependency for ~100 lines of infra code. |
| Test Infra | Terraform HCL | Pulumi | Overkill for a test environment with 4-5 resources. Terraform HCL is simpler and universally understood. |
| Agent Framework | LangGraph (custom nodes) | Deep Agents | PROJECT.md explicitly drops Deep Agents. Niche library, LangGraph sub-graphs cover the same use cases natively. |
| HTTP Client | httpx | aiohttp | httpx has cleaner API, sync+async in one library, HTTP/2 support. aiohttp is async-only and more verbose. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| Deep Agents | Dropped per PROJECT.md. Niche, unnecessary -- LangGraph sub-graphs handle sub-agent patterns. |
| CDKTF | Deprecated December 2025. Archived. No maintenance. |
| AWS CDK (Python) | Python 3.11 max. Incompatible with our 3.12+ requirement. |
| `langchain-community` ChatLiteLLM | Deprecated in v0.3.24. Use `langchain-litellm` package instead. |
| `langchain-community` ChatOllama | Deprecated. Use `langchain-ollama` (dedicated package) instead. |
| `langgraph.prebuilt` | Deprecated in LangGraph 1.0. Use `langchain.agents` if prebuilt agents are needed. PolicyFoundry uses custom nodes, so this doesn't apply. |
| Vector (log ingestion) | Original architecture plan suggested Vector for log normalization. Unnecessary for CLI -- Python parsers handle the same job without a separate Rust binary dependency. |
| Kafka | Phase 2+ cloud feature. Not needed for CLI batch processing. |
| ClickHouse | Phase 2+ cloud feature. DuckDB covers CLI analytics. |
| PostgreSQL | Phase 2+ cloud feature. SQLite covers CLI state/audit. |
| Redis | Phase 2+ cloud feature. No caching layer needed for CLI. |
| Textual (TUI) | Optional nice-to-have. Do NOT include in Phase 1 scope -- Rich terminal output is sufficient. Defer to Phase 2. |

## LLM Integration Architecture Decision

There are two viable patterns for integrating LiteLLM + Ollama with LangGraph. Use **Pattern A**.

### Pattern A: langchain-litellm as universal adapter (RECOMMENDED)

```python
from langchain_litellm import ChatLiteLLM

# All providers routed through LiteLLM
llm = ChatLiteLLM(
    model="ollama/llama3.2",          # Ollama via LiteLLM
    api_base="http://localhost:11434",
    temperature=0.1,
    max_tokens=4096,
)

# Structured output works via LiteLLM's OpenAI-compatible interface
structured_llm = llm.with_structured_output(TrafficAnalysis)
result = await structured_llm.ainvoke(messages)
```

**Why:** Single code path for all providers. Swap `ollama/llama3.2` for `bedrock/anthropic.claude-sonnet-4-20250514` with zero code changes. Cost tracking and fallback chains come free.

### Pattern B: Direct langchain-ollama for dev, LiteLLM for prod (ALTERNATIVE)

```python
# Development (faster, no proxy overhead)
from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3.2", temperature=0.1)

# Production (multi-provider routing)
from langchain_litellm import ChatLiteLLM
llm = ChatLiteLLM(model="bedrock/anthropic.claude-sonnet-4-20250514")
```

**Why not:** Two code paths. Config-driven switching adds complexity for marginal performance gain. LiteLLM's Ollama overhead is negligible for a batch CLI.

## DuckDB Async Strategy

DuckDB has no native async Python support. For PolicyFoundry's async architecture:

```python
import asyncio
import duckdb

async def query_traffic_stats(query: str) -> list[dict]:
    """Run DuckDB queries without blocking the event loop."""
    def _execute():
        conn = duckdb.connect("flow_logs.duckdb")
        return conn.execute(query).fetchdf().to_dict("records")

    return await asyncio.to_thread(_execute)
```

**Rationale:** `asyncio.to_thread()` is stdlib, zero dependencies, and sufficient for CLI batch processing where DuckDB queries are the primary bottleneck (not concurrent I/O). The `aioduckdb` package exists but is unmaintained and unnecessary for this use case.

## Installation

```bash
# Initialize project with uv
uv init policyfoundry
cd policyfoundry

# Core dependencies
uv add \
    typer>=0.24.1 \
    rich>=14.3 \
    pydantic>=2.12 \
    pydantic-settings>=2.13 \
    langgraph>=1.0.10 \
    langgraph-checkpoint-sqlite>=3.0.3 \
    langchain>=1.2 \
    langchain-litellm>=0.6.1 \
    langchain-ollama>=1.0.1 \
    langchain-aws>=1.3.1 \
    langsmith>=0.7.14 \
    litellm>=1.82 \
    duckdb>=1.4.4 \
    pyarrow>=23.0 \
    boto3>=1.42 \
    httpx>=0.28.1 \
    pyyaml>=6.0 \
    python-dotenv>=1.0 \
    aiosqlite>=0.21

# Dev dependencies
uv add --dev \
    pytest>=9.0 \
    pytest-asyncio>=1.3 \
    pytest-cov>=6.0 \
    "moto[ec2,s3]>=5.1" \
    ruff>=0.15 \
    mypy>=1.14 \
    pre-commit>=4.0
```

## pyproject.toml Reference

```toml
[project]
name = "policyfoundry"
version = "0.1.0"
requires-python = ">=3.12,<3.14"
description = "AI-powered firewall policy management CLI"
license = { text = "BSL-1.1" }

dependencies = [
    # CLI
    "typer>=0.24.1",
    "rich>=14.3",

    # Data Validation
    "pydantic>=2.12",
    "pydantic-settings>=2.13",

    # LangChain Ecosystem
    "langgraph>=1.0.10",
    "langgraph-checkpoint-sqlite>=3.0.3",
    "langchain>=1.2",
    "langchain-litellm>=0.6.1",
    "langchain-ollama>=1.0.1",
    "langchain-aws>=1.3.1",
    "langsmith>=0.7.14",

    # LLM Routing
    "litellm>=1.82",

    # Storage
    "duckdb>=1.4.4",
    "pyarrow>=23.0",
    "aiosqlite>=0.21",

    # AWS
    "boto3>=1.42",

    # HTTP
    "httpx>=0.28.1",

    # Config
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.3",
    "pytest-cov>=6.0",
    "moto[ec2,s3]>=5.1",
    "ruff>=0.15",
    "mypy>=1.14",
    "pre-commit>=4.0",
]

[project.scripts]
policyfoundry = "policyfoundry.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "TCH"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

## Version Pinning Strategy

- **Minimum version pins** (`>=X.Y`) for most dependencies -- allows patch updates.
- **No exact pins** except Python itself (`>=3.12,<3.14`).
- **Lock file** generated by `uv lock` captures exact resolved versions for reproducibility.
- **boto3**: Pin `>=1.42`, never exact -- AWS releases weekly and exact pins cause dependency hell.
- **LangChain ecosystem**: All pinned to current major version (`>=1.x`) to stay within the v1.0 stability commitment.

## Key Version Changes from Original Spec

The original `02-implementation-spec.md` has outdated versions. Here are the corrections:

| Package | Original Spec | Current Version | Notes |
|---------|--------------|-----------------|-------|
| langgraph | >=0.2 | >=1.0.10 | v1.0 GA released. Major milestone. |
| langchain | >=0.3 | >=1.2 | v1.0 GA released alongside LangGraph 1.0. |
| langchain-community | >=0.3 | **REMOVE** | ChatLiteLLM deprecated here. Use `langchain-litellm` instead. |
| deepagents | >=0.1 | **REMOVE** | Dropped per PROJECT.md decision. |
| litellm | >=1.40 | >=1.82 | Active development, fast release cycle. |
| duckdb | >=1.0 | >=1.4.4 | v1.4.0 is LTS. |
| pyarrow | >=17.0 | >=23.0 | Major version jump. Now requires Python >=3.10. |
| typer | >=0.12 | >=0.24.1 | Many releases since spec was written. |
| rich | >=13.7 | >=14.3 | Major version bump. |
| pytest | >=8.0 | >=9.0 | Major version bump. |
| pytest-asyncio | >=0.23 | >=1.3 | Major version bump to 1.x. |
| moto | >=5.0 | >=5.1.21 | Minor updates. |
| ruff | >=0.5 | >=0.15 | Significant updates. |
| textual | >=0.70 | **DEFER** | Not needed for Phase 1. |
| langchain-aws | >=0.2 | >=1.3.1 | Major version bump. |
| langsmith | >=0.1 | >=0.7.14 | Significant updates. |
| N/A | N/A | langgraph-checkpoint-sqlite>=3.0.3 | **NEW.** Separate package, must be explicitly installed. |
| N/A | N/A | langchain-litellm>=0.6.1 | **NEW.** Replaces deprecated community package. |
| N/A | N/A | langchain-ollama>=1.0.1 | **NEW.** Dedicated Ollama integration. |
| N/A | N/A | aiosqlite>=0.21 | **NEW.** Required for async SQLite access. |

## Sources

- [LangGraph PyPI](https://pypi.org/project/langgraph/) - v1.0.10 verified 2026-03-07
- [LangGraph 1.0 GA announcement](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [LangGraph v1 migration guide](https://docs.langchain.com/oss/python/migrate/langgraph-v1)
- [LangChain PyPI](https://pypi.org/project/langchain/) - v1.2.10 verified
- [langchain-litellm PyPI](https://pypi.org/project/langchain-litellm/) - v0.6.1 verified
- [langchain-ollama PyPI](https://pypi.org/project/langchain-ollama/) - v1.0.1 verified
- [langchain-aws PyPI](https://pypi.org/project/langchain-aws/) - v1.3.1 verified
- [langgraph-checkpoint-sqlite PyPI](https://pypi.org/project/langgraph-checkpoint-sqlite/) - v3.0.3 verified
- [LiteLLM PyPI](https://pypi.org/project/litellm/) - v1.82.0 verified
- [LiteLLM Ollama docs](https://docs.litellm.ai/docs/providers/ollama)
- [LiteLLM structured output docs](https://docs.litellm.ai/docs/completion/json_mode)
- [DuckDB PyPI](https://pypi.org/project/duckdb/) - v1.4.4 verified
- [DuckDB async discussion](https://github.com/duckdb/duckdb/discussions/3560)
- [PyArrow PyPI](https://pypi.org/project/pyarrow/) - v23.0.1 verified
- [Pydantic PyPI](https://pypi.org/project/pydantic/) - v2.12.5 verified
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) - v2.13.1 verified
- [Typer PyPI](https://pypi.org/project/typer/) - v0.24.1 verified
- [Rich PyPI](https://pypi.org/project/rich/) - v14.3.3 verified
- [boto3 PyPI](https://pypi.org/project/boto3/) - v1.42.63 verified
- [httpx PyPI](https://pypi.org/project/httpx/) - v0.28.1 verified
- [moto PyPI](https://pypi.org/project/moto/) - v5.1.21 verified
- [LangSmith PyPI](https://pypi.org/project/langsmith/) - v0.7.14 verified
- [pytest PyPI](https://pypi.org/project/pytest/) - v9.0.2 verified
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) - v1.3.0 verified
- [ruff PyPI](https://pypi.org/project/ruff/) - v0.15.5 verified
- [aws-cdk-lib PyPI](https://pypi.org/project/aws-cdk-lib/) - v2.241.0, Python <=3.11
- [CDKTF deprecation announcement](https://ascii.co.uk/news/article/news-20251219-002e4264/cdk-for-terraform-officially-deprecated-after-five-years)
- [LangChain structured output docs](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Ollama structured outputs blog](https://ollama.com/blog/structured-outputs)
- [Python package managers 2026 comparison](https://scopir.com/posts/best-python-package-managers-2026/)
