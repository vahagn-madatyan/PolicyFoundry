---
estimated_steps: 5
estimated_files: 5
---

# T01: E2E test with flow log fixtures and reference output

**Slice:** S10 — Infrastructure And Packaging
**Milestone:** M001

## Description

Create sample flow log fixture files and an E2E test that exercises the full `policyfoundry analyze` CLI command through real file I/O (ingestion → Parquet storage → DuckDB queries → output formatting) with mocked LLM and adapter boundaries. Capture reference output fixtures for regression testing.

This is the most valuable deliverable in S10 — it proves the CLI actually works end-to-end before we package it in Docker or provision infrastructure for it.

## Steps

1. Create `tests/fixtures/sample_flowlogs/vpc_flow_sample.log` with 15-20 valid VPC Flow Log v2 lines covering ACCEPT, REJECT, and NODATA actions across multiple source/destination IPs and ports. Reuse the format from `tests/test_ingestion/conftest.py::valid_vpc_v2_line`.
2. Create `tests/e2e/__init__.py` and `tests/e2e/conftest.py` with shared E2E fixtures: a factory that writes a temp config YAML pointing `sources.log_paths` at the fixture file and `output.data_dir` at a `tmp_path` directory. Mock boundary follows D033 — mock `LLMClient` and `FirewallAdapter`, keep real config/ingestion/storage/output.
3. Write `tests/e2e/test_e2e_analyze.py` with tests for both `--format rich` and `--format json`. The Rich test asserts on content patterns (traffic analysis keywords, risk levels, proposal text). The JSON test parses the output and asserts structural keys match the `PipelineResult` schema.
4. Create `tests/fixtures/sample_output/reference.json` containing the expected JSON structure from a successful E2E run, used for structural regression comparison in the JSON test.
5. Run full test suite (`.venv/bin/python -m pytest --tb=short -q`) and confirm 349+ tests pass with 0 failures.

## Must-Haves

- [ ] Sample flow log fixture with valid v2 lines (ACCEPT, REJECT, NODATA)
- [ ] E2E test exercises real ingestion → real Parquet write → real DuckDB query → real output format
- [ ] LLM and adapter are mocked (no real API/AWS calls)
- [ ] Both `--format rich` and `--format json` tested
- [ ] Reference JSON output fixture for structural regression
- [ ] All 349 existing tests still pass

## Verification

- `.venv/bin/python -m pytest tests/e2e/ -v` — E2E tests pass
- `.venv/bin/python -m pytest --tb=short -q` — 349+ tests, 0 failures
- `tests/fixtures/sample_flowlogs/vpc_flow_sample.log` exists with valid v2 lines
- `tests/fixtures/sample_output/reference.json` exists with valid JSON matching PipelineResult schema

## Inputs

- `tests/test_ingestion/conftest.py` — flow log line format reference
- `tests/test_cli/conftest.py` — mock boundary pattern (`_make_mocks`, `sample_pipeline_state`)
- `tests/test_cli/test_analyze.py` — CliRunner invocation pattern
- `src/policyfoundry/main.py` — CLI entrypoint with `app` and `analyze` command
- `src/policyfoundry/config/models.py` — `PolicyFoundryConfig` env prefix and nesting

## Expected Output

- `tests/fixtures/sample_flowlogs/vpc_flow_sample.log` — realistic flow log data
- `tests/fixtures/sample_output/reference.json` — structural reference for JSON regression
- `tests/e2e/__init__.py` — package marker
- `tests/e2e/conftest.py` — E2E fixtures (temp config, mock factories)
- `tests/e2e/test_e2e_analyze.py` — E2E tests for Rich and JSON output
