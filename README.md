# PolicyFoundry

AI-powered firewall policy analysis and recommendation engine. Feed it VPC Flow Logs or Excel traffic exports and get back validated, risk-assessed firewall rule proposals — with optional change request form export.

---

## What It Does

PolicyFoundry ingests network traffic data, runs it through a multi-stage AI pipeline, and produces concrete firewall rule recommendations with risk assessments and justifications.

**Input:** VPC Flow Logs (local files or S3) or Excel traffic exports  
**Processing:** 5-stage LangGraph pipeline → Analyze → Assess → Generate → Validate → Decide  
**Output:** Rich terminal display, JSON, or exported change request forms (xlsx/pdf)

```
                  ┌──────────────┐
                  │  Traffic Data │
                  │ (Logs/Excel)  │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │   Ingestion   │  Parse, normalize, deduplicate
                  └──────┬───────┘
                         │
              ┌──────────▼──────────┐
              │   Analysis Pipeline  │
              │                      │
              │  Analyze  → Assess   │  LLM-powered stages via
              │  Generate → Validate │  LangGraph + Instructor
              │  Decide              │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │       Output         │
              │  Rich · JSON · xlsx  │
              │         · pdf        │
              └─────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Ollama](https://ollama.com/) running locally (default LLM provider)

### Install

```bash
# Clone the repository
git clone https://github.com/policyfoundry/policyfoundry.git
cd policyfoundry

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

### Pull the Default Model

PolicyFoundry uses `llama3.2` via Ollama by default:

```bash
ollama pull llama3.2
```

### Run Your First Analysis

**Analyze an Excel traffic export:**

```bash
policyfoundry analyze --source excel --file traffic.xlsx
```

**Analyze VPC Flow Logs from local files:**

```bash
policyfoundry analyze --source local --sg-ids sg-0123456789abcdef0
```

**Analyze VPC Flow Logs from S3:**

```bash
policyfoundry analyze --source s3 --sg-ids sg-0123456789abcdef0
```

## CLI Reference

### `policyfoundry analyze`

Run the analysis pipeline on VPC Flow Logs or Excel traffic exports.

```bash
policyfoundry analyze [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--source` | Log source type: `local`, `s3`, or `excel` | `local` |
| `--format` | Output format: `rich` or `json` | `rich` |
| `--file` | Path to input file (required for `--source excel`) | — |
| `--export` | Export format(s): `xlsx`, `pdf`, or `xlsx,pdf` | — |
| `--template` | Custom Excel template for change request export | — |
| `--sg-ids` | Security group IDs to analyze | — |
| `--config` | Path to YAML config file | — |
| `--debug` | Enable debug output and full tracebacks | `false` |

**Examples:**

```bash
# Excel analysis with JSON output
policyfoundry analyze --source excel --file traffic.xlsx --format json

# Excel analysis with change request export
policyfoundry analyze --source excel --file traffic.xlsx --export xlsx,pdf

# Excel analysis with custom template
policyfoundry analyze --source excel --file traffic.xlsx --export xlsx --template template.xlsx

# VPC Flow Log analysis with specific security groups
policyfoundry analyze --source local --sg-ids sg-abc123 --sg-ids sg-def456

# Full debug output
policyfoundry analyze --source excel --file traffic.xlsx --debug
```

### `policyfoundry rules`

Display current firewall rules from an adapter.

```bash
policyfoundry rules [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--adapter` | Adapter name | `aws_sg` |
| `--sg-id` | Security group ID to query | — |
| `--format` | Output format: `rich` or `json` | `rich` |

### `policyfoundry config`

Show the fully resolved configuration from all sources.

```bash
policyfoundry config [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--format` | Output format: `rich` or `json` | `rich` |

### Global Options

| Option | Description |
|--------|-------------|
| `--debug` | Enable debug output and full tracebacks |
| `--verbose` | Enable verbose logging |

## Configuration

PolicyFoundry uses a layered configuration system with the following merge priority (highest wins):

1. **CLI flags** (`--config`)
2. **Environment variables** (`POLICYFOUNDRY_` prefix)
3. **Local YAML** (`.policyfoundry.yaml` in current directory)
4. **Global YAML** (`~/.policyfoundry/config.yaml`)

### YAML Config File

Create `.policyfoundry.yaml` in your project directory:

```yaml
# LLM Provider Settings
llm:
  provider: ollama          # ollama | openai | bedrock
  model: llama3.2
  temperature: 0.1          # Lower = more deterministic
  max_tokens: 4096
  # base_url: null          # Custom API endpoint
  # api_key: null           # Prefer env var instead
  timeout: 120

# Log Sources
sources:
  log_paths:
    - /var/log/vpc-flow/*.log
    - ./logs/**/*.log.gz
  # s3_bucket: my-vpc-logs-bucket
  # s3_prefix: vpc-flow-logs/
  # aws_profile: default

# Target Security Groups
targets:
  security_group_ids:
    - sg-0123456789abcdef0

# Excel Ingestion Settings
excel:
  # sheet_name: null        # Default: first sheet
  # header_row: 1
  # column_mapping: null    # Override auto-detection

# Output Settings
output:
  format: rich              # rich | json
  data_dir: ~/.policyfoundry/data
```

### Environment Variables

All settings can be overridden with environment variables using the `POLICYFOUNDRY_` prefix and `__` for nesting:

```bash
# LLM settings
export POLICYFOUNDRY_LLM__PROVIDER=openai
export POLICYFOUNDRY_LLM__MODEL=gpt-4o
export POLICYFOUNDRY_LLM__API_KEY=sk-...
export POLICYFOUNDRY_LLM__BASE_URL=https://api.openai.com/v1

# Source settings
export POLICYFOUNDRY_SOURCES__S3_BUCKET=my-vpc-logs
export POLICYFOUNDRY_SOURCES__S3_PREFIX=flow-logs/
export POLICYFOUNDRY_SOURCES__LOG_PATHS=/var/log/flow1.log,/var/log/flow2.log

# Target settings
export POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS=sg-abc123,sg-def456
```

## Architecture

### Project Structure

```
src/policyfoundry/
├── __main__.py              # CLI entry point
├── main.py                  # Typer CLI app (analyze, rules, config)
├── exceptions.py            # Structured exception hierarchy
├── adapters/                # Firewall vendor adapters
│   ├── base.py              #   FirewallAdapter ABC
│   ├── registry.py          #   Plugin-based adapter registry
│   ├── safety.py            #   ReadOnlyAdapter wrapper
│   ├── schema.py            #   UniversalRule, ValidationResult
│   ├── null.py              #   NullAdapter for testing/Excel
│   └── aws_sg/              #   AWS Security Group adapter
│       ├── adapter.py       #     SG constraint validation
│       ├── client.py        #     boto3 SG API client
│       └── translator.py    #     SG rule → UniversalRule
├── analysis/                # Traffic analysis & aggregation
│   ├── models.py            #   AggregatedFlow, SubnetGroup
│   ├── direction.py         #   Traffic direction inference
│   ├── aggregator.py        #   Flow dedup & aggregation
│   └── subnet.py            #   Subnet grouping for CIDR candidates
├── config/                  # Configuration management
│   ├── models.py            #   Pydantic Settings models
│   ├── loader.py            #   Config load with merge priority
│   ├── defaults.py          #   Config template & source annotation
│   └── validation.py        #   Unknown key warnings
├── ingestion/               # Data ingestion
│   ├── local.py             #   Local file ingestion
│   ├── s3.py                #   S3 ingestion with gzip support
│   ├── excel.py             #   Excel traffic export parser
│   ├── column_detect.py     #   Auto column detection
│   ├── parser.py            #   VPC Flow Log line parser
│   ├── dedup.py             #   Record deduplication
│   └── schema.py            #   NormalizedFlowLog model
├── pipeline/                # AI analysis pipeline
│   ├── graph.py             #   LangGraph StateGraph (VPC logs)
│   ├── excel_graph.py       #   LangGraph StateGraph (Excel)
│   ├── llm.py               #   LLM client (Instructor + LiteLLM)
│   ├── runner.py            #   Pipeline runner (VPC logs)
│   ├── excel_runner.py      #   Pipeline runner (Excel)
│   ├── stages/              #   VPC log pipeline stages
│   │   ├── analyze.py       #     Traffic pattern analysis
│   │   ├── assess.py        #     Risk assessment
│   │   ├── generate.py      #     Rule proposal generation
│   │   ├── validate.py      #     Adapter constraint validation
│   │   └── decide.py        #     Final decision & justification
│   ├── excel_stages/        #   Excel pipeline stages
│   ├── prompts/             #   LLM prompt templates (VPC)
│   └── excel_prompts/       #   LLM prompt templates (Excel)
├── storage/                 # Data persistence
│   ├── writer.py            #   Parquet writer with cross-run dedup
│   ├── queries.py           #   DuckDB analytical queries
│   └── parquet_schema.py    #   Arrow schema definition
├── output/                  # Output formatting
│   ├── rich_output.py       #   Rich terminal renderer
│   ├── json_output.py       #   JSON output formatter
│   ├── excel_rich_output.py #   Excel pipeline Rich renderer
│   ├── excel_json_output.py #   Excel pipeline JSON formatter
│   └── models.py            #   TokenUsage tracking
└── export/                  # Change request export
    ├── change_request.py    #   xlsx + PDF generation
    └── models.py            #   ChangeRequestEntry model
```

### Pipeline Stages

Both the VPC Flow Log and Excel pipelines follow the same 5-stage architecture, built with [LangGraph](https://langchain-ai.github.io/langgraph/):

| Stage | Purpose |
|-------|---------|
| **Analyze** | Examines traffic patterns, identifies communication flows, detects anomalies |
| **Assess** | Evaluates risk levels for each identified pattern, flags high-risk flows |
| **Generate** | Produces concrete firewall rule proposals in universal format |
| **Validate** | Checks proposals against adapter constraints (e.g., AWS SG limits) |
| **Decide** | Makes final accept/modify/reject decisions with justifications |

### LLM Integration

PolicyFoundry uses [Instructor](https://github.com/instructor-ai/instructor) + [LiteLLM](https://github.com/BerriAI/litellm) for structured LLM output:

- **Structured output:** Every LLM call returns a validated Pydantic model — not free-form text
- **Dual retry layers:** Inner (Instructor validation retries) + outer (tenacity transient retries)
- **Provider flexibility:** Ollama, OpenAI, AWS Bedrock, or any LiteLLM-supported provider
- **Token tracking:** Per-stage token usage and cost tracking

### Adapter System

Firewall adapters implement the `FirewallAdapter` ABC and are loaded via Python entry points:

```python
class FirewallAdapter(ABC):
    async def get_rules(self) -> list[UniversalRule]: ...
    async def validate(self, rule: UniversalRule, ...) -> ValidationResult: ...
    def capabilities(self) -> AdapterCapabilities: ...
```

The included **AWS Security Group adapter** validates against AWS-specific constraints:
- Allow-only rules (no DENY/DROP/REJECT)
- 60 rules per direction limit
- CIDR notation validation
- Overly permissive source detection (`0.0.0.0/0`)

All adapters are wrapped in a `ReadOnlyAdapter` safety layer — PolicyFoundry never modifies live firewall rules.

## Docker

Run PolicyFoundry with an Ollama sidecar:

```bash
# Start services
docker compose up -d

# Pull the model into the Ollama container (first time only)
docker compose exec ollama ollama pull llama3.2

# Run analysis
docker compose run policyfoundry analyze --source excel --file /path/to/traffic.xlsx
```

The `docker-compose.yml` automatically sets `POLICYFOUNDRY_LLM__BASE_URL` to point at the Ollama container.

## Infrastructure

The `infra/terraform/` directory contains Terraform configuration for a test environment:

- VPC with public/private subnets
- Security group with sample ingress/egress rules
- S3 bucket for VPC Flow Log delivery
- VPC Flow Log configured for Parquet output with hourly partitioning
- IAM roles and policies for log delivery

```bash
cd infra/terraform
terraform init
terraform plan -var="name_prefix=policyfoundry-dev"
terraform apply
```

## Development

### Setup

```bash
# Clone and install dev dependencies
git clone https://github.com/policyfoundry/policyfoundry.git
cd policyfoundry
uv sync --group dev
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=policyfoundry

# Run a specific test module
uv run pytest tests/test_pipeline/test_excel_stages.py

# Run tests matching a pattern
uv run pytest -k "test_analyze"
```

### Project Conventions

- **Build system:** [Hatch](https://hatch.pypa.io/) (hatchling backend)
- **Dependency management:** [uv](https://docs.astral.sh/uv/) with `uv.lock`
- **Testing:** [pytest](https://pytest.org/) with `pytest-asyncio` (auto mode)
- **AWS mocking:** [moto](https://github.com/getmoto/moto) for S3 and EC2 tests
- **Linting:** [Ruff](https://docs.astral.sh/ruff/)
- **Models:** [Pydantic v2](https://docs.pydantic.dev/) throughout
- **Async:** All adapters, pipeline stages, and storage operations are async

### Key Dependencies

| Package | Purpose |
|---------|---------|
| `langgraph` | Multi-stage AI pipeline orchestration |
| `instructor` | Structured LLM output with Pydantic validation |
| `litellm` | Unified LLM provider interface |
| `pydantic` / `pydantic-settings` | Data models and config management |
| `typer` + `rich` | CLI framework and terminal formatting |
| `duckdb` | Analytical queries over Parquet storage |
| `pyarrow` | Parquet file I/O with zstd compression |
| `boto3` | AWS SDK (S3 ingestion, SG adapter) |
| `openpyxl` | Excel file reading and xlsx export |
| `fpdf2` | PDF change request generation |

## License

[Apache License 2.0](LICENSE)
