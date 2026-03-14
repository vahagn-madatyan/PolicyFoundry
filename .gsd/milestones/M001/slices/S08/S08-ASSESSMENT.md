# S08 Post-Slice Roadmap Assessment

**Verdict: Roadmap is sound — minor boundary map correction applied.**

## What S08 Delivered

S08 delivered ~80% of its planned scope across 4 tasks:

- **Token tracking** (T02, T03): `LLMClient.create_with_completion()` with `get_usage()`/`reset_usage()`, `TokenUsage` dataclass, deep-copy safety, None-safe cost extraction. 25 LLM tests passing.
- **Output formatters** (T04): `format_rich()` with 6-section report and RISK_COLORS, `format_json()` with PipelineResult serialization. 14 output tests passing.
- **PipelineResult model** (T02): Wraps PipelineState with typed stage outputs via `from_state()`.
- **Test scaffolding** (T01): Safety tests for ReadOnlyAdapter/SafetyError fully written (6 tests).

## What S08 Did NOT Deliver

Two items listed in the S08→S09 boundary were not implemented:

1. **`adapters/safety.py` (ReadOnlyAdapter)** — Tests exist in `tests/test_safety/test_readonly_adapter.py` but the module doesn't exist. T04 explicitly notes "T05 (ReadOnlyAdapter) not yet implemented" — there was no T05.
2. **`SafetyError` in `exceptions.py`** — The exception class is imported by safety tests but not defined.

These are small implementations (~50 lines total) with complete test coverage already scaffolded.

## Risk Retirement

- **"Token tracking reliability"** → ✅ RETIRED. `create_with_completion()` tested with mock Instructor client, usage dict propagation verified, cost extraction hardened with None-safety. This risk is closed.
- **"CLI integration surfaces hidden coupling"** → Still open, owned by S09 as planned.
- **"Terraform + Docker require external service dependencies"** → Still open, owned by S10 as planned.

## Roadmap Changes Applied

1. **S09 description** — Added explicit mention that ReadOnlyAdapter and SafetyError are carry-over from S08 (tests exist, implementation needed).
2. **Boundary map S08→S09** — Split into "Produces (delivered)" and "Carry-over to S09" sections so the next slice planner knows what exists vs. what must be built.
3. **Boundary map S09→S10** — Split S09 consumes into "from S08 (delivered)" and "from S09 own build (S08 carry-over)".
4. **Requirement coverage** — SAFE-01 updated from "S08 primary" to "S08 partial, S09 completes".

## Success Criteria Coverage

All success criteria have remaining owning slices:

- User can run `policyfoundry analyze` with Rich report → **S09**
- User can run `policyfoundry analyze --format json` → **S09**
- Tool never modifies firewall rules (suggest-only) → **S09** (implements ReadOnlyAdapter carry-over)
- Each pipeline run displays token usage and cost → **S09** (wires S08's TokenUsage/formatters)
- Terraform bootstraps AWS test environment → **S10**
- Docker container with Ollama sidecar → **S10**
- CLI commands show `--help` and actionable errors → **S09**

No blocking gaps.

## Requirement Coverage

- OUT-01, OUT-02 → S09 ✅
- SAFE-01 → S09 (carry-over from S08) ✅
- SAFE-02 → S08 delivered, S09 wires ✅
- INFRA-01, INFRA-02 → S10 ✅

Coverage remains sound. No requirements are orphaned.

## Remaining Slice Assessment

- **S09 (CLI Integration)** — Scope slightly larger than planned due to ReadOnlyAdapter/SafetyError carry-over, but manageable: tests already exist, implementation is ~50 lines. Risk level unchanged at medium.
- **S10 (Infrastructure And Packaging)** — No changes needed. Still depends on S09 CLI entrypoint.

No reordering, merging, splitting, or removal needed.
