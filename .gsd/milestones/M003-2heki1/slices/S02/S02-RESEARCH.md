# S02: Silent Failure Elimination — Research

**Date:** 2026-03-16

## Summary

S02 replaces four categories of silent failure with visible diagnostics: (1) template export silently returning on zero matching columns, (2) eight bare `except Exception` blocks in output renderers that log but never surface warnings to the user, (3) orphaned decisions silently dropped in export flattening, and (4) `ImportError` silently swallowed in adapter registry. All four are mechanical fixes in well-understood files with existing test infrastructure. No new technology, no risky integrations.

The S01 Forward Intelligence confirms no overlap — S01 fixed bare `except` blocks in pipeline stage functions; S02's targets are all in output/export/adapter code.

## Recommendation

Four independent tasks, one per issue category. Each is a small edit + targeted test(s). Build order doesn't matter — they touch different files with no interdependencies. Template export error (#1) is the highest-value fix since it's user-facing deception (success message on empty output). The `except Exception` blocks (#2) are the largest by file count but are a simple pattern change across two files.

## Implementation Landscape

### Key Files

- `src/policyfoundry/export/change_request.py` — `_fill_template()` at line ~157: `if not col_mapping: return` silently does nothing when template has no recognized columns. Must raise `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"`.

- `src/policyfoundry/output/rich_output.py` — `format_rich()` has 4 bare `except Exception:` blocks (lines 224, 233, 243, 253) for traffic analysis, security assessment, proposals, and decisions sections. Each logs `logger.warning` but prints nothing to the console. Must also print a visible `[yellow]⚠ Failed to render {section}[/yellow]` warning via the Rich console so the user sees it.

- `src/policyfoundry/output/excel_rich_output.py` — `format_excel_rich()` has 4 identical bare `except Exception:` blocks (lines 113, 122, 132, 142). Same fix as `rich_output.py` — add console warning alongside existing logger.warning.

- `src/policyfoundry/export/models.py` — `flatten_to_entries()` at line ~100: `if proposal is None: continue` silently drops decisions referencing missing proposals. Must add `logger.warning(f"Orphaned decision {decision.decision_id}: proposal {decision.proposal_id} not found")` before continue.

- `src/policyfoundry/adapters/registry.py` — `get_adapter()` at line ~35: `except ImportError: pass` silently swallows failure to import `aws_sg` adapter. Must add `logger.warning("Failed to import aws_sg adapter", exc_info=True)` before pass.

- `src/policyfoundry/exceptions.py` — Already has `ExportError` and `OutputError`. No changes needed.

### Existing Test Files

- `tests/test_export/test_xlsx_export.py` — Has `TestTemplateExport` and `TestExportErrors` classes. Add test for no-matching-columns raising `ExportError`.
- `tests/test_output/test_rich_output.py` — Has `TestFormatRichEmptyState`. Add test proving render failure surfaces console warning text.
- `tests/test_output/test_excel_output.py` — Has `TestFormatExcelRichEmptyState`. Add test proving render failure surfaces console warning text.
- `tests/test_adapters/test_registry.py` — Has `TestAdapterRegistry` with mock entry_points. Add test proving `ImportError` is logged.
- `tests/test_export/` — Need a test file or additions for orphaned decision logging. Could add to existing export test fixtures or a new small test.

### Test Fixtures

- `tests/test_export/conftest.py` — Contains `sample_excel_state` and `sample_excel_state_empty` fixtures used by xlsx export tests.
- `tests/test_output/conftest.py` — Contains `sample_pipeline_state` fixtures for rich output tests.

### Build Order

All four changes are independent — no ordering constraint. Suggested grouping by natural task boundaries:

1. **Template no-match → ExportError** (change_request.py + test) — highest user value, simplest change.
2. **Orphaned decisions logging** (export/models.py + test) — small, isolated.
3. **Adapter ImportError logging** (registry.py + test) — small, isolated.
4. **Console warnings on render failures** (rich_output.py + excel_rich_output.py + tests) — largest by file count but same pattern repeated 8 times.

### Verification Approach

- Each fix gets at least one targeted test proving the diagnostic surfaces.
- Template test: `pytest.raises(ExportError)` with a template containing only unrecognized column headers.
- Render warning tests: Inject bad data that fails `model_validate()`, capture console output, assert warning text appears.
- Orphaned decision test: Create state with a decision referencing a nonexistent proposal_id, assert `logger.warning` is called.
- ImportError test: Mock `importlib` to raise `ImportError`, assert `logger.warning` is called before `AdapterNotFoundError`.
- Full suite regression: `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — expect 636+ passed.

## Constraints

- The 8 `except Exception` blocks must keep their `logger.warning` calls — they provide exc_info for debugging. The console warning is additive, not a replacement.
- `_fill_template` is called inside `export_xlsx` which has its own `except ExportError: raise` pass-through — the new `ExportError` will propagate correctly through the existing error handling chain.
- Orphaned decision logging must not change the return value of `flatten_to_entries` — it still skips the orphan, it just logs first.
- The adapter registry `ImportError` path is a fallback for dev environments when entry points aren't installed. The warning should not be alarming — it's informational. The code still falls through to `AdapterNotFoundError` if it was the last option.
