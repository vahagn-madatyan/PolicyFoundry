# Phase 1: Project Foundation - Research

**Researched:** 2026-03-07
**Domain:** Python project scaffolding, Pydantic v2 domain models, TypedDict, exception hierarchies, dev tooling (uv, Ruff, Pyright, pre-commit)
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield scaffolding phase: create a `src/policyfoundry/` package managed by `uv`, define all domain models in Pydantic v2, create a `PipelineState` TypedDict, and build a structured exception hierarchy. No business logic -- just the skeleton, types, and error handling that every subsequent phase builds on.

The technology choices are fully locked by user decisions: uv for package management, Ruff for linting/formatting, Pyright in strict mode for type checking, Pydantic v2 for domain models, and a `src/` layout. All are current, well-documented, and compatible with each other. The primary risk is getting the domain model schemas right so they don't need breaking changes later -- the CONTEXT.md locks the field lists and shapes, giving clear guidance.

**Primary recommendation:** Use `uv init --package policyfoundry` to bootstrap, configure all tooling in `pyproject.toml`, define all domain models in dedicated schema modules under their domain packages, and export exceptions from a single `policyfoundry.exceptions` module. Target Python >=3.12 with development on 3.13 (3.12 and 3.13 are both installed locally).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- src/ layout: `src/policyfoundry/` -- prevents accidental dev-copy imports, standard for publishable packages
- Pipeline module named `pipeline/` (not `agents/`) with sub-modules `stages/` and `prompts/` -- matches domain language (Analyze, Assess, Generate, Decide)
- Module structure: config/, ingestion/, storage/, pipeline/, adapters/, output/, utils/
- Separate `tests/` tree mirroring src/ structure: tests/test_config/, tests/test_ingestion/, etc.
- No audit/ module -- deferred to v2; add when audit requirements are active
- Old spec references to `firewall_ai` and Palo Alto modules are superseded -- name is `policyfoundry`, AWS-only for v1
- NormalizedFlowLog: 12-field schema (expanded from requirements' 10) -- timestamp, src_ip, dst_ip, src_port, dst_port, protocol, action, bytes_transferred, rule_id, app_name, flow_direction (INBOUND/OUTBOUND), packets_count
- LLM output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision): full schemas defined in Phase 1 based on architecture plan -- shape is locked, fields can evolve
- UniversalRule: vendor-neutral from day 1 -- direction, action (ALLOW/DENY), protocol, ports, CIDRs, description, priority. AWS adapter won't use DENY or priority but the model is ready for Palo Alto later
- PipelineState: TypedDict (not Pydantic) with run metadata -- run_id, started_at, current_stage, plus data references (flow_log_path, sg_ids, analysis, assessment, proposals, decisions). Stores flow log references as strings, not raw data
- Package manager: uv (already in success criteria)
- Linting: Ruff strict config (most rules enabled), formatting via ruff format -- all config in pyproject.toml
- Type checking: Pyright in strict mode via pyproject.toml
- Pre-commit: .pre-commit-config.yaml with ruff (lint + format) and pyright hooks
- Dev commands: Makefile wrapping uv run -- make test, make lint, make format, make check
- Per-domain exception hierarchy: PolicyFoundryError base, then ConfigError, IngestionError, StorageError, AdapterError, PipelineError, OutputError
- ConfigError gets immediate subclasses: ConfigFileNotFound, ConfigValidationError; other domains add subclasses in their phases
- Structured context: each exception carries optional error_code (string like 'INGEST_001') and details dict for machine-readable context
- All exceptions importable from single module: policyfoundry.exceptions
- User-facing: clean actionable messages by default; stack traces only with --debug flag or POLICYFOUNDRY_DEBUG=1 env var
- Package should be installable as CLI entry point: `policyfoundry` command via `[project.scripts]`

### Claude's Discretion
- Exact field types and validators for LLM output models (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision)
- pyproject.toml dependency versions and optional dependency groups
- conftest.py shared fixtures design
- Makefile target names and help formatting

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uv | >=0.10.7 | Package/project manager | Fastest Python package manager, replaces pip/venv/poetry; used locally (v0.10.7 installed) |
| uv-build | >=0.10.9 | Build backend | uv's native build backend for src layout packages |
| pydantic | >=2.12 | Domain model validation | Industry standard for Python data models; v2.12.5 is latest (supports Python 3.12-3.14) |
| ruff | >=0.15 | Linting + formatting | Replaces flake8+isort+black in one tool; v0.15.5 is latest |
| pyright | >=1.1.400 | Static type checking | Microsoft's type checker, strict mode catches type errors Pyright can't; v1.1.408 is latest |
| pre-commit | >=3.7 | Git hook management | Standard for enforcing code quality gates before commits |
| pytest | >=9.0 | Testing framework | De facto Python testing standard; v9.0.2 is latest |

### Supporting (Phase 1 only -- no runtime deps beyond pydantic)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-cov | >=5.0 | Coverage reporting | Running `make test` with coverage |
| typing-extensions | >=4.12 | Extended typing support | Only if needed for backported types; Python 3.12 has most features natively |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv-build backend | hatchling, setuptools | uv-build is native to uv ecosystem, zero config needed for src layout |
| Ruff | flake8 + isort + black | Ruff replaces all three, 100x faster, single config in pyproject.toml |
| Pyright | mypy | Pyright is faster, better strict mode, better IDE integration; both are valid |

**Installation (dev dependencies for Phase 1):**
```bash
uv add --dev ruff pyright pre-commit pytest pytest-cov
```

## Architecture Patterns

### Recommended Project Structure

This follows the locked decisions from CONTEXT.md exactly:

```
policyfoundry/
├── pyproject.toml              # All config: project, ruff, pyright, pytest
├── Makefile                    # Dev commands wrapping uv run
├── .pre-commit-config.yaml     # Ruff + Pyright hooks
├── .python-version             # Pin Python version (3.13)
├── src/
│   └── policyfoundry/
│       ├── __init__.py         # Version, package metadata
│       ├── py.typed            # PEP 561 marker for type information
│       ├── exceptions.py       # Single-module exception hierarchy
│       ├── config/
│       │   └── __init__.py     # Empty -- populated in Phase 2
│       ├── ingestion/
│       │   ├── __init__.py
│       │   └── schema.py       # NormalizedFlowLog, enums
│       ├── storage/
│       │   └── __init__.py     # Empty -- populated in Phase 4
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── state.py        # PipelineState TypedDict
│       │   ├── schema.py       # TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision
│       │   ├── stages/
│       │   │   └── __init__.py # Empty -- populated in Phase 7
│       │   └── prompts/
│       │       └── __init__.py # Empty -- populated in Phase 7
│       ├── adapters/
│       │   ├── __init__.py
│       │   └── schema.py       # UniversalRule, RuleAction, Direction, enums
│       ├── output/
│       │   └── __init__.py     # Empty -- populated in Phase 8
│       └── utils/
│           └── __init__.py     # Empty -- populated as needed
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_models/
│   │   ├── test_flow_log.py    # NormalizedFlowLog validation tests
│   │   ├── test_universal_rule.py  # UniversalRule validation tests
│   │   ├── test_pipeline_schema.py # LLM output model tests
│   │   └── test_pipeline_state.py  # PipelineState TypedDict tests
│   └── test_exceptions/
│       └── test_exceptions.py  # Exception hierarchy tests
└── .gitignore
```

### Pattern 1: Domain Model per Schema Module

**What:** Each domain area has its own `schema.py` containing Pydantic models and related enums.
**When to use:** Always -- keeps models co-located with their domain, prevents circular imports.
**Example:**
```python
# src/policyfoundry/ingestion/schema.py
from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from pydantic import BaseModel, Field

class ProtocolEnum(StrEnum):
    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"

class ActionEnum(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DROP = "DROP"

class FlowDirection(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"

class NormalizedFlowLog(BaseModel):
    """Unified schema for all traffic flow log sources. 12 fields."""
    timestamp: datetime
    src_ip: IPv4Address | IPv6Address
    dst_ip: IPv4Address | IPv6Address
    src_port: int = Field(ge=0, le=65535)
    dst_port: int = Field(ge=0, le=65535)
    protocol: ProtocolEnum
    action: ActionEnum
    bytes_transferred: int = Field(ge=0, default=0)
    rule_id: str | None = None
    app_name: str | None = None
    flow_direction: FlowDirection
    packets_count: int = Field(ge=0, default=0)
```

### Pattern 2: TypedDict for Pipeline State (Not Pydantic)

**What:** PipelineState uses `typing.TypedDict` for compatibility with LangGraph's state management, which expects dict-like objects, not Pydantic models.
**When to use:** Only for PipelineState -- LangGraph manages graph state as dicts.
**Example:**
```python
# src/policyfoundry/pipeline/state.py
from typing import TypedDict

class PipelineState(TypedDict, total=False):
    # Run metadata (always present)
    run_id: str
    started_at: str  # ISO format string
    current_stage: str

    # Data references (strings, NOT raw data)
    flow_log_path: str
    sg_ids: list[str]

    # Stage outputs (populated as pipeline progresses)
    analysis: dict  # Serialized TrafficAnalysis
    assessment: dict  # Serialized SecurityAssessment
    proposals: list[dict]  # Serialized PolicyProposal list
    decisions: list[dict]  # Serialized RuleDecision list
```

### Pattern 3: Structured Exception Hierarchy

**What:** Single-file exception hierarchy with base class carrying structured context.
**When to use:** All error handling across the project.
**Example:**
```python
# src/policyfoundry/exceptions.py
class PolicyFoundryError(Exception):
    """Base exception for all PolicyFoundry errors."""
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ConfigError(PolicyFoundryError):
    """Configuration-related errors."""

class ConfigFileNotFound(ConfigError):
    """Config file does not exist at expected path."""

class ConfigValidationError(ConfigError):
    """Config file exists but contains invalid values."""

class IngestionError(PolicyFoundryError):
    """Log ingestion and parsing errors."""

class StorageError(PolicyFoundryError):
    """Storage layer errors (Parquet, DuckDB, SQLite)."""

class AdapterError(PolicyFoundryError):
    """Firewall adapter errors."""

class PipelineError(PolicyFoundryError):
    """AI pipeline execution errors."""

class OutputError(PolicyFoundryError):
    """Output formatting and rendering errors."""
```

### Anti-Patterns to Avoid

- **Putting all models in one giant file:** Leads to circular import hell. Use per-domain schema.py files.
- **Using Pydantic for PipelineState:** LangGraph expects TypedDict-based state, not Pydantic models. The state dict flows through graph nodes and checkpointing.
- **Storing raw flow logs in PipelineState:** The CONTEXT.md explicitly prohibits this -- use string references (file paths) to prevent checkpoint bloat.
- **Creating `__init__.py` files that import everything:** Leads to import side effects. Keep `__init__.py` minimal except for `exceptions.py` exports and the top-level package.
- **Using `firewall_ai` or `firewall-ai` naming:** Old spec names are superseded. The project is `policyfoundry` everywhere.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IP address validation | Custom regex parsers | `ipaddress.IPv4Address` / `IPv6Address` + Pydantic | Standard library handles all edge cases, Pydantic integrates natively |
| Port range validation | Manual `if port < 0 or port > 65535` | `Field(ge=0, le=65535)` | Pydantic handles validation + error messages + serialization |
| Enum serialization | Custom string mapping | `StrEnum` (Python 3.11+) | Native, type-safe, works with Pydantic and serialization |
| Code formatting | Manual style guides | Ruff format | Deterministic, zero-config, 100x faster than Black |
| Import sorting | isort configuration | Ruff `I` rule set | Same tool, no extra dependency |
| Type checking config | Custom validation | Pyright strict mode | Catches type errors at development time, not runtime |

**Key insight:** Phase 1 has zero business logic -- it is entirely about getting the type system, validation, and tooling right. Every "don't hand-roll" item is about leveraging existing tools rather than writing custom infrastructure.

## Common Pitfalls

### Pitfall 1: Wrong TypedDict Import for Pydantic Interop
**What goes wrong:** Using `typing_extensions.TypedDict` when `typing.TypedDict` works fine on Python >=3.12.
**Why it happens:** Old documentation and LangGraph examples may reference `typing_extensions.TypedDict` for Python <3.12 compat.
**How to avoid:** Since we target Python >=3.12, use `from typing import TypedDict` directly. Only use `typing_extensions` if you need features not yet in the stdlib (e.g., `ReadOnly` from PEP 705 on Python <3.13).
**Warning signs:** Import warnings from Pydantic about TypedDict source.

### Pitfall 2: StrEnum Value Casing Mismatch
**What goes wrong:** Defining enum values as lowercase ("allow") but receiving uppercase ("ALLOW") from external data sources, causing validation failures.
**Why it happens:** Different systems use different casing conventions. AWS uses uppercase in some APIs, the old spec used lowercase.
**How to avoid:** Pick a consistent casing convention (UPPERCASE is recommended for enum values per Python convention) and document it. Use Pydantic's `model_config = ConfigDict(use_enum_values=True)` if you need string serialization.
**Warning signs:** Pydantic `ValidationError` on enum fields when ingesting external data.

### Pitfall 3: uv Build Backend Not Configured
**What goes wrong:** Running `uv run python -c "import policyfoundry"` fails because uv didn't install the package in the venv.
**Why it happens:** Missing `[build-system]` table in pyproject.toml. Without it, uv installs dependencies but not the project itself.
**How to avoid:** Always include:
```toml
[build-system]
requires = ["uv_build>=0.10.9,<0.11.0"]
build-backend = "uv_build"
```
**Warning signs:** `ModuleNotFoundError: No module named 'policyfoundry'` after `uv sync`.

### Pitfall 4: Pyright Virtual Environment Detection with pre-commit
**What goes wrong:** Pyright pre-commit hook can't find installed dependencies because pre-commit creates its own isolated venv.
**Why it happens:** pre-commit installs hooks in isolated environments. Pyright needs to see the project's actual venv to resolve imports.
**How to avoid:** Configure Pyright's `venvPath` and `venv` settings in pyproject.toml, OR use a local pre-commit hook that runs `uv run pyright` instead of the mirror repo.
**Warning signs:** Pyright reports `Import "pydantic" could not be resolved` only in pre-commit, not in IDE.

### Pitfall 5: Overly Strict Ruff Rules Breaking Prototyping
**What goes wrong:** Enabling every Ruff rule from day 1 creates hundreds of warnings on new code, making iteration painful.
**Why it happens:** Some rule sets (e.g., `ANN` for annotations, `D` for docstrings) require 100% compliance immediately.
**How to avoid:** Start with a strong but practical rule set. Enable `ANN` (annotations) and `D` (docstrings) later or per-file-ignore in tests. Use the recommended core set plus targeted extras.
**Warning signs:** Developers spending more time fixing lint than writing code.

### Pitfall 6: Circular Imports Between Schema Modules
**What goes wrong:** `pipeline/schema.py` imports `UniversalRule` from `adapters/schema.py`, and `adapters/schema.py` imports something from `pipeline/`.
**Why it happens:** Domain models reference each other (e.g., `PolicyProposal` contains a `UniversalRule`).
**How to avoid:** Keep the dependency direction one-way: `pipeline/schema.py` can import from `adapters/schema.py` and `ingestion/schema.py`, but not vice versa. If bidirectional references are needed, use `TYPE_CHECKING` imports.
**Warning signs:** `ImportError` at module load time.

## Code Examples

### pyproject.toml (Complete Configuration)

```toml
[project]
name = "policyfoundry"
version = "0.1.0"
description = "AI-powered firewall policy management"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "BSL-1.1" }
dependencies = [
    "pydantic>=2.12",
]

[project.scripts]
policyfoundry = "policyfoundry.__main__:main"

[build-system]
requires = ["uv_build>=0.10.9,<0.11.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "ruff>=0.15",
    "pyright>=1.1.400",
    "pre-commit>=3.7",
    "pytest>=9.0",
    "pytest-cov>=5.0",
]

# ── Ruff ──
[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort (import sorting)
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade (modern Python)
    "SIM",    # flake8-simplify
    "RET",    # flake8-return
    "PTH",    # flake8-use-pathlib
    "RUF",    # Ruff-specific rules
    "S",      # flake8-bandit (security)
    "T20",    # flake8-print (no print statements)
    "ICN",    # flake8-import-conventions
    "TC",     # flake8-type-checking
]
ignore = [
    "S101",   # assert used -- needed in tests
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "T20"]
"__init__.py" = ["F401"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

# ── Pyright ──
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "strict"
venvPath = "."
venv = ".venv"

# ── Pytest ──
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra -q"
```

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.5
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: pyright
        name: pyright
        entry: uv run pyright
        language: system
        types: [python]
        pass_filenames: false
```

Note: Pyright uses a `local` hook running `uv run pyright` to ensure it sees the project's actual virtual environment and dependencies, avoiding the isolated venv problem.

### Makefile

```makefile
.DEFAULT_GOAL := help

.PHONY: help install test lint format check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=policyfoundry --cov-report=term-missing

lint: ## Run linter
	uv run ruff check src/ tests/

format: ## Format code
	uv run ruff format src/ tests/

typecheck: ## Run type checker
	uv run pyright

check: lint typecheck ## Run all checks (lint + typecheck)

clean: ## Remove build artifacts
	rm -rf .pytest_cache .ruff_cache .venv build dist *.egg-info
```

### __init__.py (Package Root)

```python
# src/policyfoundry/__init__.py
"""PolicyFoundry: AI-powered firewall policy management."""

__version__ = "0.1.0"
```

### __main__.py (CLI Entry Point Stub)

```python
# src/policyfoundry/__main__.py
"""CLI entry point for policyfoundry."""

def main() -> None:
    """Entry point -- will be replaced by Typer app in Phase 9."""
    print(f"PolicyFoundry v{__import__('policyfoundry').__version__}")

if __name__ == "__main__":
    main()
```

### UniversalRule Model (Adapter Schema)

```python
# src/policyfoundry/adapters/schema.py
from enum import StrEnum
from pydantic import BaseModel, Field

class RuleAction(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"

class Direction(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"

class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PortRange(BaseModel):
    from_port: int = Field(ge=0, le=65535)
    to_port: int = Field(ge=0, le=65535)

class UniversalRule(BaseModel):
    """Vendor-neutral firewall rule representation."""
    id: str | None = None
    name: str
    description: str
    action: RuleAction
    direction: Direction
    protocol: str  # TCP, UDP, ICMP, ANY
    source_cidrs: list[str] = Field(default_factory=list)
    destination_cidrs: list[str] = Field(default_factory=list)
    port_range: PortRange | None = None
    priority: int | None = None  # For ordered rulesets (Palo Alto)
    risk_level: RiskLevel = RiskLevel.LOW
```

### LLM Output Models (Pipeline Schema)

```python
# src/policyfoundry/pipeline/schema.py
from pydantic import BaseModel, Field
from policyfoundry.adapters.schema import RiskLevel, UniversalRule

class TrafficAnalysis(BaseModel):
    """Stage 1 output: traffic pattern analysis."""
    summary: str
    total_flows: int = Field(ge=0)
    unique_sources: int = Field(ge=0)
    unique_destinations: int = Field(ge=0)
    top_talkers: list[dict]
    port_distribution: list[dict]
    anomalies: list[dict]
    bandwidth_outliers: list[dict]

class SecurityAssessment(BaseModel):
    """Stage 2 output: security posture assessment."""
    overall_risk: RiskLevel
    risk_scores: list[dict]
    rule_gaps: list[dict]
    compliance_findings: list[str] = Field(default_factory=list)

class PolicyProposal(BaseModel):
    """Stage 3 output: rule change proposal."""
    proposal_id: str
    rule: UniversalRule
    justification: str
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    impact_analysis: str

class RuleDecision(BaseModel):
    """Stage 4 output: final decision on a proposal."""
    decision_id: str
    proposal_id: str
    action: str  # CREATE, UPDATE, SKIP
    risk_level: RiskLevel
    reason: str
    approval_required: bool = True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip + venv + requirements.txt | uv (single tool) | 2024+ | 10-100x faster installs, lockfile, project management |
| flake8 + isort + black (3 tools) | Ruff (1 tool) | 2023+ | Single config, 100x faster, fewer dependencies |
| mypy for type checking | Pyright strict mode | 2023+ | Faster, better strict mode, better IDE integration |
| setuptools/setup.py | uv-build backend | 2025+ | Native to uv, zero-config for src layout |
| Pydantic v1 | Pydantic v2 | 2023 | 5-50x faster, Rust core, ConfigDict |
| typing_extensions.TypedDict | typing.TypedDict | Python 3.12 | Standard library, no extra dependency |

**Deprecated/outdated:**
- `firewall_ai` / `firewall-ai` naming: Superseded by `policyfoundry`
- `agents/` module naming: Superseded by `pipeline/` with `stages/` and `prompts/`
- `audit/` module: Deferred to v2
- Deep Agents library: Dropped in favor of LangGraph native
- Palo Alto adapter: AWS-only for v1

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (see Wave 0) |
| Quick run command | `uv run pytest -x -q` |
| Full suite command | `uv run pytest --cov=policyfoundry --cov-report=term-missing` |

### Phase Requirements -> Test Map

Phase 1 has no direct requirement IDs (foundational scaffolding). Tests map to success criteria:

| Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-------------------|----------|-----------|-------------------|-------------|
| SC-1 | `import policyfoundry` succeeds | smoke | `uv run python -c "import policyfoundry"` | -- Wave 0 |
| SC-2a | NormalizedFlowLog accepts valid data | unit | `uv run pytest tests/test_models/test_flow_log.py -x` | -- Wave 0 |
| SC-2b | NormalizedFlowLog rejects invalid data | unit | `uv run pytest tests/test_models/test_flow_log.py -x` | -- Wave 0 |
| SC-2c | UniversalRule accepts valid data | unit | `uv run pytest tests/test_models/test_universal_rule.py -x` | -- Wave 0 |
| SC-2d | UniversalRule rejects invalid data | unit | `uv run pytest tests/test_models/test_universal_rule.py -x` | -- Wave 0 |
| SC-2e | TrafficAnalysis instantiation | unit | `uv run pytest tests/test_models/test_pipeline_schema.py -x` | -- Wave 0 |
| SC-2f | SecurityAssessment instantiation | unit | `uv run pytest tests/test_models/test_pipeline_schema.py -x` | -- Wave 0 |
| SC-2g | PolicyProposal instantiation | unit | `uv run pytest tests/test_models/test_pipeline_schema.py -x` | -- Wave 0 |
| SC-2h | RuleDecision instantiation | unit | `uv run pytest tests/test_models/test_pipeline_schema.py -x` | -- Wave 0 |
| SC-3a | PipelineState stores flow_log_path as string | unit | `uv run pytest tests/test_models/test_pipeline_state.py -x` | -- Wave 0 |
| SC-3b | PipelineState does not store raw log data | unit | `uv run pytest tests/test_models/test_pipeline_state.py -x` | -- Wave 0 |
| SC-4a | All exceptions importable from policyfoundry.exceptions | unit | `uv run pytest tests/test_exceptions/test_exceptions.py -x` | -- Wave 0 |
| SC-4b | Exception hierarchy correct (subclass relationships) | unit | `uv run pytest tests/test_exceptions/test_exceptions.py -x` | -- Wave 0 |
| SC-4c | Exceptions carry error_code and details | unit | `uv run pytest tests/test_exceptions/test_exceptions.py -x` | -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest -x -q`
- **Per wave merge:** `uv run pytest --cov=policyfoundry --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- shared fixtures (model factories for valid/invalid test data)
- [ ] `tests/test_models/test_flow_log.py` -- covers SC-2a, SC-2b
- [ ] `tests/test_models/test_universal_rule.py` -- covers SC-2c, SC-2d
- [ ] `tests/test_models/test_pipeline_schema.py` -- covers SC-2e through SC-2h
- [ ] `tests/test_models/test_pipeline_state.py` -- covers SC-3a, SC-3b
- [ ] `tests/test_exceptions/test_exceptions.py` -- covers SC-4a through SC-4c
- [ ] Framework config in pyproject.toml `[tool.pytest.ini_options]`

## Open Questions

1. **Python version pin: 3.12 or 3.13?**
   - What we know: `requires-python = ">=3.12"` is set in PROJECT.md. Both 3.12.12 and 3.13.12 are available locally. Pydantic v2.12 supports both.
   - What's unclear: Whether to pin `.python-version` to 3.12 or 3.13 for development.
   - Recommendation: Use `>=3.12` in pyproject.toml and pin `.python-version` to `3.13` for development. 3.13 is stable and offers better TypedDict support. Avoid 3.14 (still maturing, some libraries have initial support only).

2. **LLM output model field types (Claude's discretion)**
   - What we know: Shape is locked per CONTEXT.md. Fields can evolve.
   - What's unclear: Exact types for nested structures in TrafficAnalysis, SecurityAssessment (e.g., `list[dict]` vs typed models for anomalies, risk scores).
   - Recommendation: Use `list[dict]` for now since the LLM output structure will be refined in Phase 6/7 when we have actual LLM responses. Typed sub-models can be added later without breaking the outer model shape.

3. **Dependency groups vs optional-dependencies**
   - What we know: uv supports both `[dependency-groups]` (PEP 735) and `[project.optional-dependencies]`.
   - What's unclear: Whether to use the newer `[dependency-groups]` or the traditional `[project.optional-dependencies]`.
   - Recommendation: Use `[dependency-groups]` for dev dependencies (PEP 735, supported by uv). It's the modern approach and avoids polluting `[project.optional-dependencies]` which is meant for user-facing extras.

## Sources

### Primary (HIGH confidence)
- [uv docs - Creating projects](https://docs.astral.sh/uv/concepts/projects/init/) - src layout, build backend, project init
- [uv docs - Configuration](https://docs.astral.sh/uv/concepts/configuration-files/) - pyproject.toml settings
- [Ruff docs - Configuration](https://docs.astral.sh/ruff/configuration/) - lint rules, format settings
- [Ruff pre-commit](https://github.com/astral-sh/ruff-pre-commit) - hook configuration
- [Pyright configuration](https://github.com/microsoft/pyright/blob/main/docs/configuration.md) - strict mode, pyproject.toml settings
- [Pydantic docs - Network types](https://docs.pydantic.dev/latest/api/networks/) - IPv4/IPv6 validation
- [Pydantic docs - Models](https://docs.pydantic.dev/latest/concepts/models/) - field constraints, validators, ConfigDict
- [PyPI - pydantic 2.12.5](https://pypi.org/project/pydantic/) - latest version verified
- [PyPI - ruff 0.15.5](https://pypi.org/project/ruff/) - latest version verified
- Local system: uv 0.10.7, Python 3.14.3 (system), 3.13.12 and 3.12.12 (via uv)

### Secondary (MEDIUM confidence)
- [Python Developer Tooling Handbook](https://pydevtools.com/handbook/how-to/how-to-configure-recommended-ruff-defaults/) - Ruff rule recommendations
- [Pyright pre-commit](https://github.com/RobertCraigie/pyright-python) - pre-commit hook setup and venv detection issue
- [PEP 655 - NotRequired](https://peps.python.org/pep-0655/) - TypedDict optional fields

### Tertiary (LOW confidence)
- None -- all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools verified with official docs and local installation
- Architecture: HIGH -- structure directly constrained by CONTEXT.md decisions
- Pitfalls: HIGH -- based on official documentation and known issues (Pyright venv detection is documented)
- Domain models: MEDIUM -- field types for LLM output models are discretionary and will evolve

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (30 days -- all technologies are stable releases)