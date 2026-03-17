# S05: CLI Integration & End-to-End

**Milestone:** M002
**Risk:** low
**Depends:** S03, S04
**Estimate:** 1 task

## Goal

Wire all S01–S04 modules into a complete CLI workflow: `policyfoundry analyze --source excel --file traffic.xlsx --export xlsx` produces both Rich terminal output and a filled change request form. Add `--export` and `--template` options. Write CLI integration tests proving all layers compose.

## Tasks

- [x] **T01: Wire CLI + Integration Tests** `est:medium`
  Wire `--export` (xlsx/pdf) and `--template` options into the `analyze` command. Replace S01's ingestion-only handler with full pipeline flow (ingest → pipeline → output → export). Write 19 CLI integration tests covering Rich output, JSON output, export to xlsx/pdf, template fill, error handling, and end-to-end composition.

## Verification

- All 19 new CLI integration tests pass
- All 611 existing tests pass (no regressions)
- All 12 e2e tests pass
- `--export xlsx` creates a valid xlsx file with rule data
- `--export pdf` creates a valid PDF with %PDF magic bytes
- `--export xlsx,pdf` creates both files in one invocation
- `--template custom.xlsx` fills a user-provided template
- Error handling: missing --file, --template without --export, pipeline errors all produce structured Rich error panels
