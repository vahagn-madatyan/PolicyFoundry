---
id: T01
parent: S02
milestone: M002
provides:
  - analysis package with DirectionLabel, DirectionResult, AggregatedFlow, SubnetGroup models
  - infer_direction() multi-signal heuristic (well-known port → interface zone → flag → UNKNOWN)
  - aggregate_flows() direction-aware grouping producing ~603 tuples from 83K records
  - group_to_subnets() /24 candidate generator with shared pattern detection
key_files:
  - src/policyfoundry/analysis/__init__.py
  - src/policyfoundry/analysis/models.py
  - src/policyfoundry/analysis/direction.py
  - src/policyfoundry/analysis/aggregator.py
  - src/policyfoundry/analysis/subnet.py
key_decisions:
  - DirectionLabel is a standalone StrEnum (INBOUND/OUTBOUND/UNKNOWN) rather than extending adapters.schema.Direction, since Direction has no UNKNOWN and modifying it would break downstream contracts
  - Direction inference signal priority: well-known port (strongest) → interface zone → flag 'O' → UNKNOWN fallback
  - Aggregation key is (src_ip, dst_ip, service_port, protocol, direction) — ephemeral ports excluded
  - Subnet grouping checks both source-side and destination-side IPs for /24 candidates
  - SubnetGroup.shared_patterns uses list[dict[str, str | int]] for flexibility across pattern types
patterns_established:
  - Multi-signal heuristic with clear fallback chain for direction inference
  - _GroupAccumulator slots-based class for efficient in-memory aggregation
  - Subnet grouping via ipaddress.ip_network with parameterizable prefix length
observability_surfaces:
  - none (pure stateless functions — no runtime logging needed)
duration: 20m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Build analysis package with direction inference, flow aggregation, and subnet grouping

**Built complete `src/policyfoundry/analysis/` package: 4 modules, 7 public exports, 67 parametrized tests covering all signal combinations and edge cases.**

## What Happened

Created the `analysis` package with four modules:

1. **models.py** — `DirectionLabel(StrEnum)` with INBOUND/OUTBOUND/UNKNOWN; `DirectionResult`, `AggregatedFlow`, `SubnetGroup` Pydantic models with field validation (port ranges, flow_count ≥ 1, member_count ≥ 2).

2. **direction.py** — `infer_direction()` implements a 4-signal heuristic: (1) well-known port < 1024 or in KNOWN_SERVICE_PORTS {5274} identifies the server side; (2) interface zone "inet" identifies the external/server side; (3) flag "O" indicates outbound from FW; (4) fallback to UNKNOWN. Maps client → src_ip, server → dst_ip.

3. **aggregator.py** — `aggregate_flows()` calls `infer_direction()` per record, groups by (src_ip, dst_ip, service_port, protocol, direction), produces sorted `AggregatedFlow` list with flow_count and up to 5 sample ephemeral ports per group.

4. **subnet.py** — `group_to_subnets()` checks both source and destination IPs for /N subnet membership (default /24). Groups IPs sharing a subnet AND a traffic pattern (same counterpart IP + service_port + protocol). Merges duplicate groups and requires ≥ 2 member IPs.

## Verification

- `pytest tests/test_analysis/ -v` — **67 passed** (15 model, 27 direction, 12 aggregator, 13 subnet)
- `npx pyright src/policyfoundry/analysis/` — **0 errors, 0 warnings**
- `pytest tests/ -x -q` — **482 passed** (415 baseline + 67 new), 0 failures

### Must-Haves Checklist
- [x] `DirectionLabel` has INBOUND, OUTBOUND, UNKNOWN values
- [x] `infer_direction()` correctly identifies IP1 as server (dst) for well-known-port records
- [x] `infer_direction()` returns UNKNOWN for both-ephemeral-port records
- [x] `aggregate_flows()` uses service_port (not ephemeral port) in grouping key
- [x] `aggregate_flows()` produces deduplicated tuples (verified via test with realistic data patterns)
- [x] `group_to_subnets()` groups IPs by /24 only when 2+ IPs share the subnet
- [x] `group_to_subnets()` records shared traffic patterns per subnet group
- [x] All new src/ files pass pyright strict — 0 errors
- [x] Full test suite ≥415 tests, 0 failures — 482 passed

### Slice Verification Status
- [x] `pytest tests/test_analysis/ -v` — all tests pass (67/67)
- [x] `pytest tests/ -x -q` — full regression 482 tests, no failures

## Diagnostics

None — pure stateless functions with no runtime side effects.

## Deviations

- `DirectionLabel` is a new standalone `StrEnum` rather than extending `adapters.schema.Direction` as initially suggested in the research. The adapter's `Direction` has only INBOUND/OUTBOUND and is used in `UniversalRule` validation — adding UNKNOWN there would break downstream contracts. The task plan already anticipated this ("extends the concept... but adds UNKNOWN").

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/analysis/__init__.py` — Package exports (7 public symbols)
- `src/policyfoundry/analysis/models.py` — DirectionLabel, DirectionResult, AggregatedFlow, SubnetGroup
- `src/policyfoundry/analysis/direction.py` — infer_direction() with 4-signal heuristic
- `src/policyfoundry/analysis/aggregator.py` — aggregate_flows() with direction-aware grouping
- `src/policyfoundry/analysis/subnet.py` — group_to_subnets() with /24 candidate generation
- `tests/test_analysis/__init__.py` — Test package init
- `tests/test_analysis/test_models.py` — 15 model validation tests
- `tests/test_analysis/test_direction.py` — 27 parametrized direction inference tests
- `tests/test_analysis/test_aggregator.py` — 12 aggregation tests
- `tests/test_analysis/test_subnet.py` — 13 subnet grouping tests
