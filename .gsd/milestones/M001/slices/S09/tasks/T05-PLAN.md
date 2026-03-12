---
estimated_steps: 4
estimated_files: 8
---

# T05: Reconstruct src AWS SG adapter and output module from bytecode

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the concrete AWS Security Group adapter (translator, boto3 client, adapter implementation) and the output module (TokenUsage model, PipelineResult model, Rich formatter, JSON formatter). These are the "ends" of the pipeline — the adapter fetches real firewall rules and the output module renders results. Both are directly consumed by CLI commands in T12.

The output module is especially important because `format_rich()` and `format_json()` are called by the CLI's analyze command, and `TokenUsage` is used for cost display (SAFE-02).

## Steps

1. **Reconstruct AWS SG adapter** (4 files):
   - `aws_sg/__init__.py` — re-exports `AwsSecurityGroupAdapter`
   - `aws_sg/translator.py` — `AwsSgTranslator` with static methods (D016) for converting between AWS SG rules and `UniversalRule` format
   - `aws_sg/client.py` — boto3 wrapper for `describe_security_groups` and related API calls
   - `aws_sg/adapter.py` — `AwsSecurityGroupAdapter(security_group_id, *, region=None)` implementing `FirewallAdapter` ABC. Constructor takes single SG ID (not list). Validation collects all errors (D017).

2. **Reconstruct output module** (4 files):
   - `output/__init__.py` — re-exports
   - `output/models.py` — `TokenUsage` dataclass with `add_call`, `to_dict`, `__add__` methods; `PipelineResult` Pydantic model with `from_state(state: PipelineState)` classmethod
   - `output/json_output.py` — `format_json(state: PipelineState) -> str` using `PipelineResult.from_state(state)` for serialization
   - `output/rich_output.py` — `format_rich(state: PipelineState, *, console=None) -> None` rendering summary, traffic analysis, assessment, proposals, decisions, and token usage tables. Uses `RISK_COLORS` dict mapping `RiskLevel` values to Rich color names. This is the largest output file (12.5KB pyc).

3. **Verify adapter + output imports** and key function signatures.

4. **Spot-check** `format_rich` has the `RISK_COLORS` dict and `format_json` uses `PipelineResult.from_state`.

## Must-Haves

- [ ] `AwsSecurityGroupAdapter.__init__` takes `security_group_id` (singular) + optional `region`
- [ ] `AwsSgTranslator` uses only static methods (D016)
- [ ] `TokenUsage` has `add_call`, `to_dict`, `__add__` methods
- [ ] `PipelineResult` has `from_state` classmethod accepting `PipelineState`
- [ ] `format_rich(state, *, console=None)` signature is correct (console is keyword-only)
- [ ] All 8 files import without error

## Verification

- `uv run python -c "from policyfoundry.adapters.aws_sg.adapter import AwsSecurityGroupAdapter; from policyfoundry.adapters.aws_sg.translator import AwsSgTranslator; print('OK')"`
- `uv run python -c "from policyfoundry.output.models import TokenUsage, PipelineResult; t = TokenUsage(); print(t.to_dict()); print('OK')"`
- `uv run python -c "from policyfoundry.output.rich_output import format_rich; from policyfoundry.output.json_output import format_json; print('OK')"`

## Observability Impact

- Signals added/changed: None (reconstruction only)
- How a future agent inspects this: Import `TokenUsage` and verify `add_call`/`to_dict` work; import `format_rich` and check for `RISK_COLORS`
- Failure state exposed: None

## Inputs

- `src/policyfoundry/adapters/aws_sg/__pycache__/*.cpython-313.pyc` (4 files, 366–6496 bytes)
- `src/policyfoundry/output/__pycache__/*.cpython-313.pyc` (4 files, 896–12506 bytes)
- `tools/inspect_pyc.py` from T01
- `src/policyfoundry/adapters/base.py` and `schema.py` from T04 (FirewallAdapter ABC, UniversalRule, etc.)
- Decisions D016, D017

## Expected Output

- `src/policyfoundry/adapters/aws_sg/__init__.py`, `translator.py`, `client.py`, `adapter.py`
- `src/policyfoundry/output/__init__.py`, `models.py`, `json_output.py`, `rich_output.py`
