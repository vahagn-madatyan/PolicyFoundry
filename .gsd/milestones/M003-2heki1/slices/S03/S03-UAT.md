# S03: Type Safety & Data Integrity — UAT

**Milestone:** M003-2heki1
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All four fixes are data-model and pure-function changes — correctness is fully provable by unit tests. No runtime services, no UI, no user-facing interaction surfaces.

## Preconditions

- Python 3.13 venv active (`.venv/bin/python`)
- All project dependencies installed (`pip install -e ".[dev]"`)
- Working directory is project root

## Smoke Test

```bash
.venv/bin/python -m pytest tests/test_models/test_pipeline_schema.py tests/test_analysis/test_models.py tests/test_output/test_models.py tests/test_analysis/test_subnet.py -v
```
All 56 targeted tests pass.

## Test Cases

### 1. DecisionAction enum accepts valid members

1. Run: `.venv/bin/python -m pytest tests/test_models/test_pipeline_schema.py::TestDecisionAction::test_valid_members -v`
2. **Expected:** 3 parametrized tests pass — CREATE, SKIP, UPDATE each accepted as valid enum values.

### 2. DecisionAction enum rejects invalid strings

1. Run: `.venv/bin/python -m pytest tests/test_models/test_pipeline_schema.py::TestDecisionAction::test_invalid_action_rejected -v`
2. **Expected:** `ValidationError` raised when constructing DecisionAction with `"APPROVE"` or any non-member string.

### 3. DecisionAction is StrEnum (string serialization)

1. Run: `.venv/bin/python -m pytest tests/test_models/test_pipeline_schema.py::TestDecisionAction::test_is_strenum -v`
2. **Expected:** `DecisionAction.CREATE` is an instance of both `str` and `StrEnum`, so `model_dump()` produces plain strings, not enum wrappers.

### 4. RuleDecision uses DecisionAction for action field

1. Run: `.venv/bin/python -m pytest tests/test_models/test_pipeline_schema.py::TestRuleDecisionEnum -v`
2. **Expected:** 5 tests pass — valid actions accepted as RuleDecision.action; invalid actions raise ValidationError; all three enum members work in full RuleDecision construction.

### 5. SubnetGroup consistency validator — valid case

1. Run: `.venv/bin/python -m pytest tests/test_analysis/test_models.py::TestSubnetGroup::test_member_count_consistency_valid -v`
2. **Expected:** SubnetGroup with `member_count=2` and 2 entries in `member_ips` constructs without error.

### 6. SubnetGroup consistency validator — mismatch rejected

1. Run: `.venv/bin/python -m pytest tests/test_analysis/test_models.py::TestSubnetGroup::test_member_count_mismatch_rejected -v`
2. **Expected:** SubnetGroup with `member_count=5` but only 2 entries in `member_ips` raises `ValidationError` with message containing both values (5 and 2).

### 7. Standard dict construction in output models

1. Run: `.venv/bin/python -m pytest tests/test_output/test_models.py -v`
2. **Expected:** 4 tests pass — `from_state` and serialization tests confirm token usage dicts are constructed correctly using standard `dict()`.

### 8. Subnet dedup — same CIDR, same members, different patterns are deduped

1. Run: `.venv/bin/python -m pytest tests/test_analysis/test_subnet.py::TestDeduplication::test_same_cidr_same_members_different_patterns_deduped -v`
2. **Expected:** Two groups with identical (cidr, member_ips) but different shared_patterns collapse to one group, with both patterns merged via `_merge_same_subnet`.

### 9. Subnet dedup — same CIDR, different members are kept

1. Run: `.venv/bin/python -m pytest tests/test_analysis/test_subnet.py::TestDeduplication::test_same_cidr_different_members_kept -v`
2. **Expected:** Two groups with same CIDR but different member_ips are both retained — they represent distinct subnets.

### 10. Full regression suite

1. Run: `.venv/bin/python -m pytest --tb=short -q`
2. **Expected:** 679 passed, zero failures. No regressions from any of the four changes.

## Edge Cases

### Invalid action string in LLM structured output

1. Simulate Instructor returning `action="BLOCK"` on a RuleDecision.
2. **Expected:** Pydantic `ValidationError` with message "Input should be 'CREATE', 'SKIP' or 'UPDATE'" — Instructor's retry mechanism will re-prompt the LLM.

### SubnetGroup constructed with member_count=0 and empty member_ips

1. Construct `SubnetGroup(cidr="10.0.0.0/24", member_count=0, member_ips=[], shared_patterns=[])`.
2. **Expected:** Validation passes — 0 == len([]) is consistent. (Minimum count validation is separate from consistency.)

### Subnet dedup with single group (no duplicates possible)

1. Pass a single group through `group_to_subnets`.
2. **Expected:** Group is returned unchanged — seen-set never triggers dedup.

## Failure Signals

- Any `ValidationError` from `DecisionAction` or `SubnetGroup` in production logs → check if LLM output or data pipeline is producing invalid values
- Subnet groups disappearing from analysis output → inspect the `seen` set in the dedup loop of `group_to_subnets`
- Test count below 679 → a test was deleted or a fixture change broke an unrelated test

## Requirements Proved By This UAT

- R406 — DecisionAction enum rejects invalid action strings; SubnetGroup validator catches member_count divergence
- R407 — Standard dict() construction works identically; seen-set dedup preserves distinct groups while collapsing duplicates

## Not Proven By This UAT

- Runtime behavior with real LLM returning unexpected action strings (tested only via mock/unit)
- Performance impact of model_validator on bulk SubnetGroup construction (negligible for current data sizes)

## Notes for Tester

- The enum caught a real bug during implementation: 3 fixtures were using `"APPROVE"` as an action value. If you see any test using `"APPROVE"` in a RuleDecision, that's a regression.
- `DecisionAction` members are uppercase (`CREATE`, `SKIP`, `UPDATE`). Lowercase inputs are auto-coerced by StrEnum, but all production code uses uppercase.
