---
estimated_steps: 4
estimated_files: 3
---

# T02: Fix dict construction and simplify subnet dedup logic

**Slice:** S03 — Type Safety & Data Integrity
**Milestone:** M003-2heki1

## Description

Two data integrity fixes. First, replace the non-standard `dict[str, Any](usage_raw)` pattern with `dict(usage_raw)` in `output/models.py` — the type annotation on the left side already provides typing information. Second, simplify the subnet dedup logic in `analysis/subnet.py` from a fragile `break`/`else: continue` pattern to a seen-set on `(cidr, frozenset(member_ips))`. The old pattern can incorrectly drop groups when a group's first pattern matches a seen group but the group has a different member set. Since `_merge_same_subnet` already handles pattern merging downstream for groups with identical `(cidr, member_ips)`, the dedup only needs to deduplicate on that key.

## Steps

1. In `src/policyfoundry/output/models.py`, find `dict[str, Any](usage_raw)` on lines 157 and 238. Replace both with `dict(usage_raw)`. Keep the type annotation on the variable being assigned (e.g., `usage_dict: dict[str, Any] = dict(usage_raw)`).
2. In `src/policyfoundry/analysis/subnet.py`, replace the dedup block (approximately lines 53–65) with a seen-set approach: initialize `seen: set[tuple[str, frozenset[str]]] = set()` before the loop. For each group, compute `key = (group.cidr, frozenset(group.member_ips))`. If `key in seen`, skip. Otherwise `seen.add(key)` and append the group.
3. In `tests/test_analysis/test_subnet.py`, add a targeted dedup test: construct two `SubnetGroup` objects with the same CIDR and member_ips but different `shared_patterns`, feed them through the dedup logic, and verify only one survives. Also construct a group with same CIDR but different `member_ips` and verify it is kept. This tests the scenario where the old `break`/`else: continue` logic could misbehave.
4. Run targeted tests then full regression: `pytest tests/test_output/test_models.py tests/test_analysis/test_subnet.py -v && pytest --tb=short -q`

## Must-Haves

- [ ] `dict[str, Any](usage_raw)` replaced with `dict(usage_raw)` on both occurrences in `output/models.py`
- [ ] Subnet dedup uses seen-set on `(cidr, frozenset(member_ips))` instead of `break`/`else: continue`
- [ ] Targeted test verifies dedup keeps groups with different member sets and deduplicates groups with same member sets
- [ ] Full test suite passes (623+ tests, zero regressions)

## Verification

- `pytest tests/test_output/test_models.py -v` — existing from_state tests still pass (dict construction)
- `pytest tests/test_analysis/test_subnet.py -v` — new dedup test passes
- `pytest --tb=short -q` — 623+ tests, zero failures

## Inputs

- `src/policyfoundry/output/models.py` — lines 157 and 238 with `dict[str, Any](usage_raw)` pattern
- `src/policyfoundry/analysis/subnet.py` — dedup block at lines 53–65 with `break`/`else: continue`
- Existing test files for patterns and fixtures

## Observability Impact

- **dict construction fix**: No runtime behavior change — `dict(usage_raw)` produces the same result as `dict[str, Any](usage_raw)`. Failure mode: if `usage_raw` is not dict-like, `TypeError` propagates unchanged.
- **subnet dedup fix**: Groups that were incorrectly dropped by the `break`/`else: continue` pattern will now be preserved. A future agent can inspect dedup correctness by checking `len(deduped)` vs `len(groups)` before `_merge_same_subnet`. If subnet groups with distinct member sets disappear from analysis output, the dedup key `(cidr, frozenset(member_ips))` is the place to look.
- **Inspection**: Both fixes are pure data-transform logic — no new logging or metrics. Correctness is verified through unit tests. The seen-set approach is deterministic and inspectable via debugger or print statement on the `seen` set.

## Expected Output

- `src/policyfoundry/output/models.py` — both `dict[str, Any](...)` calls replaced with `dict(...)`
- `src/policyfoundry/analysis/subnet.py` — dedup block uses seen-set, cleaner and correct
- `tests/test_analysis/test_subnet.py` — new test proving dedup correctness for same/different member sets
