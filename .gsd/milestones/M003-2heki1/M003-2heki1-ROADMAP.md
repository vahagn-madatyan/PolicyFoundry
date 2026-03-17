# M003-2heki1: PR Review Bug Fixes

**Vision:** Fix all 14 critical + important issues identified in the M002 PR review — pipeline correctness, silent failure elimination, and type safety — so the codebase is solid before adding new capability in M004.

## Success Criteria

- Pipeline errors report the actual stage that failed (not `"starting"`)
- Token usage output shows per-stage breakdown (not all `"unknown"`)
- LLM generate prompt accurately describes `SubnetGroup.shared_patterns` field names
- Template export with no matching columns raises `ExportError` (not silent empty file)
- Output render failures surface visible warnings to the user
- `RuleDecision.action` is an enum that prevents invalid values
- `SubnetGroup.member_count` is consistent with `len(member_ips)`
- Full test suite passes (623+ tests, zero regressions)

## Key Risks / Unknowns

- Subnet dedup logic change (#13) could alter grouping behavior for edge cases — needs careful test analysis before changing
- `RuleDecision.action` enum (#10) touches serialization boundary with LLM structured output — must preserve compatibility with Instructor

## Proof Strategy

- Subnet dedup risk → retire in S03 by proving existing tests still pass plus new test covers the specific drop scenario
- Action enum risk → retire in S03 by proving LLM structured output tests work with the enum type

## Verification Classes

- Contract verification: pytest — targeted tests per issue + full suite regression
- Integration verification: none required
- Operational verification: none
- UAT / human verification: none — all issues are mechanically verifiable

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 14 PR review issues have fixes with targeted tests
- Full test suite passes (623+ tests, zero regressions)
- No new bare `except Exception` blocks introduced
- Each stage properly identifies itself in token usage and error reporting

## Requirement Coverage

- Covers: R401, R402, R403, R404, R405, R406, R407
- Partially covers: none
- Leaves for later: R501, R502, R503, R504 (M004)
- Orphan risks: none

## Slices

- [ ] **S01: Pipeline Correctness & Observability** `risk:high` `depends:[]`
  > After this: Pipeline errors report correct stage name; token usage shows per-stage breakdown; generate prompt references actual `dst_ip`/`src_ip` field names; rejected proposals and stage failures are logged. Verified by targeted tests.

- [ ] **S02: Silent Failure Elimination** `risk:medium` `depends:[]`
  > After this: Template with no matching columns raises `ExportError`; render failures surface console warnings; orphaned decisions are logged; adapter `ImportError` is logged. Verified by targeted tests.

- [ ] **S03: Type Safety & Data Integrity** `risk:low` `depends:[]`
  > After this: `RuleDecision.action` is a `DecisionAction` enum; `SubnetGroup.member_count` has a consistency validator; `dict()` construction is standard; subnet dedup produces correct results. Verified by targeted tests.

## Boundary Map

### S01 (independent)

Produces:
- Fixed `excel_runner.py` error handler that reads stage from evolved state, not initial state
- Fixed `excel_prompts/generate.py` prompt with correct `dst_ip`/`src_ip` field names
- All 8 LLM `complete()` calls (4 Excel stages + 4 VPC stages) now pass `stage=` parameter
- Stage-specific `PipelineError` wrapping in all pipeline stages with stage name in details
- Logged rejected proposals in validate stage
- Fixed `main.py` docstring (5 stages, not 6)

Consumes:
- nothing (independent slice)

### S02 (independent)

Produces:
- `ExportError` raised when template fill matches zero columns
- 8 bare `except Exception` blocks replaced with specific exception handling + visible console warnings
- Logged orphaned decisions in `export/models.py` when proposal_id not found
- Logged `ImportError` in `adapters/registry.py` instead of silent `pass`

Consumes:
- nothing (independent slice)

### S03 (independent)

Produces:
- `DecisionAction` StrEnum (`CREATE`, `SKIP`, `MODIFY`) on `RuleDecision.action`
- `model_validator` on `SubnetGroup` enforcing `member_count == len(member_ips)`
- Fixed `dict()` construction in `output/models.py`
- Fixed subnet dedup logic in `analysis/subnet.py`

Consumes:
- nothing (independent slice)
