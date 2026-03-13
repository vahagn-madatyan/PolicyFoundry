---
id: T01
parent: S10
milestone: M001
provides:
  - E2E test proving full CLI pipeline (ingestion → Parquet → DuckDB → output) works end-to-end
  - Sample VPC Flow Log fixture with 16 data lines (ACCEPT/REJECT/NODATA, TCP/UDP/ICMP)
  - Reference JSON output fixture for structural regression testing
  - E2E test conftest with real ingestion + mock LLM dispatch by response_model type
key_files:
  - tests/fixtures/sample_flowlogs/vpc_flow_sample.log
  - tests/fixtures/sample_output/reference.json
  - tests/e2e/__init__.py
  - tests/e2e/conftest.py
  - tests/e2e/test_e2e_analyze.py
key_decisions:
  - Mock boundary is LLM and adapter only; config uses real PolicyFoundryConfig with tmp_path data_dir
  - LLM mock dispatches by response_model type (TrafficAnalysis, SecurityAssessment, PolicyProposalList, RuleDecisionList)
  - Reference JSON fixture uses structural comparison (key presence + type matching), not exact value equality
patterns_established:
  - E2E test pattern: real ingestion → real Parquet → real DuckDB queries → mock LLM → real output formatting
  - _e2e_patches() helper returns 3 context managers for config/LLM/adapter mocking
  - _assert_structure_matches() recursive structural comparison for JSON regression
observability_surfaces:
  - none
duration: 15m
verification_result: passed
blocker_discovered: false
completed_at: 2026-03-12
---

# T01: E2E test with flow log fixtures and reference output

**Built 12 E2E tests exercising the full `policyfoundry analyze` CLI path through real ingestion, Parquet storage, and DuckDB queries with mocked LLM/adapter boundaries.**

## What Happened

Created a VPC Flow Log fixture file with 16 parseable data lines (10 ACCEPT, 4 REJECT, 2 NODATA) across TCP/UDP/ICMP protocols, multiple source/destination IPs, and ports 22/80/443/445/3306/8080/53. The fixture uses the standard v2 14-field format matching the existing parser.

The E2E conftest ingests the fixture into real Parquet via `ingest_local_files` + `write_records`, then builds a real `PolicyFoundryConfig` pointing `output.data_dir` at the temp Parquet directory. The LLM mock dispatches by `response_model` type — each pipeline stage (analyze/assess/generate/decide) gets a deterministic Pydantic response. The adapter mock returns empty rules and approves all validations.

Tests cover both `--format rich` (6 tests asserting section presence: Traffic Analysis, risk level, proposals, decisions, token usage) and `--format json` (6 tests asserting valid JSON, PipelineResult schema keys, populated subfields, and structural match against reference fixture). The reference JSON fixture captures the full output structure for regression comparison via recursive key/type matching.

## Verification

- `pytest tests/e2e/ -v` — 12/12 passed (6 Rich + 6 JSON)
- `pytest --tb=short -q` — 361 passed, 0 failures (349 existing + 12 new)
- `tests/fixtures/sample_flowlogs/vpc_flow_sample.log` exists with 18 lines (1 header + 16 data + 1 trailing)
- `tests/fixtures/sample_output/reference.json` exists with valid JSON matching PipelineResult schema

## Diagnostics

None — test-only task. Failures surface through pytest output with full exit code and CLI output in assertion messages.

## Deviations

Used `patch("policyfoundry.main.load_config")` instead of `--config` CLI flag because the `--config` path doesn't actually wire through to pydantic-settings YAML loading (it passes `_yaml_file` which is silently ignored by `extra="ignore"`). This matches the existing CLI test pattern in `tests/test_cli/test_analyze.py`.

## Known Issues

None.

## Files Created/Modified

- `tests/fixtures/sample_flowlogs/vpc_flow_sample.log` — 16 valid VPC Flow Log v2 lines (ACCEPT, REJECT, NODATA) across TCP/UDP/ICMP
- `tests/fixtures/sample_output/reference.json` — Reference JSON structure for PipelineResult regression testing
- `tests/e2e/__init__.py` — Package marker
- `tests/e2e/conftest.py` — E2E fixtures: real ingestion/Parquet, mock LLM dispatch, mock adapter, real config
- `tests/e2e/test_e2e_analyze.py` — 12 E2E tests for Rich and JSON output formats
