---
estimated_steps: 6
estimated_files: 10
---

# T01: Build analysis package with direction inference, flow aggregation, and subnet grouping

**Slice:** S02 — Traffic Pre-Processing
**Milestone:** M002

## Description

Create the `src/policyfoundry/analysis/` package with four modules: models, direction inference, flow aggregation, and subnet grouping. These are pure stateless functions transforming `ExcelTrafficRecord` lists into `AggregatedFlow` and `SubnetGroup` outputs for S03's LangGraph pipeline. Direction inference must run first (maps ip1/ip2 → src/dst), aggregation groups by the normalized tuple, and subnet grouping identifies /24 candidates. Write comprehensive parametrized tests covering all signal combinations, edge cases, and the boundary contract to S03.

## Steps

1. **Create `analysis/models.py`** — Define `DirectionLabel(StrEnum)` with INBOUND/OUTBOUND/UNKNOWN (extends the concept from `adapters.schema.Direction` but adds UNKNOWN for ambiguous cases). Define `DirectionResult(BaseModel)` with direction, src_ip, dst_ip, service_port, client_port fields. Define `AggregatedFlow(BaseModel)` with src_ip, dst_ip, service_port, protocol, direction, flow_count, src_interface, dst_interface, sample_src_ports. Define `SubnetGroup(BaseModel)` with cidr (str), member_ips (list[str]), member_count (int), shared_patterns (list of dicts describing dst/port/proto patterns). Write `tests/test_analysis/test_models.py` with validation tests.

2. **Create `analysis/direction.py`** — Implement `infer_direction(record: ExcelTrafficRecord) -> DirectionResult` with multi-signal heuristic: (a) well-known port signal: if exactly one side has port < 1024 or port in KNOWN_SERVICE_PORTS (e.g. {5274}), that side is server, other is client; (b) interface zone signal: 'inet' side is external; (c) flag signal: 'O' in flag suggests outbound from FW perspective; (d) fallback: UNKNOWN when both ports are ephemeral and no interface signal resolves it. When direction resolved, map: src_ip=client IP, dst_ip=server IP, service_port=server port. Write `tests/test_analysis/test_direction.py` with parametrized tests for all signal combos.

3. **Create `analysis/aggregator.py`** — Implement `aggregate_flows(records: list[ExcelTrafficRecord]) -> list[AggregatedFlow]`. For each record, call `infer_direction()` to get normalized src/dst/service_port. Group by (src_ip, dst_ip, service_port, protocol, direction) using a Counter/dict. Produce one `AggregatedFlow` per group with flow_count and metadata from the first record. Write `tests/test_analysis/test_aggregator.py`.

4. **Create `analysis/subnet.py`** — Implement `group_to_subnets(flows: list[AggregatedFlow], prefix_len: int = 24) -> list[SubnetGroup]`. Group flows by src_ip side: collect src_ips sharing a /24 that also share traffic patterns (same dst_ip + service_port + protocol). Also check dst_ip side. Use `ipaddress.ip_network(f'{ip}/{prefix_len}', strict=False)` for subnet computation. Require at least 2 IPs per subnet to create a candidate. Write `tests/test_analysis/test_subnet.py`.

5. **Create `analysis/__init__.py`** — Export all public symbols: `DirectionLabel`, `DirectionResult`, `AggregatedFlow`, `SubnetGroup`, `infer_direction`, `aggregate_flows`, `group_to_subnets`.

6. **Run full verification** — `pytest tests/test_analysis/ -v` all pass + `pytest tests/ -x -q` ≥415 tests pass + pyright on new src files.

## Must-Haves

- [ ] `DirectionLabel` has INBOUND, OUTBOUND, UNKNOWN values
- [ ] `infer_direction()` correctly identifies IP1 as server (dst) for well-known-port records
- [ ] `infer_direction()` returns UNKNOWN for both-ephemeral-port records
- [ ] `aggregate_flows()` uses service_port (not ephemeral port) in grouping key
- [ ] `aggregate_flows()` produces ~603 tuples from 83K records (verified via test with realistic data)
- [ ] `group_to_subnets()` groups IPs by /24 only when 2+ IPs share the subnet
- [ ] `group_to_subnets()` records shared traffic patterns per subnet group
- [ ] All new src/ files pass pyright strict
- [ ] Full test suite ≥415 tests, 0 failures

## Verification

- `pytest tests/test_analysis/ -v` — all new tests pass
- `pytest tests/ -x -q` — full suite ≥415 tests, 0 failures
- `.venv/bin/pyright src/policyfoundry/analysis/` — 0 errors

## Inputs

- `src/policyfoundry/ingestion/excel_schema.py` — `ExcelTrafficRecord` model with ip1/port1/ip2/port2 neutral naming
- `src/policyfoundry/adapters/schema.py` — `Direction(StrEnum)` with INBOUND/OUTBOUND for downstream compatibility reference
- S02-RESEARCH.md — Data profile (603 tuples, 9 /24 subnets, 770 UNKNOWN records, direction inference logic)
- S01 forward intelligence — port coercion already done, flag field contains "U"/"UI"/"UIO"

## Expected Output

- `src/policyfoundry/analysis/__init__.py` — Package exports
- `src/policyfoundry/analysis/models.py` — DirectionLabel, DirectionResult, AggregatedFlow, SubnetGroup
- `src/policyfoundry/analysis/direction.py` — infer_direction() with multi-signal heuristic
- `src/policyfoundry/analysis/aggregator.py` — aggregate_flows() with direction-aware grouping
- `src/policyfoundry/analysis/subnet.py` — group_to_subnets() with /24 candidate generation
- `tests/test_analysis/__init__.py` — Test package init
- `tests/test_analysis/test_models.py` — Model validation tests
- `tests/test_analysis/test_direction.py` — Direction inference parametrized tests
- `tests/test_analysis/test_aggregator.py` — Aggregation tests
- `tests/test_analysis/test_subnet.py` — Subnet grouping tests
