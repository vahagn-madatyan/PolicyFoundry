# S02: Traffic Pre-Processing — UAT

**Milestone:** M002
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 produces pure stateless functions with no CLI surface, no runtime services, and no UI. All outputs are data structures (Pydantic models) consumed by S03. Comprehensive parametrized tests against known data patterns are the definitive proof.

## Preconditions

- Python 3.13 virtualenv activated (`.venv/bin/python`)
- All dependencies installed (`pip install -e ".[dev]"`)
- S01 complete (ExcelTrafficRecord model available)

## Smoke Test

```bash
.venv/bin/python -m pytest tests/test_analysis/ -v --tb=short
```
Expected: 67 passed, 0 failed

## Test Cases

### 1. Direction inference correctly identifies outbound web traffic

1. Run `pytest tests/test_analysis/test_direction.py::TestRealisticScenarios::test_typical_outbound_web -v`
2. **Expected:** PASS — record with IP2 port 443 on inet identified as OUTBOUND, src_ip = IP1 (client), dst_ip = IP2 (server), service_port = 443

### 2. Direction inference returns UNKNOWN for ambiguous flows

1. Run `pytest tests/test_analysis/test_direction.py::TestUnknownFallback -v`
2. **Expected:** 2 PASS — both-ephemeral-port records with no zone/flag signal return UNKNOWN direction

### 3. Aggregation collapses duplicate flows into counted tuples

1. Run `pytest tests/test_analysis/test_aggregator.py::TestBasicAggregation::test_same_tuple_aggregates -v`
2. **Expected:** PASS — 3 identical flows produce 1 AggregatedFlow with flow_count=3

### 4. Ephemeral ports excluded from aggregation key

1. Run `pytest tests/test_analysis/test_aggregator.py::TestEphemeralPortExclusion::test_different_ephemeral_ports_same_group -v`
2. **Expected:** PASS — flows differing only in ephemeral source port collapse into one group

### 5. Subnet grouping identifies /24 candidates

1. Run `pytest tests/test_analysis/test_subnet.py::TestSourceSideGrouping::test_two_ips_same_subnet_same_pattern -v`
2. **Expected:** PASS — two IPs in 10.1.1.0/24 with same traffic pattern produce one SubnetGroup

### 6. Subnet grouping requires minimum 2 IPs

1. Run `pytest tests/test_analysis/test_subnet.py::TestMinimumMembers::test_single_ip_no_group -v`
2. **Expected:** PASS — single IP in a /24 does not produce a SubnetGroup

### 7. Full regression passes

1. Run `pytest tests/ -x -q`
2. **Expected:** 482+ passed, 0 failed — no regression from new code

### 8. Type checking passes

1. Run `npx pyright src/policyfoundry/analysis/`
2. **Expected:** 0 errors, 0 warnings, 0 informations

## Edge Cases

### Both ports well-known (< 1024)

1. Run `pytest tests/test_analysis/test_direction.py::TestWellKnownPort::test_both_well_known_ports_falls_through -v`
2. **Expected:** PASS — when both IP1 and IP2 have well-known ports, the signal falls through to the next heuristic (interface zone)

### Empty input to aggregation

1. Run `pytest tests/test_analysis/test_aggregator.py::TestEmptyInput::test_empty_list -v`
2. **Expected:** PASS — empty input returns empty list, no errors

### Custom prefix length for subnet grouping

1. Run `pytest tests/test_analysis/test_subnet.py::TestCustomPrefixLength -v`
2. **Expected:** 2 PASS — /25 and /16 prefix lengths produce correct groupings

## Failure Signals

- Any test in `tests/test_analysis/` failing — core logic broken
- pyright errors on `src/policyfoundry/analysis/` — type contract violated
- Full regression test count dropping below 482 — existing code broken by new imports or changes
- DirectionLabel missing UNKNOWN value — downstream S03 cannot handle ambiguous flows

## Requirements Proved By This UAT

- R103 — Traffic flow aggregation verified by 12 aggregation tests (dedup, counting, key composition)
- R104 — Direction inference verified by 27 parametrized tests (all signal combinations, realistic scenarios)
- R105 — Subnet grouping candidates verified by 13 tests (/24 detection, minimum members, pattern matching)

## Not Proven By This UAT

- R105 final subnet grouping decision (deferred to S03 — AI makes final call, D042)
- Integration with S01's `ingest_excel_file()` on the actual 83K-row sample file (deferred to S03/S05 integration testing)
- Rich terminal display of aggregation results (deferred to S05)

## Notes for Tester

- This is a pure data-processing slice with no user-facing CLI output yet. All verification is through pytest.
- The 67 test count matches exactly what T01 produced. If you see fewer, check that `tests/test_analysis/__init__.py` exists.
- Direction inference is the most nuanced module — the 27 tests cover every combination of signals. The `TestRealisticScenarios` class is the most representative of real-world data.
