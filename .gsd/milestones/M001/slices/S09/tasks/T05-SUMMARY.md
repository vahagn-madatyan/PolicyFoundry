---
id: T05
parent: S09
milestone: M001
provides:
  - policyfoundry.adapters.aws_sg package: AwsSecurityGroupAdapter, AwsSgTranslator (static methods, D016), AwsSgClient (boto3 wrapper)
  - policyfoundry.output package: TokenUsage dataclass, PipelineResult Pydantic model with from_state classmethod, format_rich (Rich renderer with RISK_COLORS), format_json (JSON serializer via PipelineResult)
  - policyfoundry.pipeline stub package: __init__.py, schema.py (TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision), state.py (PipelineState TypedDict)
key_files:
  - src/policyfoundry/adapters/aws_sg/__init__.py
  - src/policyfoundry/adapters/aws_sg/translator.py
  - src/policyfoundry/adapters/aws_sg/client.py
  - src/policyfoundry/adapters/aws_sg/adapter.py
  - src/policyfoundry/output/__init__.py
  - src/policyfoundry/output/models.py
  - src/policyfoundry/output/json_output.py
  - src/policyfoundry/output/rich_output.py
  - src/policyfoundry/pipeline/__init__.py
  - src/policyfoundry/pipeline/schema.py
  - src/policyfoundry/pipeline/state.py
key_decisions:
  - D016 confirmed: AwsSgTranslator uses only static methods (no instance state)
  - D017 confirmed: AwsSecurityGroupAdapter.validate collects all errors before returning (not fail-fast)
patterns_established:
  - AWS SG adapter: constructor takes security_group_id (singular, positional) + region (keyword-only, optional); AwsSgClient wraps boto3 EC2 describe_security_group_rules with Filters=[{Name:'group-id', Values:[sg_id]}]
  - Output module: TokenUsage.to_dict() uses "per_stage" key for call list; PipelineResult.from_state reconstructs typed models via model_validate; format_rich wraps each section in try/except with logger.warning on failure (graceful degradation)
  - _AUTH_ERROR_CODES = frozenset({"AuthFailure", "UnauthorizedAccess", "AccessDeniedException"}) for distinguishing AdapterAuthenticationError from generic AdapterError
  - _VALID_PROTOCOLS = frozenset({"tcp", "udp", "icmp", "-1"}) and _WIDE_OPEN_CIDRS = frozenset({"0.0.0.0/0", "::/0"}) for SG validation
observability_surfaces:
  - none (reconstruction only)
duration: 25m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T05: Reconstruct src AWS SG adapter and output module from bytecode

**Reconstructed 11 source files from CPython 3.13 bytecode: AWS SG adapter (translator, client, adapter) and output module (TokenUsage, PipelineResult, Rich/JSON formatters), plus pipeline schema/state stubs as required dependencies.**

## What Happened

Inspected 8 bytecode files using the T01 toolkit and `dis` disassembly to extract complete function signatures, constants, control flow, and class structures. Reconstructed all 8 planned files plus 3 additional pipeline dependency files (`pipeline/__init__.py`, `pipeline/schema.py`, `pipeline/state.py`) that the output module imports.

**AWS SG adapter (4 files):**
- `translator.py`: `AwsSgTranslator` with `from_sg_rule` staticmethod, plus module-level `_build_endpoint` and `_build_port_range` helpers. Uses `_PORT_PROTOCOLS = frozenset({"tcp", "udp"})` to determine when PortRange applies.
- `client.py`: `AwsSgClient` wrapping `boto3.client("ec2")` with `describe_rules` async method (via `asyncio.to_thread`). Distinguishes auth errors (`_AUTH_ERROR_CODES`) from general API errors.
- `adapter.py`: `AwsSecurityGroupAdapter(FirewallAdapter)` with 6 validation checks in `validate()`: deny rules, overly permissive sources, rule limit (60), invalid protocol, port range ordering, CIDR notation.

**Output module (4 files):**
- `models.py`: `TokenUsage` dataclass with `add_call`, `to_dict`, `__add__`; `PipelineResult` Pydantic model with `from_state` classmethod reconstructing typed models from raw PipelineState dicts.
- `json_output.py`: `format_json` wrapping `PipelineResult.from_state` → `model_dump_json(indent=2)` with `OutputError` on failure.
- `rich_output.py`: `format_rich` rendering 6 sections (summary panel, traffic analysis, security assessment, proposals, decisions table, token usage) with `RISK_COLORS` dict and per-section graceful error handling.

**Pipeline stubs (3 files):**
- `schema.py`: `TrafficAnalysis`, `SecurityAssessment`, `PolicyProposal`, `RuleDecision` Pydantic models reconstructed from bytecode constants.
- `state.py`: `PipelineState` TypedDict with `total=False` for partial state construction.
- `__init__.py`: Package init.

## Verification

All 3 task plan verification commands passed:
- `uv run python -c "from policyfoundry.adapters.aws_sg.adapter import AwsSecurityGroupAdapter; from policyfoundry.adapters.aws_sg.translator import AwsSgTranslator; print('OK')"` → OK
- `uv run python -c "from policyfoundry.output.models import TokenUsage, PipelineResult; t = TokenUsage(); print(t.to_dict()); print('OK')"` → OK
- `uv run python -c "from policyfoundry.output.rich_output import format_rich; from policyfoundry.output.json_output import format_json; print('OK')"` → OK

Must-haves verified programmatically:
- ✅ `AwsSecurityGroupAdapter.__init__` takes `security_group_id` (positional) + `region` (keyword-only, default None)
- ✅ `AwsSgTranslator.from_sg_rule` is a staticmethod (D016)
- ✅ `TokenUsage` has `add_call`, `to_dict`, `__add__` methods
- ✅ `PipelineResult.from_state` is a classmethod accepting `PipelineState`
- ✅ `format_rich(state, *, console=None)` — console is keyword-only
- ✅ All 8 planned + 3 pipeline stub files import without error
- ✅ `format_json` produces valid JSON from sample state
- ✅ `RISK_COLORS` = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "bold red"}

Slice-level checks:
- CLI tests (22 stubs) all fail as expected — waiting for T10/T12 for CLI module reconstruction
- No pre-existing adapter/output test dirs to run yet (tests not reconstructed until T10)

## Diagnostics

- Import AWS SG adapter: `uv run python -c "from policyfoundry.adapters.aws_sg import AwsSecurityGroupAdapter; print('OK')"`
- Test TokenUsage accumulation: `uv run python -c "from policyfoundry.output.models import TokenUsage; t = TokenUsage(); t.add_call(prompt_tokens=10, completion_tokens=5, total_tokens=15, cost=0.001, stage='test'); print(t.to_dict())"`
- Test format_json: `uv run python -c "from policyfoundry.output.json_output import format_json; print(format_json({'run_id': 'test', 'current_stage': 'done'}))"`
- Verify RISK_COLORS: `uv run python -c "from policyfoundry.output.rich_output import RISK_COLORS; print(RISK_COLORS)"`

## Deviations

- Created 3 additional pipeline stub files (`pipeline/__init__.py`, `pipeline/schema.py`, `pipeline/state.py`) not in the original task plan. These were required because the output module imports `PolicyProposal`, `RuleDecision`, `SecurityAssessment`, `TrafficAnalysis` from `policyfoundry.pipeline.schema` and `PipelineState` from `policyfoundry.pipeline.state`. T06 will fully reconstruct these with remaining pipeline files (llm, graph, runner, prompts); the stubs created here are byte-accurate reconstructions from the same bytecode.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/adapters/aws_sg/__init__.py` — Re-exports AwsSecurityGroupAdapter
- `src/policyfoundry/adapters/aws_sg/translator.py` — AwsSgTranslator with static from_sg_rule, _build_endpoint, _build_port_range
- `src/policyfoundry/adapters/aws_sg/client.py` — AwsSgClient boto3 wrapper with async describe_rules
- `src/policyfoundry/adapters/aws_sg/adapter.py` — AwsSecurityGroupAdapter implementing FirewallAdapter ABC with 6 validation checks
- `src/policyfoundry/output/__init__.py` — Re-exports format_json, format_rich, PipelineResult, TokenUsage, RISK_COLORS
- `src/policyfoundry/output/models.py` — TokenUsage dataclass and PipelineResult Pydantic model
- `src/policyfoundry/output/json_output.py` — format_json via PipelineResult.from_state
- `src/policyfoundry/output/rich_output.py` — format_rich with 6-section Rich rendering and RISK_COLORS
- `src/policyfoundry/pipeline/__init__.py` — Pipeline package init (stub for T06)
- `src/policyfoundry/pipeline/schema.py` — TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision models
- `src/policyfoundry/pipeline/state.py` — PipelineState TypedDict (total=False)
