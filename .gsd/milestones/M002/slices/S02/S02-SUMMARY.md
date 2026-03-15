---
id: S02
parent: M002
milestone: M002
provides:
  - analysis package with DirectionLabel, DirectionResult, AggregatedFlow, SubnetGroup models
  - infer_direction() multi-signal heuristic (well-known port → interface zone → flag → UNKNOWN)
  - aggregate_flows() direction-aware grouping producing ~603 tuples from 83K records
  - group_to_subnets() /24 candidate generator with shared pattern detection
requires:
  - slice: S01
    provides: ExcelTrafficRecord model, ExcelIngestionResult, ingest_excel_file()
affects:
  - S03
key_files:
  - src/policyfoundry/analysis/__init__.py
  - src/policyfoundry/analysis/models.py
  - src/policyfoundry/analysis/direction.py
  - src/policyfoundry/analysis/aggregator.py
  - src/policyfoundry/analysis/subnet.py
key_decisions:
  - DirectionLabel is a standalone StrEnum (INBOUND/OUTBOUND/UNKNOWN) rather than extending adapters.schema.Direction (D045)
  - Direction inference signal priority: well-known port → interface zone → flag 'O' → UNKNOWN fallback (D046)
  - Aggregation key is (src_ip, dst_ip, service_port, protocol, direction) — ephemeral ports excluded (D047)
  - Subnet grouping checks both source-side and destination-side IPs for /24 candidates
patterns_established:
  - Multi-signal heuristic with clear fallback chain for direction inference
  - _GroupAccumulator slots-based class for efficient in-memory aggregation
  - Subnet grouping via ipaddress.ip_network with parameterizable prefix length
observability_surfaces:
  - none (pure stateless functions — no runtime logging needed)
drill_down_paths:
  - .gsd/milestones/M002/slices/S02/tasks/T01-SUMMARY.md
duration: 20m
verification_result: passed
completed_at: 2026-03-15
---

# S02: Traffic Pre-Processing

**Complete analysis package: direction inference, flow aggregation, and subnet grouping — 83K raw flows collapse to ~603 aggregated tuples with direction labels and /24 subnet candidates.**

## What Happened

Built the `src/policyfoundry/analysis/` package with four modules in a single task (T01), since direction inference feeds aggregation which feeds subnet grouping — tightly coupled pure functions sharing a models file.

**models.py** defines `DirectionLabel(StrEnum)` with INBOUND/OUTBOUND/UNKNOWN, plus three Pydantic models: `DirectionResult` (direction + normalized src/dst/service_port), `AggregatedFlow` (grouped tuple with flow_count and sample ephemeral ports), and `SubnetGroup` (CIDR + member IPs + shared traffic patterns). Field validators enforce port ranges 0–65535, flow_count ≥ 1, member_count ≥ 2.

**direction.py** implements `infer_direction()` with a 4-signal heuristic: (1) well-known port < 1024 or in KNOWN_SERVICE_PORTS {5274} identifies the server side; (2) interface zone "inet" identifies the external/server side; (3) flag containing "O" indicates outbound from the firewall; (4) fallback to UNKNOWN for ambiguous cases (both ephemeral ports, no zone/flag signal). The function maps client → src_ip, server → dst_ip and returns a `DirectionResult`.

**aggregator.py** implements `aggregate_flows()` which calls `infer_direction()` per record, groups by (src_ip, dst_ip, service_port, protocol, direction) via a `_GroupAccumulator` (slots-based for efficiency), and returns sorted `AggregatedFlow` list with highest flow_count first. Ephemeral ports are excluded from the grouping key; up to 5 sample source ports are collected per group for diagnostic purposes.

**subnet.py** implements `group_to_subnets()` which checks both source-side and destination-side IPs across all flows. IPs sharing a /N subnet (default /24) AND a traffic pattern (same counterpart IP + service_port + protocol) are grouped. Duplicate groups are merged. Groups require ≥ 2 member IPs. Results sorted largest-first.

## Verification

- `pytest tests/test_analysis/ -v` — **67 passed** (15 model, 27 direction, 12 aggregator, 13 subnet)
- `npx pyright src/policyfoundry/analysis/` — **0 errors, 0 warnings**
- `pytest tests/ -x -q` — **482 passed** (415 baseline + 67 new), 0 failures

All must-haves from the slice plan verified:
- [x] DirectionResult model with direction label + normalized src/dst/service_port mapping
- [x] infer_direction() multi-signal heuristic with correct signal priority
- [x] AggregatedFlow Pydantic model with correct grouping key
- [x] aggregate_flows() calls direction inference, groups correctly, counts flows
- [x] SubnetGroup Pydantic model with CIDR, member IPs, shared patterns
- [x] group_to_subnets() identifies /24 candidates with ≥ 2 IPs sharing a pattern
- [x] Reuses concept of INBOUND/OUTBOUND via new DirectionLabel that adds UNKNOWN
- [x] UNKNOWN direction for both-ephemeral-port cases
- [x] Ephemeral ports excluded from aggregation key
- [x] All code passes pyright strict (src/ scope per D001)

## Requirements Advanced

- R103 (Traffic flow aggregation) — `aggregate_flows()` collapses raw flows into unique tuples with flow counts, producing ~603 from 83K raw rows
- R104 (Direction inference) — `infer_direction()` determines direction from flags, interfaces, and well-known port analysis with 4-signal heuristic
- R105 (Subnet grouping) — `group_to_subnets()` identifies /24 subnet candidates where 2+ IPs share traffic patterns

## Requirements Validated

- R103 — Verified by 12 aggregation tests proving dedup, counting, service port keying, and ephemeral port exclusion
- R104 — Verified by 27 parametrized direction inference tests covering all signal combinations (well-known port, interface zone, flag, both-ephemeral fallback)
- R105 — Verified by 13 subnet grouping tests proving /24 candidates, min 2 IPs, pattern matching, custom prefix lengths

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- `DirectionLabel` is a standalone `StrEnum` rather than extending `adapters.schema.Direction` as initially suggested in research. The adapter's `Direction` has only INBOUND/OUTBOUND and is used in `UniversalRule` validation — adding UNKNOWN would break downstream contracts. This was anticipated in the task plan ("extends the concept").

## Known Limitations

- Direction inference heuristic is tuned for the sample data's flag conventions (U/UI/UIO). Other firewall vendors may use different flag schemes — the heuristic would fall back to UNKNOWN more often.
- Subnet grouping uses strict /24 boundaries by default. Organizational subnetting may use different prefix lengths — the `prefix_length` parameter allows customization, and S03's AI stage makes the final grouping decision (D042).

## Follow-ups

- none

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

## Forward Intelligence

### What the next slice should know
- `aggregate_flows()` returns `list[AggregatedFlow]` sorted by flow_count descending — highest traffic first. S03's analyze stage can use this ordering to prioritize the most significant flows.
- `group_to_subnets()` returns `list[SubnetGroup]` with `shared_patterns: list[dict[str, str | int]]` — each dict has keys like `counterpart_ip`, `service_port`, `protocol`. S03 should use these patterns to inform subnet-level rule proposals.
- DirectionLabel.UNKNOWN applies to ~770 records (2 IPs) with both-ephemeral ports. S03 should handle UNKNOWN gracefully — either skip or flag for human review.
- The `sample_src_ports` field on AggregatedFlow captures up to 5 ephemeral ports per group for diagnostic display.

### What's fragile
- The well-known port threshold (< 1024) plus the KNOWN_SERVICE_PORTS set {5274} is tuned for the sample data. If future traffic exports include other non-standard service ports on high numbers, they'll need to be added to KNOWN_SERVICE_PORTS or caught by the interface/flag signals.

### Authoritative diagnostics
- `pytest tests/test_analysis/test_direction.py -v` — 27 tests covering every signal combination; if direction inference seems wrong, check which signal is winning
- `pytest tests/test_analysis/test_aggregator.py -v` — 12 tests proving the grouping key and ephemeral exclusion

### What assumptions changed
- No assumption changes — the sample data profile matched expectations from the research phase
