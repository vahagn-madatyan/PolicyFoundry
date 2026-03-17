# S03: Type Safety & Data Integrity — Research

**Date:** 2026-03-17

## Summary

This slice covers four targeted fixes — all well-understood patterns already established in the codebase. `RuleDecision.action` needs a `StrEnum` (same pattern as `DirectionLabel`, `RiskLevel`, `RuleAction`). `SubnetGroup.member_count` needs a Pydantic `model_validator`. `dict[str, Any](usage_raw)` is a non-standard constructor that should be `dict(usage_raw)`. The subnet dedup logic uses a confusing `break`/`else: continue` pattern that can be simplified since `_merge_same_subnet` already handles pattern merging downstream.

No new dependencies, no API changes, no architectural decisions needed.

## Recommendation

Implement all four fixes in a single pass with targeted tests for each. The `DecisionAction` enum is the highest-risk change (it touches the LLM structured output boundary via Instructor), so it should be built first with an explicit test proving Instructor compatibility. The other three are mechanical.

## Implementation Landscape

### Key Files

- `src/policyfoundry/pipeline/schema.py` — `RuleDecision.action` is `str` on line 46. Add `DecisionAction(StrEnum)` with members `CREATE`, `SKIP`, `UPDATE`. Change `action: str` → `action: DecisionAction`. The VPC prompt (`prompts/decide.py:13`) documents CREATE/UPDATE/SKIP; the Excel prompt (`excel_prompts/decide.py:25`) documents CREATE/SKIP. Both are valid.
- `src/policyfoundry/analysis/models.py` — `SubnetGroup` has `member_count: int = Field(ge=2)` with no consistency check against `member_ips`. Add a `@model_validator(mode="after")` enforcing `member_count == len(member_ips)`. Pattern exists in codebase: `DirectionResult`, `AggregatedFlow` use Pydantic Field constraints.
- `src/policyfoundry/output/models.py` — Lines 157 and 238 use `dict[str, Any](usage_raw)`. This is valid Python (calls the `dict` type with a type parameter, which is ignored at runtime and the constructor receives `usage_raw`), but it's confusing and non-standard. Replace with `dict(usage_raw)`. The type annotation on the left side already provides the typing.
- `src/policyfoundry/analysis/subnet.py` — Dedup block (lines 53–65) uses `break`/`else: continue` to skip groups where all patterns are seen. This is fragile. Since `_merge_same_subnet` already merges patterns for groups with same `(cidr, member_ips)`, the dedup can be simplified to a seen-set on `(cidr, frozenset(member_ips))` — append group only if the key is novel, skip if already seen.
- `src/policyfoundry/export/models.py` — `ChangeRequestEntry.action` is also `str` (line 31). This is a display model that receives `decision.action` at line 133. Once `RuleDecision.action` becomes `DecisionAction`, this field will receive enum values. The `decision.action.upper()` call at line 112 will still work (`StrEnum` members support `.upper()`). This field can stay `str` since it's a display model, or it can accept `DecisionAction` — either works.

### Downstream Consumers of `RuleDecision.action`

1. **Instructor/LLM structured output**: `RuleDecisionList` in `pipeline/stages/decide.py` and `pipeline/excel_stages/decide.py` wraps `list[RuleDecision]`. Instructor handles `StrEnum` natively — it constrains the LLM to valid enum values.
2. **Export models**: `export/models.py:112` checks `decision.action.upper() == "SKIP"`. `StrEnum` values compare equal to their string values, and `.upper()` works. No change needed.
3. **Test fixtures**: ~17 test files construct `RuleDecision(action="CREATE")` or `action="SKIP"`. `StrEnum` accepts string construction, so all existing tests pass without modification.

### Build Order

1. **DecisionAction enum + RuleDecision change** — highest risk (LLM serialization boundary). Build enum, update `action` field type, run existing schema tests to confirm backward compat. Add explicit test for enum validation (rejects invalid strings).
2. **SubnetGroup validator** — add `model_validator`, add test that invalid `member_count` raises `ValidationError`.
3. **dict() construction fix** — mechanical replacement on 2 lines, existing `from_state` tests cover this.
4. **Subnet dedup simplification** — simplify the loop, add a targeted test for the scenario where the old logic could misbehave (group with multi-pattern where first pattern is seen but group has novel member set).

### Verification Approach

```bash
# Targeted tests for new behavior
pytest tests/test_models/test_pipeline_schema.py -v
pytest tests/test_analysis/test_models.py -v
pytest tests/test_analysis/test_subnet.py -v
pytest tests/test_output/test_models.py -v

# Full regression
pytest --tb=short -q
```

Expected: 623+ tests pass, zero regressions. New tests add ~4-6 targeted cases.

## Constraints

- `DecisionAction` must use `StrEnum` (not plain `Enum`) to preserve string serialization compatibility with Instructor and existing `action.upper()` comparisons.
- `SubnetGroup.member_count` validator must not break `_collect_groups` which currently constructs `SubnetGroup(member_count=len(member_ips), ...)` — this is already consistent, so the validator will pass.
- The `dict()` fix must preserve the type annotation on the left side (`usage_dict: dict[str, Any]`).
