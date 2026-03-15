# S02 ("Traffic Pre-Processing") — Research

**Date:** 2026-03-15

## Summary

S02 is **already fully implemented and verified**. The `src/policyfoundry/analysis/` package exists with four modules (`models.py`, `direction.py`, `aggregator.py`, `subnet.py`), a clean `__init__.py` exporting 7 public symbols, and comprehensive test coverage (67 tests, all passing). The code correctly processes the 83K-row sample file: direction inference labels all 603 aggregated flows as OUTBOUND (matching the sample profile — all traffic flows from internal zoneA clients to external inet servers), and subnet grouping identifies 24 /24 candidates across 5 subnet ranges (10.195.231.0/24 being the largest with 56 IPs).

The previous execution also produced a complete S02-SUMMARY.md, S02-PLAN.md, S02-UAT.md, and task summaries. The full regression suite stands at 482 tests with 0 failures.

**One gap exists between the slice "After this" definition and what was built:** The roadmap says S02 is "verified by unit tests and Rich summary table displayed in terminal," but the implementation deferred the Rich display to S05. The UAT explicitly notes "Rich terminal display of aggregation results (deferred to S05)" under "Not Proven By This UAT." This gap needs a decision: either (a) accept the deferral as-is since S02's primary value is the data processing modules consumed by S03, or (b) add a Rich summary display for the aggregation/direction/subnet results to the `--source excel` CLI path now.

## Recommendation

**No new implementation work is needed.** The core data-processing modules are complete, tested, and correct. The S02→S03 boundary contract is fully satisfied:

- `aggregate_flows(records: list[ExcelTrafficRecord]) -> list[AggregatedFlow]` ✓
- `infer_direction(flow: ExcelTrafficRecord) -> DirectionResult` ✓ (note: returns `DirectionResult`, not `Direction` — provides richer data including normalized src/dst)
- `group_to_subnets(flows: list[AggregatedFlow]) -> list[SubnetGroup]` ✓
- `AggregatedFlow`, `SubnetGroup`, `DirectionLabel` Pydantic models ✓

The Rich summary table gap is cosmetic — the slice definition's "displayed in terminal" was a verification method, not a core deliverable. The actual deliverables (the data processing functions consumed by S03) are complete. If a Rich display is desired, it would be a small addition to `_run_excel_ingestion()` in `main.py`, calling `aggregate_flows()` + `group_to_subnets()` and rendering results in a Rich table. This would add ~50 LOC but is optional since S05 handles the full CLI integration anyway.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CIDR subnet grouping | `ipaddress` (stdlib) | Already used in `subnet.py` — `ip_network(f'{ip}/24', strict=False)` |
| Direction enum | `analysis.models.DirectionLabel` | Already created with INBOUND/OUTBOUND/UNKNOWN |
| Flow aggregation | `analysis.aggregator.aggregate_flows()` | Already implemented and tested |
| Pydantic models | `analysis.models.*` | All 4 models exist with proper validators |

## Existing Code and Patterns

### Already Built (S02 deliverables — verified working)

- `src/policyfoundry/analysis/models.py` — `DirectionLabel(StrEnum)` with INBOUND/OUTBOUND/UNKNOWN, `DirectionResult` (direction + normalized src/dst/service_port), `AggregatedFlow` (grouped tuple with flow_count ≥ 1, sample_src_ports), `SubnetGroup` (cidr, member_ips, member_count ≥ 2, shared_patterns)
- `src/policyfoundry/analysis/direction.py` — `infer_direction()` with 4-signal priority: well-known port (<1024 or in {5274}) → interface zone ("inet" = external) → flag "O" → UNKNOWN fallback. Helper functions `_result_ip1_server()` and `_result_ip2_server()` handle the src/dst mapping.
- `src/policyfoundry/analysis/aggregator.py` — `aggregate_flows()` calls `infer_direction()` per record, groups by `(src_ip, dst_ip, service_port, protocol, direction)` using `_GroupAccumulator` (slots-based), returns sorted by flow_count descending. Max 5 sample ephemeral ports collected.
- `src/policyfoundry/analysis/subnet.py` — `group_to_subnets()` checks both source-side and destination-side IPs. Groups by (subnet_cidr, traffic_pattern) → collects IPs. Deduplicates, merges same-subnet groups, requires ≥ 2 members. Prefix length parameterizable (default /24).
- `src/policyfoundry/analysis/__init__.py` — Exports: `AggregatedFlow`, `DirectionLabel`, `DirectionResult`, `SubnetGroup`, `aggregate_flows`, `group_to_subnets`, `infer_direction`

### S01 Outputs (consumed by S02)

- `src/policyfoundry/ingestion/excel_schema.py` — `ExcelTrafficRecord` with neutral naming (ip1/port1/ip2/port2 per D043). Ports are int (coercion already handled by S01). Strings stripped of whitespace.
- `src/policyfoundry/ingestion/excel.py` — `ingest_excel_file()` returns `ExcelIngestionResult` with `.records: list[ExcelTrafficRecord]`. This is the input to `aggregate_flows()`.

### CLI Integration Point

- `src/policyfoundry/main.py` — `_run_excel_ingestion()` handles `--source excel`. Currently prints ingestion summary only. The analysis modules are NOT imported or called here. S03/S05 will wire them in.

### Downstream Consumer (S03)

- `src/policyfoundry/pipeline/state.py` — `PipelineState(TypedDict)` pattern. S03 will create `ExcelPipelineState` consuming `AggregatedFlow` and `SubnetGroup` data.
- `src/policyfoundry/pipeline/schema.py` — `TrafficAnalysis`, `PolicyProposal`, `RuleDecision` models. S03 may extend these for Excel-specific analysis.

## Constraints

- **D043: Neutral naming preserved** — `ExcelTrafficRecord` uses ip1/port1/ip2/port2. Direction inference correctly maps to src/dst without modifying S01 models. ✓ Already implemented.
- **D042: Subnet grouping by AI** — `group_to_subnets()` produces *candidates*, not final rules. The LLM in S03 makes the final grouping decision. ✓ `SubnetGroup.shared_patterns` provides the AI with pattern context.
- **Pyright strict in src/ (D001)** — All analysis modules pass pyright strict. ✓ Verified in S02-SUMMARY.
- **482 tests baseline** — Full regression passes with 0 failures. ✓ Verified.
- **No new dependencies** — `ipaddress` is stdlib. No pip changes needed. ✓

## Common Pitfalls

- **Mixing up src/dst assignment** — In the sample data, IP1 (on inet) is the *server* and IP2 (on zoneA) is the *client*. `_result_ip1_server()` correctly maps src=ip2 (client), dst=ip1 (server). Verified by `TestRealisticScenarios::test_typical_outbound_web`.
- **Ephemeral port in aggregation key** — Would produce ~30K tuples instead of ~603. Already avoided — only `service_port` is in the key. Verified by `TestEphemeralPortExclusion::test_different_ephemeral_ports_same_group`.
- **Over-aggressive subnet grouping** — /24 is the default, not /16 (which would group 132 of 133 IPs too broadly). Parameterizable via `prefix_len` argument. AI makes final call per D042.
- **Both-ephemeral ambiguity** — 770 records (0.92%) from 2 IPs produce UNKNOWN direction. Correctly handled as fallback signal 4. Verified by `TestUnknownFallback`.

## Open Risks

- **None for this slice** — All implementation is complete and verified. The direction inference heuristic is tuned for the sample data's Juniper SRX flags (U/UI/UIO). Other vendors may produce more UNKNOWN labels, but that's handled gracefully.
- **Rich display gap** — Minor: the roadmap's "After this" mentions a Rich summary table in terminal, but this was deferred to S05. Not a blocking risk since S03 consumes the data processing modules, not a CLI display.

## Verified Data Profile (from live sample analysis)

| Metric | Value | Status |
|--------|-------|--------|
| Total records ingested | 83,633 | ✓ matches M002-CONTEXT |
| Aggregated flows | 603 | ✓ matches ~600 prediction |
| Direction distribution | 603 OUTBOUND, 0 INBOUND, 0 UNKNOWN | ✓ (note: both-ephemeral records aggregate with their patterns) |
| Unique source IPs | 133 | ✓ matches expected (these are internal zoneA clients) |
| Unique destination IPs | 7 | ✓ matches expected (external inet servers) |
| Service ports | 443 (258 flows), 80 (85 flows), 5274 (70 flows), + 190 ephemeral-port flows | ✓ |
| Interface pairs | zoneA → inet (100%) | ✓ |
| Subnet groups | 24 groups across 5 /24 ranges | ✓ reasonable |
| Largest subnet group | 10.195.231.0/24 with 56 IPs | ✓ |

**Direction accuracy note:** The research predicted 770 UNKNOWN records, but the actual aggregation produces 0 UNKNOWN flows. This is because the "both-ephemeral" records still have interface signals (inet vs zoneA) that resolve direction — the interface zone signal (signal 2) catches them before falling to UNKNOWN. This is correct and actually better than predicted.

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| R103 — Traffic flow aggregation | **Complete** | `aggregate_flows()` + 12 tests. 83K → 603 tuples verified. |
| R104 — Direction inference | **Complete** | `infer_direction()` + 27 parametrized tests. All signal combinations covered. |
| R105 — Subnet grouping candidates | **Complete** | `group_to_subnets()` + 13 tests. 24 subnet groups identified. AI makes final decision in S03 (D042). |

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Python ipaddress | (stdlib) | N/A — no skill needed |
| Pydantic BaseModel | (well-established in codebase) | N/A — patterns already followed |
| Network CIDR grouping | `automateyournetwork/netclaw@subnet-calculator` (7 installs) | Not relevant — stdlib ipaddress is sufficient |

## Sources

- Live sample analysis via `.venv/bin/python` against `referance/samples/test-FW501_20260219_All_App1-updated.xlsx` — all metrics verified empirically
- Existing S02 artifacts (S02-SUMMARY.md, S02-PLAN.md, S02-UAT.md) — confirmed implementation completeness
- `pytest tests/test_analysis/ -v` — 67 passed in 0.34s, confirming all tests green
- `pytest tests/ -x -q` — 482 passed in 20s, confirming full regression clean
- M002-ROADMAP.md boundary map — S02→S03 contract verified against actual module signatures
- Decisions register — D042, D043, D044 all respected in implementation
