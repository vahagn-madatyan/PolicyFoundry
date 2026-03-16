# S05: CLI Integration & End-to-End — UAT

**Milestone:** M002
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: CLI integration tests verify composition with mocked LLM boundary. Live runtime verification requires real LLM (Ollama) and the sample Excel file — user should confirm output quality visually.

## Preconditions

- Python venv activated (`.venv/bin/activate`)
- Ollama running with `llama3.2` model available (for live tests)
- Sample Excel file available at the expected path (e.g. `data/traffic.xlsx`)

## Smoke Test

```bash
policyfoundry analyze --source excel --file data/traffic.xlsx
```
Should display: Excel Pipeline Summary panel, Traffic Analysis, Proposals, Decisions table, Token Usage footer. Exit code 0.

## Test Cases

### 1. Rich output from Excel analysis

1. Run `policyfoundry analyze --source excel --file data/traffic.xlsx`
2. **Expected:** Rich terminal output with "Excel Pipeline Summary" panel showing run ID, flow counts, direction breakdown, subnet candidates. Traffic analysis, proposals, and decisions sections visible. Token usage footer with cost.

### 2. JSON output from Excel analysis

1. Run `policyfoundry analyze --source excel --file data/traffic.xlsx --format json`
2. **Expected:** Valid JSON with keys: `run_id`, `aggregated_flows`, `subnet_groups`, `analysis`, `assessment`, `proposals`, `decisions`, `token_usage`. Parseable with `| python -m json.tool`.

### 3. Export xlsx change request form

1. Run `policyfoundry analyze --source excel --file data/traffic.xlsx --export xlsx`
2. **Expected:** Rich terminal output displayed, then "✓ Excel change request exported: data/traffic_change_request.xlsx". File opens in Excel/Numbers with metadata header rows, styled column headers, and rule data rows.

### 4. Export PDF change request document

1. Run `policyfoundry analyze --source excel --file data/traffic.xlsx --export pdf`
2. **Expected:** Rich terminal output displayed, then "✓ PDF change request exported: data/traffic_change_request.pdf". File opens in Preview with "Firewall Change Request" title, metadata section, and rule table.

### 5. Export both xlsx and pdf

1. Run `policyfoundry analyze --source excel --file data/traffic.xlsx --export xlsx,pdf`
2. **Expected:** Both export files created. Both confirmation messages displayed.

### 6. Custom template fill

1. Create a template with headers: Source, Destination, Port, Protocol, Direction, Action, Justification, Risk
2. Run `policyfoundry analyze --source excel --file data/traffic.xlsx --export xlsx --template custom_template.xlsx`
3. **Expected:** Template filled with rule data below the header row. Original template structure preserved.

## Edge Cases

### Missing --file option

1. Run `policyfoundry analyze --source excel`
2. **Expected:** Exit code 1, error panel with "MISSING_FILE_OPTION", message includes example usage.

### --template without --export

1. Run `policyfoundry analyze --source excel --file data/traffic.xlsx --template template.xlsx`
2. **Expected:** Exit code 1, error panel with "TEMPLATE_WITHOUT_EXPORT".

### Non-existent file

1. Run `policyfoundry analyze --source excel --file nonexistent.xlsx`
2. **Expected:** Exit code 1, error panel with file-related error.

## Failure Signals

- Exit code 1 on any of the happy-path test cases
- Missing "Excel Pipeline Summary" in Rich output
- Missing "Token Usage" footer
- Export files not created or empty
- PDF without %PDF magic bytes
- xlsx without data rows below header

## Requirements Proved By This UAT

- R108 — Rich terminal output showing proposed FW rules (test cases 1, 2)
- R109 — FW change request form export to Excel (test case 3, already validated in S04 but re-verified through CLI)
- R110 — FW change request form export to PDF (test case 4, already validated in S04 but re-verified through CLI)
- R111 — Custom template support (test case 6, already validated in S04 but re-verified through CLI)

## Not Proven By This UAT

- LLM analysis quality (depends on model and prompts — not testable via UAT structure)
- Performance with 83K-row files (needs the full sample dataset)
- Real-world Excel format variability (tested with sample data only)

## Notes for Tester

- The automated test suite (19 CLI tests + 611 unit/integration + 12 e2e = 642 total) provides strong coverage of the composition layer. Live testing with the sample Excel file and Ollama confirms the full stack works end-to-end including actual LLM responses.
- Token costs will vary depending on the LLM model and traffic volume.
- Export files are named `{source_stem}_change_request.{ext}` and placed in the same directory as the input file.
