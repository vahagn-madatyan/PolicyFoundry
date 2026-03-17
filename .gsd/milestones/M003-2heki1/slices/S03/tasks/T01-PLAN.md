---
estimated_steps: 5
estimated_files: 4
---

# T01: Add DecisionAction enum and SubnetGroup consistency validator

**Slice:** S03 — Type Safety & Data Integrity
**Milestone:** M003-2heki1

## Description

Two type safety fixes. First, add a `DecisionAction` StrEnum to replace the bare `str` type on `RuleDecision.action`. This is the highest-risk change in S03 because `RuleDecision` is used as Instructor structured output — the enum must be `StrEnum` so it serializes as a plain string and preserves compatibility with downstream `.upper()` comparisons. Second, add a Pydantic `model_validator` on `SubnetGroup` enforcing `member_count == len(member_ips)`.

## Steps

1. In `src/policyfoundry/pipeline/schema.py`, add `from enum import StrEnum` and define `DecisionAction(StrEnum)` with members `CREATE = "CREATE"`, `SKIP = "SKIP"`, `UPDATE = "UPDATE"`. Change `RuleDecision.action: str` to `action: DecisionAction`.
2. In `src/policyfoundry/analysis/models.py`, add `from pydantic import model_validator` (if not already imported). Add a `@model_validator(mode="after")` method on `SubnetGroup` that raises `ValueError` if `self.member_count != len(self.member_ips)`.
3. In `tests/test_models/test_pipeline_schema.py`, add tests: (a) `DecisionAction("CREATE")` succeeds, (b) `DecisionAction("SKIP")` succeeds, (c) `DecisionAction("UPDATE")` succeeds, (d) constructing `RuleDecision(action="INVALID", ...)` raises `ValidationError`, (e) `RuleDecision(action="CREATE", ...)` succeeds and `action` is a `DecisionAction` instance.
4. In `tests/test_analysis/test_models.py`, add tests: (a) `SubnetGroup(member_count=3, member_ips=[...3 ips...], ...)` succeeds, (b) `SubnetGroup(member_count=5, member_ips=[...3 ips...], ...)` raises `ValidationError`.
5. Run targeted tests then full regression: `pytest tests/test_models/test_pipeline_schema.py tests/test_analysis/test_models.py -v && pytest --tb=short -q`

## Must-Haves

- [ ] `DecisionAction` is a `StrEnum` (not plain `Enum`) — critical for Instructor compatibility and `.upper()` calls
- [ ] `RuleDecision.action` type is `DecisionAction`, not `str`
- [ ] `SubnetGroup` has `model_validator` enforcing `member_count == len(member_ips)`
- [ ] Targeted tests cover both valid and invalid cases for each change
- [ ] Full test suite passes (623+ tests, zero regressions)

## Verification

- `pytest tests/test_models/test_pipeline_schema.py -v` — enum tests pass
- `pytest tests/test_analysis/test_models.py -v` — validator tests pass
- `pytest --tb=short -q` — 623+ tests, zero failures

## Observability Impact

- **New failure signal:** `RuleDecision(action="BOGUS", ...)` now raises `ValidationError` instead of silently accepting. Any pipeline code constructing `RuleDecision` with a typo'd action will fail fast with a clear enum-validation message.
- **New failure signal:** `SubnetGroup` with `member_count != len(member_ips)` raises `ValueError` via `model_validator`. Error message includes both values for diagnosis.
- **Inspection surface:** `DecisionAction.__members__` enumerates valid actions. `list(DecisionAction)` returns `["CREATE", "SKIP", "UPDATE"]`.
- **No log/metric changes** — these are Pydantic model constraints, not runtime instrumentation.

## Inputs

- `src/policyfoundry/pipeline/schema.py` — `RuleDecision` model with `action: str` on line 46
- `src/policyfoundry/analysis/models.py` — `SubnetGroup` model with `member_count: int = Field(ge=2)` and no consistency check
- Existing test files to understand current test patterns and fixture shapes

## Expected Output

- `src/policyfoundry/pipeline/schema.py` — contains `DecisionAction(StrEnum)` class and `RuleDecision.action: DecisionAction`
- `src/policyfoundry/analysis/models.py` — `SubnetGroup` has `model_validator` checking `member_count == len(member_ips)`
- `tests/test_models/test_pipeline_schema.py` — new tests for enum validation (valid + invalid)
- `tests/test_analysis/test_models.py` — new tests for SubnetGroup consistency validator (valid + invalid)
