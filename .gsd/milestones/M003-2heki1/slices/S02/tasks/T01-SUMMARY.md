---
id: T01
parent: S02
milestone: M003-2heki1
provides:
  - ExportError on template with no matching columns
  - Warning log on orphaned decisions with decision_id/proposal_id context
  - Warning log with exc_info on adapter ImportError
key_files:
  - src/policyfoundry/export/change_request.py
  - src/policyfoundry/export/models.py
  - src/policyfoundry/adapters/registry.py
  - tests/test_export/test_xlsx_export.py
  - tests/test_export/test_export_models.py
  - tests/test_adapters/test_registry.py
key_decisions:
  - Used %-style logger formatting (not f-strings) for orphaned decision warning to avoid string interpolation when logging is disabled
patterns_established:
  - Module-level logger via logging.getLogger(__name__) in export/models.py and adapters/registry.py
observability_surfaces:
  - logger.warning "Orphaned decision {id}: proposal {id} not found" in policyfoundry.export.models
  - logger.warning "Failed to import adapter module" with exc_info=True in policyfoundry.adapters.registry
  - ExportError with error_code="TEMPLATE_NO_MATCHING_COLUMNS" propagates through existing error chain
duration: ~8 min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Raise ExportError on empty template match, log orphaned decisions and adapter ImportError

**Replaced three silent failures with explicit error/warning signals across export and adapter registry.**

## What Happened

Three independent one-line silent-failure sites were fixed:

1. `_fill_template()` in `change_request.py` had `if not col_mapping: return` — silently did nothing when a template had no recognized columns. Replaced with `raise ExportError(...)` using error_code `TEMPLATE_NO_MATCHING_COLUMNS`. The existing `export_xlsx` error handling already re-raises `ExportError` subclasses, so this propagates naturally.

2. `flatten_to_entries()` in `models.py` had a bare `continue` when a decision referenced a missing proposal. Added `logger.warning` with both `decision_id` and `proposal_id` before the continue. Added `import logging` and module-level `logger`.

3. `get_adapter()` in `registry.py` had `except ImportError: pass` on the aws_sg fallback import. Added `logger.warning("Failed to import adapter module", exc_info=True)` before `pass` so the traceback is captured. Added `import logging` and module-level `logger`.

## Verification

- `pytest tests/test_export/test_xlsx_export.py -v` — 12 passed including new `test_template_no_matching_columns`
- `pytest tests/test_export/test_export_models.py -v` — 1 passed (`test_orphaned_decision_logs_warning`)
- `pytest tests/test_adapters/test_registry.py -v` — 7 passed including new `test_get_adapter_logs_import_error`
- Full regression: `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — 639 passed

## Diagnostics

- **Template error:** Catch `ExportError` with `error_code == "TEMPLATE_NO_MATCHING_COLUMNS"` in calling code
- **Orphaned decisions:** `grep` logs for `"Orphaned decision"` — message contains both IDs
- **Adapter import:** `grep` logs for `"Failed to import adapter module"` — full traceback via exc_info

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/policyfoundry/export/change_request.py` — `_fill_template()` raises ExportError instead of silent return
- `src/policyfoundry/export/models.py` — Added logger, warning on orphaned decisions in `flatten_to_entries()`
- `src/policyfoundry/adapters/registry.py` — Added logger, warning with exc_info on ImportError in `get_adapter()`
- `tests/test_export/test_xlsx_export.py` — Added `test_template_no_matching_columns` to `TestExportErrors`
- `tests/test_export/test_export_models.py` — New file with `TestOrphanedDecisionLogging`
- `tests/test_adapters/test_registry.py` — Added `test_get_adapter_logs_import_error` to `TestAdapterRegistry`
