---
id: S03
parent: M003-2heki1
milestone: M003-2heki1
provides:
  - DecisionAction StrEnum (CREATE/SKIP/UPDATE) replacing bare str on RuleDecision.action
  - SubnetGroup model_validator enforcing member_count == len(member_ips)
  - Standard dict(usage_raw) construction in output/models.py (2 occurrences)
  - Seen-set subnet dedup on (cidr, frozenset(member_ips)) replacing fragile break/else pattern
requires:
  - slice: none
    provides: none
affects:
  - none
key_files:
  - src/policyfoundry/pipeline/schema.py
  - src/policyfoundry/analysis/models.py
  - src/policyfoundry/analysis/subnet.py
  - src/policyfoundry/output/models.py
  - tests/test_models/test_pipeline_schema.py
  - tests/test_analysis/test_models.py
  - tests/test_analysis/test_subnet.py
key_decisions:
  - D066 — DecisionAction(StrEnum) for RuleDecision.action; StrEnum preserves Instructor JSON serialization and .upper() compat
  - D065 — Subnet dedup key is (cidr, frozenset(member_ips)) only; patterns excluded because _merge_same_subnet handles merging downstream
  - Fixed 3 test fixtures using invalid "APPROVE" action to "CREATE" — the enum caught exactly the bug it was designed to prevent
patterns_established:
  - StrEnum for constrained string fields on Pydantic LLM output models (P001)
  - Seen-set dedup with frozenset for unordered collection identity
observability_surfaces:
  - ValidationError with descriptive message when invalid action string used on RuleDecision
  - ValueError with member_count vs len(member_ips) values when SubnetGroup is inconsistent
drill_down_paths:
  - .gsd/milestones/M003-2heki1/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-2heki1/slices/S03/tasks/T02-SUMMARY.md
duration: ~22m
verification_result: passed
completed_at: 2026-03-16
---

# S03: Type Safety & Data Integrity

**Added `DecisionAction` StrEnum on `RuleDecision.action`, `SubnetGroup` consistency validator, standard `dict()` construction, and simplified subnet dedup — closing all 4 type safety issues from the PR review.**

## What Happened

Two tasks, four targeted fixes:

**T01 — Enum and validator (R406).** Added `DecisionAction(StrEnum)` with `CREATE`, `SKIP`, `UPDATE` members to `pipeline/schema.py`. Changed `RuleDecision.action` from `str` to `DecisionAction`. Uses `StrEnum` (not plain `Enum`) so values serialize as plain strings — critical for Instructor structured-output compatibility and downstream `.upper()` calls (K001). Added `@model_validator(mode="after")` on `SubnetGroup` in `analysis/models.py` enforcing `member_count == len(member_ips)` with a diagnostic error message including both values.

The enum immediately caught a real bug: three test fixtures in `tests/e2e/conftest.py`, `tests/test_cli/conftest.py`, and `tests/e2e/test_e2e_analyze.py` were using `action="APPROVE"` — a value that was never a valid domain action. The bare `str` type silently accepted it. Fixed all three to `"CREATE"` (L001).

**T02 — Dict construction and subnet dedup (R407).** Replaced `dict[str, Any](usage_raw)` with `dict(usage_raw)` in two locations in `output/models.py` — functionally identical but standard. Replaced the fragile `break`/`else: continue` dedup pattern in `analysis/subnet.py` with a clean seen-set on `(cidr, frozenset(member_ips))`. The old pattern keyed on individual shared_patterns and could incorrectly drop groups; the new pattern only identifies structurally identical groups, leaving pattern merging to `_merge_same_subnet` downstream (D065).

## Verification

- `pytest tests/test_models/test_pipeline_schema.py -v` — 20 passed (10 new enum/integration tests)
- `pytest tests/test_analysis/test_models.py -v` — 18 passed (2 new validator tests)
- `pytest tests/test_output/test_models.py -v` — 4 passed (existing from_state/serialization tests cover dict fix)
- `pytest tests/test_analysis/test_subnet.py -v` — 16 passed (2 new dedup correctness tests)
- `pytest --tb=short -q` — **679 passed**, zero failures, zero regressions (exceeds 623+ threshold)

## Requirements Advanced

- R406 — validated: DecisionAction enum + SubnetGroup validator both implemented with targeted tests
- R407 — validated: dict construction standardized, subnet dedup simplified with correctness tests

## Requirements Validated

- R406 — DecisionAction StrEnum rejects invalid action strings (10 tests); SubnetGroup validator rejects mismatched counts (2 tests); enum caught real "APPROVE" bug in 3 fixtures
- R407 — Standard dict() construction confirmed by existing tests (4 tests); seen-set dedup verified by 2 new tests proving same-members dedup and different-members retention

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Fixed 3 test fixtures** (`tests/e2e/conftest.py`, `tests/test_cli/conftest.py`, `tests/e2e/test_e2e_analyze.py`) using invalid `"APPROVE"` action → `"CREATE"`. Not in the original plan but required for the full suite to pass — and exactly the class of bug the enum was designed to prevent.

## Known Limitations

- `DecisionAction` has three members (`CREATE`, `SKIP`, `UPDATE`). If future pipeline stages need new action types, the enum must be extended. Adding a new member is additive and won't break existing code.
- `SubnetGroup` validator runs at construction time. Bulk construction of many SubnetGroup objects with programmatically-set `member_count` must pass the correct count — the validator does not auto-compute it.

## Follow-ups

- none

## Files Created/Modified

- `src/policyfoundry/pipeline/schema.py` — Added `DecisionAction(StrEnum)` class; changed `RuleDecision.action` type from `str` to `DecisionAction`
- `src/policyfoundry/analysis/models.py` — Added `model_validator` import; added consistency validator on `SubnetGroup`
- `src/policyfoundry/analysis/subnet.py` — Replaced break/else dedup with seen-set on `(cidr, frozenset(member_ips))`
- `src/policyfoundry/output/models.py` — Replaced `dict[str, Any](usage_raw)` with `dict(usage_raw)` on 2 lines
- `tests/test_models/test_pipeline_schema.py` — Added `TestDecisionAction` (5 tests) and `TestRuleDecisionEnum` (5 tests)
- `tests/test_analysis/test_models.py` — Added `test_member_count_consistency_valid` and `test_member_count_mismatch_rejected`
- `tests/test_analysis/test_subnet.py` — Added `TestDeduplication` class (2 tests)
- `tests/e2e/conftest.py` — Fixed `"APPROVE"` → `"CREATE"` on two `RuleDecision` fixtures
- `tests/test_cli/conftest.py` — Fixed `"APPROVE"` → `"CREATE"` on decision dict fixture
- `tests/e2e/test_e2e_analyze.py` — Updated assertion from `"APPROVE"` to `"CREATE"`

## Forward Intelligence

### What the next slice should know
- All 14 PR review issues from M002 are now fixed across S01–S03. M003-2heki1 is complete. The codebase is solid for M004 (secrets management).
- `DecisionAction` is the pattern for constrained string fields on LLM output models — use `StrEnum` (not `Enum`) for any future enum-like fields on Instructor response models (P001, K001).

### What's fragile
- `SubnetGroup` validator requires `member_count` to be set correctly at construction. Code that builds `SubnetGroup` objects manually (not from LLM output) must ensure consistency — the validator will reject mismatches immediately with a `ValueError`.

### Authoritative diagnostics
- `DecisionAction.__members__` — enumerate valid actions at runtime
- Invalid `RuleDecision.action` → Pydantic `ValidationError` with message "Input should be 'CREATE', 'SKIP' or 'UPDATE'"
- Inconsistent `SubnetGroup` → `ValidationError` wrapping "member_count (N) does not match len(member_ips) (M)"

### What assumptions changed
- Test fixtures assumed any string was valid for `RuleDecision.action` — the enum proved 3 fixtures were using an invalid value ("APPROVE") that production code never produces. All fixed.
