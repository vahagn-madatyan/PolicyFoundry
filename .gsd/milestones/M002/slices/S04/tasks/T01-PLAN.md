---
estimated_steps: 5
estimated_files: 10
---

# T01: Export package with ChangeRequestEntry model and xlsx export

**Slice:** S04 — Change Request Form Export
**Milestone:** M002

## Description

Create the `export/` package with the `ChangeRequestEntry` flattening model, `ExportError` exception, and `export_xlsx()` function supporting both default and custom templates. This delivers R109 (xlsx export) and R111 (custom template support).

## Steps

1. **Add fpdf2 dependency and ExportError exception.** Add `fpdf2>=2.8` to `[project.dependencies]` in pyproject.toml. Add `ExportError(PolicyFoundryError)` to `exceptions.py` following the established hierarchy pattern. Run `uv sync` to install.

2. **Create export/models.py with ChangeRequestEntry and flattening logic.** Define `ChangeRequestEntry` Pydantic BaseModel with fields: source (str), destination (str), port (str), protocol (str), direction (str), action (str), justification (str), risk (str), proposal_id (str), approval_required (bool). Add helper functions: `format_endpoints(endpoints: list[NetworkEndpoint]) -> str` (join CIDRs, "any" for is_any, sg-id/tag for others), `format_port_range(port_range: PortRange | None) -> str` (single port, range, or "any"). Add `flatten_to_entries(state: ExcelPipelineState) -> list[ChangeRequestEntry]` that uses `ExcelPipelineResult.from_state()` for typed reconstruction, pairs proposals with decisions by proposal_id, and produces one entry per decision (skipping SKIP actions).

3. **Create export/change_request.py with export_xlsx().** Default mode: create workbook with metadata section (rows 1–5: Generated, Run ID, Source Type, Total Rules, blank separator), then styled header row (bold, blue fill, white font) with all ChangeRequestEntry fields, then data rows. Set column widths proportionally (wider for justification). Template mode: `load_workbook(template_path)`, scan first sheet row 1 for known column names (case-insensitive match against COLUMN_MAP dict), determine start row (first empty row after header), write data into matched columns only. Wrap both paths in try/except → `ExportError` with error_code and details.

4. **Create export/__init__.py with public API.** Re-export `ChangeRequestEntry`, `flatten_to_entries`, `export_xlsx` (and later `export_pdf`).

5. **Write tests.** `tests/test_export/__init__.py` (empty). `tests/test_export/conftest.py` with `sample_excel_state` fixture (reuse pattern from `tests/test_output/conftest.py` — full ExcelPipelineState with proposals+decisions, plus empty variant). `tests/test_export/test_models.py`: test format_endpoints (multiple CIDRs, is_any, sg-id, tag, empty list), format_port_range (single, range, None), flatten_to_entries (correct field mapping, SKIP filtering, empty proposals, missing decision for proposal). `tests/test_export/test_xlsx_export.py`: test default export (opens with openpyxl, checks metadata rows, header row, data rows, column count), test custom template (create a template fixture xlsx with known headers in different order, verify data fills correct columns), test empty proposals (metadata only, no data rows), test ExportError on invalid path.

## Must-Haves

- [ ] fpdf2 added to pyproject.toml dependencies and installed
- [ ] ExportError in exceptions.py with error_code/details support
- [ ] ChangeRequestEntry flattens proposal+decision to display-ready strings
- [ ] format_endpoints handles: multiple CIDRs joined, is_any → "any", sg-id, tag, empty → "any"
- [ ] format_port_range handles: single port, range, None → "any"
- [ ] flatten_to_entries skips SKIP decisions, pairs by proposal_id
- [ ] export_xlsx default produces valid xlsx with metadata + styled headers + data
- [ ] export_xlsx with template_path fills user template by column name matching
- [ ] Both export paths handle empty proposals (metadata only)
- [ ] All new src/ code passes pyright strict

## Verification

- `pytest tests/test_export/test_models.py -v` — all pass
- `pytest tests/test_export/test_xlsx_export.py -v` — all pass
- `npx pyright src/policyfoundry/export/` — 0 errors

## Inputs

- `src/policyfoundry/pipeline/excel_state.py` — ExcelPipelineState TypedDict (boundary contract from S03)
- `src/policyfoundry/output/models.py` — ExcelPipelineResult.from_state() for typed reconstruction
- `src/policyfoundry/pipeline/schema.py` — PolicyProposal, RuleDecision models
- `src/policyfoundry/adapters/schema.py` — UniversalRule, NetworkEndpoint, PortRange, Direction, RuleAction, RiskLevel
- `src/policyfoundry/exceptions.py` — PolicyFoundryError base class
- `tests/test_output/conftest.py` — sample_excel_state fixture pattern to reuse

## Expected Output

- `src/policyfoundry/export/__init__.py` — public API re-exports
- `src/policyfoundry/export/models.py` — ChangeRequestEntry + flatten_to_entries + format helpers
- `src/policyfoundry/export/change_request.py` — export_xlsx()
- `src/policyfoundry/exceptions.py` — ExportError added
- `pyproject.toml` — fpdf2 dependency added
- `tests/test_export/__init__.py` — package init
- `tests/test_export/conftest.py` — shared fixtures
- `tests/test_export/test_models.py` — model/flattening tests
- `tests/test_export/test_xlsx_export.py` — xlsx export tests
