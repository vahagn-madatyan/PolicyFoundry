---
id: T01
parent: S03
milestone: M003-2heki1
provides:
  - DecisionAction StrEnum replacing bare str on RuleDecision.action
  - SubnetGroup model_validator enforcing member_count == len(member_ips)
key_files:
  - src/policyfoundry/pipeline/schema.py
  - src/policyfoundry/analysis/models.py
  - tests/test_models/test_pipeline_schema.py
  - tests/test_analysis/test_models.py
key_decisions:
  - Fixed e2e/cli fixtures using "APPROVE" (invalid action) to "CREATE" — this was exactly the bug the enum prevents
patterns_established:
  - StrEnum for LLM structured output enums — preserves string serialization for Instructor and .upper() compat
observability_surfaces:
  - ValidationError with descriptive message when invalid action string is used on RuleDecision
  - ValueError with member_count vs len(member_ips) values when SubnetGroup is inconsistent
duration: 12m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add DecisionAction enum and SubnetGroup consistency validator

**Added `DecisionAction` StrEnum with CREATE/SKIP/UPDATE members on `RuleDecision.action` and a `model_validator` on `SubnetGroup` enforcing `member_count == len(member_ips)`.**

## What Happened

Two type safety changes:

1. **`DecisionAction(StrEnum)`** added to `pipeline/schema.py` with members `CREATE`, `SKIP`, `UPDATE`. `RuleDecision.action` changed from `str` to `DecisionAction`. Uses `StrEnum` (not plain `Enum`) so values serialize as plain strings — critical for Instructor structured-output compatibility and downstream `.upper()` calls.

2. **`SubnetGroup` consistency validator** added to `analysis/models.py` — a `@model_validator(mode="after")` that raises `ValueError` when `member_count != len(member_ips)`. Error message includes both values for easy diagnosis.

The enum change immediately caught a real bug: e2e and CLI test fixtures were using `action="APPROVE"` which was never a valid action. The production code only branches on `"SKIP"` vs non-SKIP, so these were silently working. Fixed all three fixture files to use `"CREATE"`.

## Verification

- `pytest tests/test_models/test_pipeline_schema.py -v` — 20 passed (10 new: 3 enum member tests, 1 StrEnum type test, 1 invalid enum test, 2 RuleDecision enum integration, 3 parametrized all-actions)
- `pytest tests/test_analysis/test_models.py -v` — 18 passed (2 new: consistency valid, mismatch rejected)
- `pytest --tb=short -q` — **677 passed**, zero failures, zero regressions

## Diagnostics

- `DecisionAction.__members__` — enumerate valid actions
- `list(DecisionAction)` — returns `["CREATE", "SKIP", "UPDATE"]`
- Invalid action on `RuleDecision` → `ValidationError` with message: "Input should be 'CREATE', 'SKIP' or 'UPDATE'"
- Inconsistent `SubnetGroup` → `ValidationError` wrapping: "member_count (N) does not match len(member_ips) (M)"

## Deviations

- **Fixed `"APPROVE"` → `"CREATE"` in 3 test fixture files** (`tests/e2e/conftest.py`, `tests/test_cli/conftest.py`, `tests/e2e/test_e2e_analyze.py`). This was a real bug that the enum caught — exactly the kind of silent inconsistency that a bare `str` type allowed. Not in the original plan but required for the full suite to pass.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/pipeline/schema.py` — Added `DecisionAction(StrEnum)` class; changed `RuleDecision.action` type from `str` to `DecisionAction`
- `src/policyfoundry/analysis/models.py` — Added `model_validator` import; added consistency validator on `SubnetGroup`
- `tests/test_models/test_pipeline_schema.py` — Added `TestDecisionAction` and `TestRuleDecisionEnum` test classes (10 new tests)
- `tests/test_analysis/test_models.py` — Added `test_member_count_consistency_valid` and `test_member_count_mismatch_rejected` (2 new tests)
- `tests/e2e/conftest.py` — Fixed `"APPROVE"` → `"CREATE"` on two `RuleDecision` fixtures
- `tests/test_cli/conftest.py` — Fixed `"APPROVE"` → `"CREATE"` on decision dict fixture
- `tests/e2e/test_e2e_analyze.py` — Updated assertion from `"APPROVE"` to `"CREATE"` in output check
