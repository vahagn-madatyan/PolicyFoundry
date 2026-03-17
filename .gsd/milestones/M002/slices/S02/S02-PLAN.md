# S02: Traffic Pre-Processing

**Goal:** 83K raw `ExcelTrafficRecord` rows collapse into ~603 aggregated flow tuples with direction labels (INBOUND/OUTBOUND/UNKNOWN) and subnet grouping candidates (~9 /24 subnets), all exposed as Pydantic models consumed by S03.
**Demo:** `pytest tests/test_analysis/ -v` passes all tests. Models, direction inference, aggregation, and subnet grouping produce correct outputs verified against the sample data profile.

## Must-Haves

- `DirectionResult` model with direction label + normalized src/dst/service_port mapping
- `infer_direction()` multi-signal heuristic: well-known port → interface zone → flag → UNKNOWN fallback
- `AggregatedFlow` Pydantic model with (src_ip, dst_ip, service_port, protocol, direction, flow_count)
- `aggregate_flows()` calls direction inference, groups by (src_ip, dst_ip, service_port, protocol, direction), counts flows
- `SubnetGroup` Pydantic model with (cidr, member_ips, member_count, shared_patterns)
- `group_to_subnets()` identifies /24 candidates where 2+ IPs share a subnet and traffic pattern
- Reuses `adapters.schema.Direction` enum (INBOUND/OUTBOUND) — no duplicate enum
- UNKNOWN direction for both-ephemeral-port cases (per research: 770 records, 2 IPs)
- Ephemeral ports excluded from aggregation key (service port only)
- All code passes pyright strict (src/ scope per D001)

## Verification

- `pytest tests/test_analysis/ -v` — all tests pass
- `pytest tests/ -x -q` — full regression, 415+ tests, no failures

Test files:
- `tests/test_analysis/test_direction.py` — parametrized tests covering all signal combinations (well-known port, interface zone, flag, both-ephemeral)
- `tests/test_analysis/test_aggregator.py` — aggregation correctness (dedup, counting, service port in key, ephemeral excluded)
- `tests/test_analysis/test_subnet.py` — subnet grouping (/24 candidates, min 2 IPs, pattern matching)
- `tests/test_analysis/test_models.py` — model validation (required fields, enum values, constraints)

## Tasks

- [x] **T01: Build analysis package with direction inference, flow aggregation, and subnet grouping** `est:45m`
  - Why: S02 is three small, tightly-coupled pure-function modules (~200 LOC production) plus models — direction feeds aggregation feeds subnet grouping. They share a models file and the aggregator calls direction inference internally. One task avoids artificial splits.
  - Files: `src/policyfoundry/analysis/__init__.py`, `src/policyfoundry/analysis/models.py`, `src/policyfoundry/analysis/direction.py`, `src/policyfoundry/analysis/aggregator.py`, `src/policyfoundry/analysis/subnet.py`, `tests/test_analysis/__init__.py`, `tests/test_analysis/test_models.py`, `tests/test_analysis/test_direction.py`, `tests/test_analysis/test_aggregator.py`, `tests/test_analysis/test_subnet.py`
  - Do: Create `analysis/` package. Build `models.py` with `DirectionResult`, `AggregatedFlow`, `SubnetGroup` Pydantic models. Build `direction.py` with `infer_direction()` using multi-signal heuristic (well-known port detection → interface zone → flag "O" → UNKNOWN). Build `aggregator.py` with `aggregate_flows()` that calls `infer_direction()` per record, then groups by (src_ip, dst_ip, service_port, protocol, direction) via Counter. Build `subnet.py` with `group_to_subnets()` that groups IPs by /24 sharing traffic patterns. Reuse `adapters.schema.Direction` for INBOUND/OUTBOUND; add UNKNOWN as a `DirectionLabel(StrEnum)` that extends the concept. Write parametrized tests for all modules. Run full regression to confirm no breakage.
  - Verify: `pytest tests/test_analysis/ -v` all pass + `pytest tests/ -x -q` 415+ tests pass
  - Done when: All 4 test files pass, pyright clean on new src/ files, full test suite ≥415 tests with 0 failures

## Files Likely Touched

- `src/policyfoundry/analysis/__init__.py`
- `src/policyfoundry/analysis/models.py`
- `src/policyfoundry/analysis/direction.py`
- `src/policyfoundry/analysis/aggregator.py`
- `src/policyfoundry/analysis/subnet.py`
- `tests/test_analysis/__init__.py`
- `tests/test_analysis/test_models.py`
- `tests/test_analysis/test_direction.py`
- `tests/test_analysis/test_aggregator.py`
- `tests/test_analysis/test_subnet.py`
