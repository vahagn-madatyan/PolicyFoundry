---
estimated_steps: 5
estimated_files: 4
---

# T04: Implement Rich and JSON formatters with risk-colored output

**Slice:** S08 — Output And Safety
**Milestone:** M001

## Description

Build the two output formatters that S09 CLI will invoke: `format_rich()` for terminal display and `format_json()` for machine-readable export. The Rich formatter renders a full report with summary panel, traffic analysis, security assessment, proposal details, risk-colored decision table, and token usage footer. The JSON formatter produces a complete structured document via PipelineResult serialization. Also adds `rich>=14.0` as a direct dependency.

## Steps

1. Add `rich>=14.0` as a direct dependency in `pyproject.toml`:
   - Add to `[project] dependencies` list
   - Run `uv sync` to verify resolution (rich is already installed via instructor, this just makes it explicit)

2. Create `src/policyfoundry/output/rich_output.py`:
   - Define `RISK_COLORS: dict[str, str]` mapping: `{"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "bold red"}`
   - Implement `format_rich(state: PipelineState, console: Console | None = None) -> None`:
     - Default console to `Console()` if None (auto-detect TTY)
     - Reconstruct typed models: `TrafficAnalysis.model_validate(state.get("analysis", {}))` etc., wrapped in try/except for graceful degradation
     - Render summary panel: run_id, started_at, sg_ids using `Panel()`
     - Render traffic analysis: Table with total_flows, unique_sources, unique_destinations, top_talkers
     - Render security assessment: overall_risk with color, risk_scores, rule_gaps, compliance_findings
     - Render proposals: iterate PolicyProposal list, show proposal_id, rule name, justification, risk_level colored, confidence
     - Render decisions table: Table with columns decision_id, proposal_id, action, risk_level (colored), reason, approval_required. Use `overflow="fold"` on reason column. Color risk_level cell text using RISK_COLORS mapping.
     - Render token usage footer: if `state.get("token_usage")` exists, show prompt_tokens, completion_tokens, total_tokens, cost. If no token_usage, skip footer silently.
     - Handle empty proposals/decisions gracefully (show "No proposals generated" message)
   - Keep all Rich imports at top level (no lazy imports needed)

3. Create `src/policyfoundry/output/json_output.py`:
   - Implement `format_json(state: PipelineState) -> str`:
     - Build `PipelineResult.from_state(state)`
     - Return `result.model_dump_json(indent=2)`
     - On construction error, raise `OutputError` with error_code="OUTPUT_SERIALIZE_FAILED"

4. Update `src/policyfoundry/output/__init__.py`:
   - Export `format_rich`, `format_json`, `PipelineResult`, `TokenUsage`, `RISK_COLORS`
   - These are the public API consumed by S09 CLI

5. Run full verification:
   - `pytest tests/test_output/ -v` — all Rich, JSON, and model tests pass
   - `pytest tests/test_safety/ -v` — safety tests still pass
   - `pytest tests/test_pipeline/test_llm.py -v` — LLM tests still pass
   - `pyright src/policyfoundry/output/` — strict clean
   - `ruff check src/ tests/` — no violations

## Must-Haves

- [ ] `rich>=14.0` in pyproject.toml direct dependencies
- [ ] `format_rich()` renders all 6 sections: summary, traffic analysis, security assessment, proposals, decisions, token usage
- [ ] Decision table rows use RISK_COLORS for risk_level text coloring
- [ ] `format_rich()` handles missing token_usage (no crash, no footer)
- [ ] `format_rich()` handles empty proposals/decisions (shows informational message)
- [ ] `format_json()` returns valid JSON string with all pipeline stage data
- [ ] `format_json()` includes token_usage when present
- [ ] RISK_COLORS dict maps LOW→green, MEDIUM→yellow, HIGH→red, CRITICAL→bold red
- [ ] All output tests pass
- [ ] pyright strict and ruff clean on all output files

## Verification

- `pytest tests/test_output/test_rich_output.py -v` — 7 tests pass
- `pytest tests/test_output/test_json_output.py -v` — 5 tests pass
- `pytest tests/test_output/ tests/test_safety/ tests/test_pipeline/test_llm.py -v` — full suite passes
- `pyright src/policyfoundry/output/` — 0 errors
- `ruff check src/policyfoundry/output/` — clean

## Observability Impact

- Signals added/changed: format_rich catches model reconstruction errors and logs them rather than crashing — degraded output is better than no output; format_json raises OutputError with error_code for structured error handling
- How a future agent inspects this: Capture Console output to StringIO in tests; parse JSON output with json.loads()
- Failure state exposed: OutputError with error_code="OUTPUT_SERIALIZE_FAILED" on JSON serialization failure; Rich formatter silently skips sections that fail to reconstruct

## Inputs

- `src/policyfoundry/output/models.py` (from T02) — PipelineResult.from_state(), TokenUsage
- `src/policyfoundry/pipeline/llm.py` (from T03) — LLMClient with get_usage() for token data flow
- `src/policyfoundry/pipeline/schema.py` (init branch) — TrafficAnalysis, SecurityAssessment, PolicyProposal, RuleDecision for model reconstruction
- `src/policyfoundry/adapters/schema.py` (init branch) — RiskLevel enum for color mapping
- `tests/test_output/` (from T01) — test files that will pass after this task
- `pyproject.toml` (init branch) — dependencies list to extend

## Expected Output

- `src/policyfoundry/output/rich_output.py` — format_rich() with 6 rendering sections and RISK_COLORS dict
- `src/policyfoundry/output/json_output.py` — format_json() with PipelineResult serialization
- `src/policyfoundry/output/__init__.py` — updated with all public exports
- `pyproject.toml` — rich>=14.0 added to dependencies
