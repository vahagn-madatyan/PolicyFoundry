# S04: Change Request Form Export — Research

**Date:** 2026-03-15

## Summary

S04 delivers three requirements: R109 (xlsx export), R110 (pdf export), R111 (custom template support). The boundary contract is clean — `ExcelPipelineState` from S03 carries `decisions` and `proposals` dicts that flatten into `ChangeRequestEntry` rows for both export formats.

**xlsx** uses openpyxl (already in deps). Default template is a styled workbook created programmatically; custom template support loads a user's .xlsx and fills rows starting after detected headers. **pdf** uses fpdf2 (new dependency, pure Python, zero system deps). Its `table()` context manager with `FontFace` heading styles produces professional tabular output with minimal code. No system libraries (Cairo/Pango) required — unlike weasyprint which would be a non-starter for a CLI tool.

The main design work is the `ChangeRequestEntry` flattening model and the template-fill strategy for custom xlsx files. Both are well-constrained by the data shapes already in the codebase.

## Recommendation

Use **fpdf2** for PDF generation. It's pure Python, has excellent table support via `table()` context manager with `FontFace` styling, handles page breaks automatically, and weighs ~1MB with no native dependencies. reportlab is more powerful but overkill — we're generating structured forms, not magazine layouts. weasyprint requires Cairo/Pango system libraries which breaks the "pip install and run" story.

Create an `export/` package with:
- `models.py` — `ChangeRequestEntry` Pydantic model (flattened from proposal + decision)
- `change_request.py` — `export_xlsx()` and `export_pdf()` functions
- `templates/default.xlsx` — built-in template generated at first call or shipped as a static asset

Add `ExportError(PolicyFoundryError)` to the exception hierarchy for export-specific failures.

Include a metadata header section in both formats: date generated, pipeline run_id, source description, total rules. Auto-populated from pipeline state — no user input needed for defaults.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Excel creation/styling | openpyxl (already in deps v3.1.5) | Column widths, fonts, fills, borders — all working. Already used in ingestion. |
| PDF creation with tables | fpdf2 (`pip install fpdf2`) | Pure Python, `table()` context manager, `FontFace` for styled headers, auto page breaks. ~1MB, no system deps. |
| Pipeline result typing | `ExcelPipelineResult.from_state()` | Reconstructs typed `PolicyProposal` and `RuleDecision` models from state dicts. Already tested. |
| Error handling | `PolicyFoundryError` hierarchy | Add `ExportError` subclass following established pattern. |

## Existing Code and Patterns

- `src/policyfoundry/output/models.py` — `ExcelPipelineResult.from_state()` reconstructs typed `PolicyProposal`/`RuleDecision` from state dicts. Use this to get clean typed data before flattening to `ChangeRequestEntry`.
- `src/policyfoundry/pipeline/schema.py` — `PolicyProposal` has `.rule` (UniversalRule with source, dest, port_range, protocol, direction), `.justification`, `.risk_level`, `.confidence`. `RuleDecision` has `.action`, `.risk_level`, `.reason`, `.approval_required`.
- `src/policyfoundry/adapters/schema.py` — `UniversalRule` source/dest are `list[NetworkEndpoint]` where each has `.cidr`, `.security_group_id`, `.tag`, `.is_any`. Flattening: join CIDRs with commas, fall back to "any" for `is_any=True`.
- `src/policyfoundry/pipeline/excel_state.py` — `ExcelPipelineState` TypedDict. Key fields for S04: `decisions` (list[dict]), `proposals` (list[dict]), `run_id`, `started_at`.
- `src/policyfoundry/exceptions.py` — Established hierarchy. `OutputError` exists for formatting. Add `ExportError` for file-writing failures (distinct concern from in-memory formatting).
- `src/policyfoundry/ingestion/excel.py` — openpyxl usage pattern: read_only mode for input. For export we'll use normal mode (write).
- `tests/test_output/conftest.py` + `test_excel_output.py` — `sample_excel_state` fixture has realistic data with proposals and decisions. Reuse or extend for export tests.

## Constraints

- **openpyxl is already a dependency** (v3.1.5). No new dep needed for xlsx export.
- **fpdf2 must be added** to `[project.dependencies]` in pyproject.toml. Pure Python — no system library installation.
- **Template detection for custom xlsx**: Must handle arbitrary user templates. Strategy: scan first sheet's row 1 for header-like text, match known column names (case-insensitive), insert data rows below. If no recognizable headers found, fall back to first empty row.
- **NetworkEndpoint flattening**: source/dest are `list[NetworkEndpoint]`. Must join into readable strings: `"10.0.1.0/24, 10.0.2.0/24"` for CIDRs, `"any"` for `is_any=True`, sg-id or tag string for others.
- **Port range display**: `PortRange(from_port=443, to_port=443)` → `"443"`, `PortRange(from_port=80, to_port=90)` → `"80-90"`, `None` → `"any"`.
- **Pyright strict on src/**: All new code under `src/policyfoundry/export/` must pass pyright strict (D001).
- **No `export/` directory exists yet** — full package creation needed (\_\_init\_\_.py, models.py, change_request.py, templates/).

## Common Pitfalls

- **openpyxl styles are not shared between cells** — Each cell needs its own Font/PatternFill instance. Don't create one Font and assign it to multiple cells expecting shared mutation; create helper functions that return fresh style objects per call.
- **fpdf2 font availability** — Only Helvetica, Times, Courier built-in. Don't attempt custom fonts without embedding TTF files. Built-in fonts are sufficient for a professional form.
- **Large rule sets and PDF page breaks** — fpdf2's `table()` handles page breaks automatically, but the metadata header should only appear on page 1. Use `header()` override for page number footer, not for the form header.
- **Custom template column ordering** — User templates may have columns in any order. The fill logic must map ChangeRequestEntry fields to detected column positions, not assume fixed column order.
- **Empty proposals/decisions** — Pipeline could produce zero decisions (all filtered). Export functions must handle empty rule lists gracefully (generate file with metadata header only, no data rows).

## Open Risks

- **Custom template reliability**: Real-world templates may have merged cells, logos, multiple header rows, or protection. The "scan row 1 for headers" strategy handles simple templates but could fail on complex ones. Mitigation: document template requirements (single header row with recognized column names, no merged cells in the data area). Fall back with a clear error message.
- **fpdf2 font rendering on different OS**: Built-in fonts should work everywhere, but if users need non-Latin characters in justification text, fpdf2's built-in fonts won't cover it. This is an edge case — most firewall justifications are English. Note as a known limitation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| openpyxl/xlsx | claude-office-skills/skills@xlsx-manipulation (179 installs) | available — not installed (low complexity, Context7 docs sufficient) |
| fpdf2/PDF | jwynia/agent-skills@pdf-generator (222 installs) | available — not installed (generic skill, fpdf2 Context7 docs have exact table API we need) |

## Sources

- fpdf2 table API with `FontFace` styling, `col_widths`, `borders_layout`, `cell_fill_color` (source: Context7 /py-pdf/fpdf2 docs)
- fpdf2 `write_html()` for HTML-to-PDF if needed as fallback (source: Context7 /py-pdf/fpdf2 docs)
- reportlab Platypus `SimpleDocTemplate` with Table styling (source: Context7 /websites/reportlab docs) — evaluated but rejected in favor of fpdf2
- openpyxl styling (Font, PatternFill, Alignment, Border) confirmed working via runtime test
- openpyxl `load_workbook()` for template fill confirmed via runtime test
- ExcelPipelineState boundary contract and field shapes confirmed from `excel_state.py` and `models.py`
