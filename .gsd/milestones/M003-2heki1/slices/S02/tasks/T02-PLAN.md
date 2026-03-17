---
estimated_steps: 5
estimated_files: 4
---

# T02: Add console warnings on render failures and run full regression

**Slice:** S02 — Silent Failure Elimination
**Milestone:** M003-2heki1

## Description

The 8 bare `except Exception` blocks in `rich_output.py` (4 blocks) and `excel_rich_output.py` (4 blocks) each log via `logger.warning` but print nothing to the console. The user sees no indication that a section failed to render. This task adds a visible `[yellow]⚠ Failed to render {section}[/yellow]` Rich console print alongside each existing `logger.warning`, then verifies with targeted tests and a full regression run.

## Steps

1. Read `src/policyfoundry/output/rich_output.py`. Find the 4 `except Exception` blocks in `format_rich()` (traffic analysis ~L224, security assessment ~L233, proposals ~L243, decisions ~L253). In each block, add `console.print(f"[yellow]⚠ Failed to render {section_name}[/yellow]")` after the existing `logger.warning` call. The section names should match the content being rendered (e.g. "traffic analysis", "security assessment", "proposals", "decisions"). Ensure a `console` object is available — check if `Console` is already imported from `rich.console` and instantiated; if not, add it.

2. Read `src/policyfoundry/output/excel_rich_output.py`. Apply the same pattern to its 4 `except Exception` blocks in `format_excel_rich()` (~L113, ~L122, ~L132, ~L142). Use the same section names as the VPC equivalent sections. Ensure a `console` object is available.

3. Read `tests/test_output/test_rich_output.py`. Add test(s) that cause at least one section to fail during `format_rich()` — for example by injecting malformed data that causes the section rendering to raise an exception. Capture console output (using `io.StringIO` with Rich's `Console(file=...)` or by mocking the console object) and assert the warning text `"⚠ Failed to render"` appears. Verify that the function still returns output for the sections that didn't fail (graceful degradation).

4. Read `tests/test_output/test_excel_output.py`. Add equivalent test(s) for `format_excel_rich()` — inject bad data for at least one section, assert the console warning appears, and verify graceful degradation.

5. Run the full test suite: `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q`. Expect 636+ passed, 0 failed. This closes the slice.

## Must-Haves

- [ ] All 4 `except Exception` blocks in `rich_output.py` print visible console warning with section name
- [ ] All 4 `except Exception` blocks in `excel_rich_output.py` print visible console warning with section name
- [ ] Existing `logger.warning` calls are preserved (not replaced)
- [ ] Test proves console warning appears on render failure in `rich_output.py`
- [ ] Test proves console warning appears on render failure in `excel_rich_output.py`
- [ ] Full test suite passes: 636+ tests, 0 failures

## Verification

- `pytest tests/test_output/test_rich_output.py tests/test_output/test_excel_output.py -v` — console warning tests pass
- `pytest --ignore=tests/test_adapters/test_aws_sg_adapter.py --ignore=tests/test_ingestion/test_s3.py -q` — full suite 636+ passed, 0 failed

## Observability Impact

- Signals added: `[yellow]⚠ Failed to render {section}[/yellow]` Rich console output in 8 except blocks
- How a future agent inspects this: run the pipeline with malformed data and observe console output for `⚠` warnings
- Failure state exposed: render failures that were previously invisible now show section-specific warnings to the user

## Inputs

- `src/policyfoundry/output/rich_output.py` — 4 bare `except Exception` blocks that only log, never print
- `src/policyfoundry/output/excel_rich_output.py` — 4 bare `except Exception` blocks, same pattern
- `tests/test_output/conftest.py` — contains `sample_pipeline_state` fixtures
- T01 completed — export/adapter fixes are already in place

## Expected Output

- `src/policyfoundry/output/rich_output.py` — all 4 except blocks now print visible console warnings
- `src/policyfoundry/output/excel_rich_output.py` — all 4 except blocks now print visible console warnings
- `tests/test_output/test_rich_output.py` — new test(s) asserting console warning on render failure
- `tests/test_output/test_excel_output.py` — new test(s) asserting console warning on render failure
- Full test suite: 636+ passed, 0 failed
