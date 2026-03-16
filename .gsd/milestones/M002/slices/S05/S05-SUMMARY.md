---
id: S05
parent: M002
milestone: M002
provides:
  - Updated `analyze` command with `--export`, `--template` CLI options
  - Full Excel pipeline integration (ingest → pipeline → output → export)
  - 19 CLI integration tests for the complete Excel workflow
requires:
  - slice: S01
    provides: Excel ingestion with auto-detect column mapping
  - slice: S02
    provides: Traffic aggregation, direction inference, subnet grouping
  - slice: S03
    provides: Excel LangGraph pipeline, Rich/JSON output formatters
  - slice: S04
    provides: xlsx/pdf export functions, ChangeRequestEntry model
affects: []
key_files:
  - src/policyfoundry/main.py
  - tests/test_cli/test_excel_analyze.py
key_decisions:
  - D054: Full pipeline replaces ingestion-only handler — `--source excel` now runs ingest → pipeline → output → export in one invocation
  - D055: Export file naming uses source file stem — `traffic.xlsx` → `traffic_change_request.xlsx`
  - D056: Comma-separated --export formats — `--export xlsx,pdf` produces both files in one run
  - D057: --template requires --export xlsx — validated at CLI boundary with TEMPLATE_WITHOUT_EXPORT error code
patterns_established:
  - Excel CLI integration test pattern: mock at ingestion + pipeline boundaries, verify Rich/JSON output content and export file creation
observability_surfaces:
  - Structured error panels for all failure modes (MISSING_FILE_OPTION, TEMPLATE_WITHOUT_EXPORT, EMPTY_EXCEL_FILE, PIPELINE_STAGE_FAILED)
  - Export confirmation messages with file paths printed to console
drill_down_paths: []
duration: ~20 minutes
verification_result: passed
completed_at: 2026-03-15
---

# S05: CLI Integration & End-to-End

**Complete end-to-end Excel workflow: `policyfoundry analyze --source excel --file traffic.xlsx --export xlsx,pdf` runs the full pipeline and exports change request forms.**

## What Happened

Replaced the S01 ingestion-only handler (`_run_excel_ingestion`) with a full pipeline function (`_run_excel_analyze`) that composes all S01–S04 modules: Excel ingestion → LangGraph pipeline → Rich/JSON output → optional xlsx/pdf export. Added `--export` (supports `xlsx`, `pdf`, or `xlsx,pdf`) and `--template` CLI options to the `analyze` command.

Wrote 19 CLI integration tests covering: Rich output (4 tests: exit code, pipeline summary panel, decisions section, token usage footer), JSON output (3 tests: exit code, valid JSON with all keys, token usage), export (7 tests: xlsx creation, pdf creation, both formats, template fill, xlsx rule data content, pdf magic bytes), error handling (4 tests: missing --file, --template without --export, pipeline errors, nonexistent file), and end-to-end composition (2 tests: Rich + dual export, JSON + export).

All 19 new tests + 611 existing tests + 12 e2e tests pass (642 total, zero failures).

## Verification

- **19 new CLI integration tests**: All pass — covers Rich output, JSON output, xlsx export, pdf export, dual export, template fill, error paths, end-to-end composition
- **611 existing tests**: All pass — zero regressions from CLI refactoring
- **12 e2e tests**: All pass — VPC flow log path unaffected by Excel changes
- **Export file creation**: Verified xlsx files contain metadata header (row 4 = rule count) and data rows (row 7+ = source populated); PDF files start with `%PDF` magic bytes
- **Error handling**: Structured Rich error panels with error codes for all failure modes

## Requirements Advanced

- R108 — Rich terminal output now shows proposed FW rules from the full Excel pipeline (was only showing ingestion summary)

## Requirements Validated

- R108 — Rich terminal output showing proposed FW rules: Verified by 4 CLI integration tests (exit code, pipeline summary, decisions, token usage) + 2 end-to-end composition tests. `--source excel` now displays the full Excel Pipeline Summary panel, traffic analysis, proposals, decisions table, and token usage footer.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

The S05 plan was a blocker placeholder (auto-mode planning failed). Plan was written and executed from scratch based on the milestone roadmap's S05 description and boundary map. Single-task execution was sufficient — the work was pure wiring with no novel complexity.

## Known Limitations

- `--export` option is only wired for `--source excel` (VPC flow log path doesn't have export support, which is expected — VPC path uses a different pipeline state shape)
- Export file naming is tied to source file location — output files go to the same directory as the input file (no `--output-dir` option)

## Follow-ups

- none

## Files Created/Modified

- `src/policyfoundry/main.py` — Replaced `_run_excel_ingestion` with `_run_excel_analyze` + `_export_results`; added `--export` and `--template` CLI options; added imports for export and Excel pipeline modules
- `tests/test_cli/test_excel_analyze.py` — New: 19 CLI integration tests for the full Excel workflow
- `.gsd/milestones/M002/slices/S05/S05-PLAN.md` — Replaced blocker placeholder with actual plan

## Forward Intelligence

### What the next slice should know
- This is the terminal slice for M002. No downstream slices.
- All M002 success criteria are now implemented and testable through the CLI.

### What's fragile
- The `_run_excel_analyze` function uses a local import for `ingest_excel_file` — if the module path changes, the import breaks silently at runtime (only when `--source excel` is used).

### Authoritative diagnostics
- `pytest tests/test_cli/test_excel_analyze.py -v` — fastest verification of CLI integration
- `pytest tests/ --ignore=tests/e2e -q` — full unit/integration suite (611 tests, ~21s)

### What assumptions changed
- S05 was estimated as low risk and confirmed low — pure wiring with well-defined boundaries from S01–S04.
