# Policy Foundry

AI-powered firewall policy analysis and recommendation engine. Feed it traffic data and get back validated, risk-assessed firewall rule proposals with change request exports.

**Input:** Excel traffic exports or VPC Flow Logs (local/S3)
**Output:** Terminal display, JSON, or change request forms (xlsx/pdf)

```text
  Traffic Data  ──▶  AI Analysis Pipeline  ──▶  Change Request
  (Excel/Logs)       Analyze → Assess →         (xlsx / pdf /
                     Generate → Validate →       terminal / JSON)
                     Decide
```

---

## Installation

### Option 1: Install from PyPI (recommended)

```bash
pip install policy-foundry
```

### Option 2: Install with pipx (isolated environment)

```bash
pipx install policy-foundry
```

### Option 3: Install with uv

```bash
uv tool install policy-foundry
```

### Verify installation

```bash
policyfoundry --help
```

---

## Setup

PolicyFoundry uses an LLM to analyze traffic. You need one of these providers configured:

### Using Ollama (free, local, default)

1. Install [Ollama](https://ollama.com/)
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. That's it — PolicyFoundry uses Ollama by default.

### Using OpenAI

Set your API key as an environment variable:

```bash
export POLICYFOUNDRY_LLM__PROVIDER=openai
export POLICYFOUNDRY_LLM__MODEL=gpt-4o
export POLICYFOUNDRY_LLM__API_KEY=sk-your-key-here
```

### Using AWS Bedrock

```bash
export POLICYFOUNDRY_LLM__PROVIDER=bedrock
export POLICYFOUNDRY_LLM__MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

Requires AWS credentials configured via `aws configure` or environment variables.

### Using a config file

Create `.policyfoundry.yaml` in your working directory:

```yaml
llm:
  provider: ollama
  model: llama3.2
  temperature: 0.1
  max_tokens: 4096
  timeout: 120
```

---

## Usage

### Analyze an Excel traffic export

```bash
policyfoundry analyze --source excel --file traffic.xlsx
```

### Export a change request form

```bash
# Excel change request
policyfoundry analyze --source excel --file traffic.xlsx --export xlsx

# PDF change request
policyfoundry analyze --source excel --file traffic.xlsx --export pdf

# Both
policyfoundry analyze --source excel --file traffic.xlsx --export xlsx,pdf
```

### Use a custom change request template

```bash
policyfoundry analyze --source excel --file traffic.xlsx \
  --export xlsx --template my-template.xlsx
```

A [sample template](examples/templates/change_request_template.xlsx) is included in the repo.

### Analyze VPC Flow Logs

```bash
# From local files
policyfoundry analyze --source local --sg-ids sg-0123456789abcdef0

# From S3
policyfoundry analyze --source s3 --sg-ids sg-0123456789abcdef0
```

### Get JSON output

```bash
policyfoundry analyze --source excel --file traffic.xlsx --format json
```

### View current firewall rules

```bash
policyfoundry rules --sg-id sg-0123456789abcdef0
```

### Show resolved configuration

```bash
policyfoundry config
```

---

## CLI Reference

### `policyfoundry analyze`

| Option | Description | Default |
| --- | --- | --- |
| `--source` | Data source: `local`, `s3`, or `excel` | `local` |
| `--format` | Output format: `rich` or `json` | `rich` |
| `--file` | Path to input file (required for `excel`) | -- |
| `--export` | Export: `xlsx`, `pdf`, or `xlsx,pdf` | -- |
| `--template` | Custom Excel template for export | -- |
| `--sg-ids` | Security group IDs to analyze | -- |
| `--config` | Path to YAML config file | -- |
| `--debug` | Enable debug output | `false` |

### `policyfoundry rules`

| Option | Description | Default |
| --- | --- | --- |
| `--adapter` | Adapter name | `aws_sg` |
| `--sg-id` | Security group ID to query | -- |
| `--format` | Output format: `rich` or `json` | `rich` |

### `policyfoundry config`

| Option | Description | Default |
| --- | --- | --- |
| `--format` | Output format: `rich` or `json` | `rich` |

---

## Configuration

PolicyFoundry merges configuration from multiple sources (highest priority wins):

1. **CLI flags**
2. **Environment variables** (`POLICYFOUNDRY_` prefix, `__` for nesting)
3. **Local YAML** (`.policyfoundry.yaml` in current directory)
4. **Global YAML** (`~/.policyfoundry/config.yaml`)

### Full config example

```yaml
llm:
  provider: ollama          # ollama | openai | bedrock
  model: llama3.2
  temperature: 0.1
  max_tokens: 4096
  timeout: 120

sources:
  log_paths:
    - /var/log/vpc-flow/*.log
  # s3_bucket: my-vpc-logs-bucket
  # s3_prefix: vpc-flow-logs/

targets:
  security_group_ids:
    - sg-0123456789abcdef0

excel:
  # sheet_name: null
  # header_row: 1

output:
  format: rich
  data_dir: ~/.policyfoundry/data
```

### Environment variable examples

```bash
export POLICYFOUNDRY_LLM__PROVIDER=openai
export POLICYFOUNDRY_LLM__MODEL=gpt-4o
export POLICYFOUNDRY_LLM__API_KEY=sk-...
export POLICYFOUNDRY_SOURCES__S3_BUCKET=my-vpc-logs
export POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS=sg-abc123,sg-def456
```

---

## Docker

Run PolicyFoundry with an Ollama sidecar:

```bash
docker compose up -d
docker compose exec ollama ollama pull llama3.2
docker compose run policyfoundry analyze --source excel --file /path/to/traffic.xlsx
```

---

## Contributing

### Build from source

```bash
git clone https://github.com/vahagn-madatyan/PolicyFoundry.git
cd PolicyFoundry

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install with dev dependencies
uv sync --group dev

# Run from source
uv run policyfoundry --help
```

### Run tests

```bash
uv run pytest
uv run pytest --cov=policyfoundry
uv run pytest -k "test_analyze"
```

### Project structure

```text
src/policyfoundry/
├── main.py                  # CLI app (analyze, rules, config)
├── adapters/                # Firewall vendor adapters (AWS SG, etc.)
├── analysis/                # Traffic analysis & aggregation
├── config/                  # Configuration management
├── ingestion/               # Data ingestion (local, S3, Excel)
├── pipeline/                # AI analysis pipeline (LangGraph)
├── storage/                 # Parquet persistence + DuckDB queries
├── output/                  # Terminal & JSON formatters
└── export/                  # Change request export (xlsx/pdf)
```

### Architecture

PolicyFoundry runs a 5-stage AI pipeline built on [LangGraph](https://langchain-ai.github.io/langgraph/):

| Stage | Purpose |
| --- | --- |
| **Analyze** | Examine traffic patterns, identify flows, detect anomalies |
| **Assess** | Evaluate risk levels, flag high-risk flows |
| **Generate** | Produce concrete firewall rule proposals |
| **Validate** | Check proposals against adapter constraints (e.g., AWS SG limits) |
| **Decide** | Final accept/modify/reject decisions with justifications |

LLM calls use [Instructor](https://github.com/instructor-ai/instructor) + [LiteLLM](https://github.com/BerriAI/litellm) for structured output — every call returns a validated Pydantic model, not free-form text.

### Adapter system

Firewall adapters are loaded via Python entry points. The included AWS Security Group adapter validates against AWS-specific constraints (allow-only rules, 60-rule limit, CIDR validation). All adapters are wrapped in a read-only safety layer — PolicyFoundry never modifies live firewall rules.

### Infrastructure (optional)

The `infra/terraform/` directory contains Terraform for a test environment (VPC, security groups, S3 bucket, flow logs):

```bash
cd infra/terraform
terraform init
terraform plan -var="name_prefix=policyfoundry-dev"
terraform apply
```

---

## License

[Apache License 2.0](LICENSE)
