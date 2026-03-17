---
id: T02
parent: S03
milestone: M003-2heki1
provides:
  - Standard dict() construction in output/models.py (both occurrences)
  - Seen-set subnet dedup on (cidr, frozenset(member_ips)) replacing fragile break/else pattern
key_files:
  - src/policyfoundry/output/models.py
  - src/policyfoundry/analysis/subnet.py
  - tests/test_analysis/test_subnet.py
key_decisions:
  - Dedup key is (cidr, frozenset(member_ips)) only — patterns handled by _merge_same_subnet downstream
patterns_established:
  - Seen-set dedup with frozenset for unordered collection identity
observability_surfaces:
  - none — pure data-transform logic; correctness verified by unit tests
duration: ~10m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Fix dict construction and simplify subnet dedup logic

**Replaced non-standard `dict[str, Any](usage_raw)` with `dict(usage_raw)` in two places and simplified subnet dedup from fragile break/else to a clean seen-set on `(cidr, frozenset(member_ips))`.**

## What Happened

Two targeted data integrity fixes:

1. **dict construction** — Both occurrences of `dict[str, Any](usage_raw)` in `output/models.py` (lines 157 and 238) replaced with `dict(usage_raw)`. The type annotation remains on the variable (`usage_dict: dict[str, Any] = dict(usage_raw)`). Functionally identical — the old syntax used a parameterized generic as a constructor, which works in Python but is non-standard and confusing.

2. **subnet dedup** — The old dedup in `analysis/subnet.py` iterated each group's `shared_patterns`, built a key `(cidr, frozenset(member_ips), str(sorted(pattern.items())))`, and used a `break`/`else: continue` to decide whether to keep the group. This was fragile: if a group's first pattern matched a seen key but the group had different overall patterns, it would be incorrectly kept or dropped. The new logic uses a simple seen-set on `(cidr, frozenset(member_ips))` — if the key is novel, keep the group; otherwise skip. Pattern merging is already handled by `_merge_same_subnet` downstream.

## Verification

- `pytest tests/test_output/test_models.py -v` — 4 passed (existing from_state and serialization tests confirm dict construction)
- `pytest tests/test_analysis/test_subnet.py -v` — 16 passed including 2 new dedup tests:
  - `test_same_cidr_same_members_different_patterns_deduped` — verifies groups with identical (cidr, member_ips) collapse to one, with both patterns merged
  - `test_same_cidr_different_members_kept` — verifies groups with same CIDR but different member sets are kept separate
- `pytest --tb=short -q` — **679 passed**, zero failures

### Slice-level verification (S03, final task):
- ✅ `pytest tests/test_models/test_pipeline_schema.py -v` — enum validation tests pass (from T01)
- ✅ `pytest tests/test_analysis/test_models.py -v` — SubnetGroup validator tests pass (from T01)
- ✅ `pytest tests/test_output/test_models.py -v` — dict construction covered
- ✅ `pytest tests/test_analysis/test_subnet.py -v` — dedup correctness tests pass
- ✅ `pytest --tb=short -q` — 679 passed (exceeds 623+ threshold), zero failures

## Diagnostics

No new runtime observability — both fixes are pure data transforms. Dict construction produces identical output. Subnet dedup correctness is verified by the two new test cases. If subnet groups with distinct member sets go missing from analysis output, inspect the `seen` set in the dedup loop of `group_to_subnets`.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/output/models.py` — replaced `dict[str, Any](usage_raw)` with `dict(usage_raw)` on lines 157 and 238
- `src/policyfoundry/analysis/subnet.py` — replaced break/else dedup with seen-set on (cidr, frozenset(member_ips))
- `tests/test_analysis/test_subnet.py` — added TestDeduplication class with two tests for dedup correctness
- `.gsd/milestones/M003-2heki1/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section
