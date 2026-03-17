# S03: Type Safety & Data Integrity

**Goal:** `RuleDecision.action` is a `DecisionAction` StrEnum; `SubnetGroup.member_count` has a consistency validator; `dict()` construction is standard; subnet dedup produces correct results.
**Demo:** All four fixes verified by targeted tests plus full regression suite (623+ tests, zero regressions).

## Must-Haves

- `DecisionAction` StrEnum with members `CREATE`, `SKIP`, `UPDATE` replaces bare `str` on `RuleDecision.action`
- `SubnetGroup` has a `model_validator` enforcing `member_count == len(member_ips)`
- `dict[str, Any](usage_raw)` replaced with `dict(usage_raw)` in `output/models.py`
- Subnet dedup in `analysis/subnet.py` uses a seen-set instead of fragile `break`/`else: continue`

## Verification

- `pytest tests/test_models/test_pipeline_schema.py -v` — enum validation tests pass
- `pytest tests/test_analysis/test_models.py -v` — SubnetGroup validator tests pass
- `pytest tests/test_output/test_models.py -v` — dict construction covered by existing `from_state` tests
- `pytest tests/test_analysis/test_subnet.py -v` — dedup correctness test passes
- `pytest --tb=short -q` — full regression (623+ tests, zero failures)

## Tasks

- [ ] **T01: Add DecisionAction enum and SubnetGroup consistency validator** `est:30m`
  - Why: R406 — bare string on `RuleDecision.action` allows typos that silently change control flow; `SubnetGroup.member_count` can diverge from actual `member_ips` length
  - Files: `src/policyfoundry/pipeline/schema.py`, `src/policyfoundry/analysis/models.py`, `tests/test_models/test_pipeline_schema.py`, `tests/test_analysis/test_models.py`
  - Do: (1) Add `DecisionAction(StrEnum)` with `CREATE`, `SKIP`, `UPDATE` in `schema.py`. Change `action: str` to `action: DecisionAction`. (2) Add `@model_validator(mode="after")` on `SubnetGroup` enforcing `member_count == len(member_ips)`. (3) Add targeted tests: enum rejects invalid strings, enum accepts valid strings (including lowercase via StrEnum), validator rejects mismatched count, validator passes when consistent. Must use `StrEnum` (not plain `Enum`) to preserve string serialization compat with Instructor and `.upper()` comparisons downstream.
  - Verify: `pytest tests/test_models/test_pipeline_schema.py tests/test_analysis/test_models.py -v && pytest --tb=short -q`
  - Done when: Enum and validator tests pass, full suite 623+ tests pass with zero regressions

- [ ] **T02: Fix dict construction and simplify subnet dedup logic** `est:25m`
  - Why: R407 — `dict[str, Any](usage_raw)` is confusing non-standard construction; subnet dedup `break`/`else: continue` pattern can incorrectly drop groups before merge step
  - Files: `src/policyfoundry/output/models.py`, `src/policyfoundry/analysis/subnet.py`, `tests/test_analysis/test_subnet.py`
  - Do: (1) Replace `dict[str, Any](usage_raw)` with `dict(usage_raw)` on lines 157 and 238 of `output/models.py` — preserve the type annotation on the left side. (2) Replace the dedup block (lines 53–65) in `analysis/subnet.py` with a seen-set on `(cidr, frozenset(member_ips))` — append only if key is novel. (3) Add targeted test for dedup: construct input where old logic would drop a group with a novel member set but a shared pattern, verify the simplified logic keeps it.
  - Verify: `pytest tests/test_output/test_models.py tests/test_analysis/test_subnet.py -v && pytest --tb=short -q`
  - Done when: dict construction is standard, dedup test passes, full suite 623+ tests pass with zero regressions

## Files Likely Touched

- `src/policyfoundry/pipeline/schema.py`
- `src/policyfoundry/analysis/models.py`
- `src/policyfoundry/analysis/subnet.py`
- `src/policyfoundry/output/models.py`
- `tests/test_models/test_pipeline_schema.py`
- `tests/test_analysis/test_models.py`
- `tests/test_analysis/test_subnet.py`
