# S05: CLI Integration & End-to-End — Research

**Date:** 2026-03-16

## Summary

S05 has already been executed. The CLI wiring (`main.py`), all 19 integration tests (`test_excel_analyze.py`), and the slice summary/plan/UAT artifacts already exist and are passing. This research retroactively documents the codebase state — confirming what was built, identifying residual quality gaps, and defining what cleanup remains for full milestone closure.

The primary requirement owned by S05 — R108 (Rich terminal output showing proposed FW rules) — is already validated by 4 CLI integration tests plus 2 end-to-end composition tests. The `analyze` command with `--source excel --file --export --template` options is fully functional.

Three residual gaps remain: (1) 9 pyright errors in `main.py` from TypedDict/dict type mismatches and a missing import, (2) no e2e test for the Excel pipeline path (only M01 VPC path has e2e tests), and (3) the REQUIREMENTS.md traceability table shows R103/R104/R105 as `active/unmapped` despite being crossed-out as validated in the Active section. These are all minor — no blocking issues.

## Recommendation

**No new implementation needed.** S05 is functionally complete. Remaining work is quality polish:

1. **Fix pyright errors in `main.py`** — Add `from policyfoundry.config.models import PolicyFoundryConfig` import and add `cast()` or explicit type annotations for the `_run()` async functions to resolve TypedDict ↔ dict mismatches. This brings `main.py` to zero new pyright errors (pre-existing errors from other modules are out of scope).
2. **Add Excel e2e test** — Mirror `tests/e2e/test_e2e_analyze.py` with an `test_e2e_excel_analyze.py` that uses real ingestion from a small fixture xlsx file through the pipeline with mock LLM. This proves the full composition path without mocking ingestion.
3. **Fix REQUIREMENTS.md traceability** — R103/R104/R105 headers say "Validated" but the traceability table still says `active/unmapped`. Align them.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI testing | `typer.testing.CliRunner` | Already established in 19 tests; captures exit code and stdout |
| Mock LLM boundary | `_excel_patches()` helper in test_excel_analyze.py | 4-patch context manager covering config, LLM, ingestion, pipeline |
| E2E test pattern | `tests/e2e/conftest.py` + `test_e2e_analyze.py` | Established pattern: real ingestion + mock LLM + real output formatting |
| Type narrowing | `typing.cast()` | Standard approach for TypedDict returns from LangGraph |

## Existing Code and Patterns

- `src/policyfoundry/main.py` — **Already complete.** `_run_excel_analyze()` composes ingest → pipeline → output → export. `_export_results()` handles comma-separated `--export` formats. Both `--export` and `--template` CLI options are wired. The only issue is 9 pyright type errors.
- `tests/test_cli/test_excel_analyze.py` — **19 tests, all passing.** 5 test classes: RichOutput (4), JsonOutput (3), Export (7), ErrorHandling (4), EndToEnd (2). Mocks at ingestion + pipeline boundary per D033.
- `tests/e2e/test_e2e_analyze.py` — **M01 VPC e2e pattern.** Uses real file ingestion → real Parquet → real DuckDB → mock LLM → real output. 12 tests. No Excel counterpart exists yet.
- `tests/e2e/conftest.py` — E2E fixture pattern: `e2e_data_dir` does real ingestion, `mock_e2e_llm_client` dispatches on `response_model` type, `mock_e2e_adapter` returns empty rules. Excel e2e would follow same pattern but with `ingest_excel_file` → `run_excel_pipeline`.
- `src/policyfoundry/output/excel_rich_output.py` — `format_excel_rich()` accepts `ExcelPipelineState` directly. Uses shared renderers from `rich_output.py` (D048).
- `src/policyfoundry/export/change_request.py` — `export_xlsx()` and `export_pdf()` both take `ExcelPipelineState` and `Path`. Template column matching via `COLUMN_MAP` dict.

## Constraints

- **D027: Typer async strategy** — Commands are sync with internal `asyncio.run()`. The `_run()` inner function returns `dict` which pyright can't resolve to `ExcelPipelineState` TypedDict without explicit annotation.
- **D033: CLI integration test mock boundary** — Mock LLMClient and pipeline runner; keep real config, ingestion, output. E2E tests should mock only LLM, not ingestion.
- **Pyright strict on src/ only (D001)** — Tests excluded from strict mode, so test pyright errors are not blocking.
- **Pre-existing 23 total pyright errors** — 9 are in `main.py` (addressable), 14 are in other modules (boto3 stubs, litellm exports, langgraph import — pre-existing from M01/S03). Only the 9 `main.py` errors are in-scope.

## Common Pitfalls

- **TypedDict from async return** — `asyncio.run(_run())` erases the TypedDict type info because the inner function's return annotation is `dict`. Fix: annotate `_run` return as `ExcelPipelineState` and cast at the call site.
- **Forward reference `PolicyFoundryConfig` in type annotation** — Line 119 uses `cfg: "PolicyFoundryConfig"` as a string forward reference but never imports the class. The lazy import pattern (inside function body) means pyright can't resolve it. Fix: add `TYPE_CHECKING` import.
- **E2E test fixture isolation** — Excel e2e tests should create a small xlsx fixture in `tests/fixtures/`, not use the 83K-row sample file (too slow for CI). The mock LLM needs `response_model` dispatch for Excel pipeline Pydantic types (same as M01 e2e pattern).

## Open Risks

- **No real LLM verification** — All testing uses mock LLM. The S05-UAT describes live testing with Ollama but this hasn't been executed. LLM prompt quality is unverified until a human runs the full pipeline against the sample file.
- **Performance with 83K-row file** — The integration tests use a 2-row fixture. No test proves the CLI handles the full 83,633-row sample file within reasonable time/memory.
- **REQUIREMENTS.md inconsistency** — R103/R104/R105 show conflicting status (header says Validated, traceability table says active/unmapped). If downstream tooling reads the table, it may incorrectly report unfulfilled requirements.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | no skill needed (well-established patterns in codebase) |
| Rich output | — | no skill needed (shared renderers from S03) |
| fpdf2 PDF | — | no skill needed (already integrated in S04) |
| openpyxl | — | no skill needed (already integrated in S01/S04) |
| LangGraph | — | no skill needed (pipeline built in S03) |

No new skills needed — S05 is pure wiring of existing modules with established test patterns.

## Sources

- Existing test suite: 605 tests passing (ignoring 2 pre-existing moto import failures)
- `tests/test_cli/test_excel_analyze.py`: 19 tests, all passing as of 2026-03-16
- `npx pyright src/policyfoundry/main.py`: 9 errors (TypedDict typing + missing import)
- S03-SUMMARY.md, S04-SUMMARY.md: Forward intelligence confirming boundary contracts
- S05-SUMMARY.md: Documents completed work and 19 test results
