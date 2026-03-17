---
estimated_steps: 6
estimated_files: 6
---

# T01: Raise ExportError on empty template match, log orphaned decisions and adapter ImportError

**Slice:** S02 — Silent Failure Elimination
**Milestone:** M003-2heki1

## Description

Three independent silent-failure fixes combined into one task because each touches one source file and one test file with minimal code change. Covers: (1) template export silently returning when no columns match — must raise `ExportError`, (2) orphaned decisions silently dropped during export flattening — must log with context, (3) adapter `ImportError` silently swallowed — must log with exc_info.

## Steps

1. Read `src/policyfoundry/export/change_request.py` and find `_fill_template()`. Replace the `if not col_mapping: return` early return with `raise ExportError("Template contains no recognized columns", error_code="TEMPLATE_NO_MATCHING_COLUMNS")`. Ensure `ExportError` is imported from `policyfoundry.exceptions`.

2. Read `src/policyfoundry/export/models.py` and find `flatten_to_entries()`. Before the `continue` in the `if proposal is None:` block, add `logger.warning(f"Orphaned decision {decision.decision_id}: proposal {decision.proposal_id} not found")`. Ensure `logger` is defined at module level (`logger = logging.getLogger(__name__)`), adding the import if needed.

3. Read `src/policyfoundry/adapters/registry.py` and find `get_adapter()`. In the `except ImportError: pass` block, add `logger.warning("Failed to import adapter module", exc_info=True)` before `pass`. Ensure `logger` is defined at module level.

4. Read `tests/test_export/test_xlsx_export.py` and add a test to the `TestExportErrors` or `TestTemplateExport` class that creates a template with only unrecognized column headers (e.g. `"FakeCol1"`, `"FakeCol2"`), calls the export function, and asserts `ExportError` is raised with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"`. Use existing fixtures (`sample_excel_state` from conftest) and patterns from neighboring tests.

5. Add a test for orphaned decision logging. This may go in an existing test file under `tests/test_export/` or a new `tests/test_export/test_export_models.py`. Create a pipeline state with a decision whose `proposal_id` references a nonexistent proposal. Call `flatten_to_entries()` and assert `logger.warning` was called with a message containing the decision_id and proposal_id. Use `unittest.mock.patch` on the logger.

6. Read `tests/test_adapters/test_registry.py` and add a test that mocks `importlib.import_module` (or the relevant import mechanism) to raise `ImportError`, calls `get_adapter()`, and asserts `logger.warning` was called with `exc_info=True`. The function should still raise `AdapterNotFoundError` after the warning.

## Must-Haves

- [ ] `_fill_template()` raises `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"` when `col_mapping` is empty
- [ ] `flatten_to_entries()` logs warning with decision_id and proposal_id before skipping orphaned decisions
- [ ] `get_adapter()` logs warning with exc_info on `ImportError` before continuing
- [ ] Test proves `ExportError` is raised on template with no recognized columns
- [ ] Test proves orphaned decision warning is logged
- [ ] Test proves adapter `ImportError` warning is logged

## Verification

- `pytest tests/test_export/test_xlsx_export.py -v` — template error test passes
- `pytest tests/test_export/test_export_models.py -v` — orphaned decision test passes (create file if needed)
- `pytest tests/test_adapters/test_registry.py -v` — adapter ImportError test passes
- No regressions in related test files

## Observability Impact

- Signals added: `logger.warning` on orphaned decisions (with decision_id, proposal_id context), `logger.warning` with exc_info on adapter ImportError
- How a future agent inspects this: grep logs for "Orphaned decision" or "Failed to import adapter module"
- Failure state exposed: `ExportError` with `error_code="TEMPLATE_NO_MATCHING_COLUMNS"` propagates through existing error handling chain in `export_xlsx`

## Inputs

- `src/policyfoundry/export/change_request.py` — contains `_fill_template()` with silent `return` on empty `col_mapping`
- `src/policyfoundry/export/models.py` — contains `flatten_to_entries()` with silent `continue` on missing proposal
- `src/policyfoundry/adapters/registry.py` — contains `get_adapter()` with silent `except ImportError: pass`
- `src/policyfoundry/exceptions.py` — already defines `ExportError` (no changes needed)
- `tests/test_export/conftest.py` — contains `sample_excel_state` and `sample_excel_state_empty` fixtures
- `tests/test_adapters/test_registry.py` — contains `TestAdapterRegistry` with mock entry_points pattern

## Expected Output

- `src/policyfoundry/export/change_request.py` — `_fill_template()` raises `ExportError` instead of silent return
- `src/policyfoundry/export/models.py` — `flatten_to_entries()` logs orphaned decision warning before continue
- `src/policyfoundry/adapters/registry.py` — `get_adapter()` logs ImportError warning before pass
- `tests/test_export/test_xlsx_export.py` — new test for template no-match error
- `tests/test_export/test_export_models.py` — new test for orphaned decision logging (new file if needed)
- `tests/test_adapters/test_registry.py` — new test for adapter ImportError logging
