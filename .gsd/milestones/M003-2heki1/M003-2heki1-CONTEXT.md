# M003-2heki1: PR Review Bug Fixes

**Gathered:** 2026-03-17
**Status:** Ready for planning

## Project Description

PolicyFoundry is an AI-powered firewall policy management CLI. M001 built the VPC Flow Log pipeline; M002 added Excel traffic analysis and change request form export. A thorough PR review of M002 identified 14 issues (4 critical + 10 important) spanning silent failures, prompt factual errors, wrong stage reporting, missing token tracking, type safety gaps, and data integrity bugs. This milestone fixes all 14 before adding new capability.

## Why This Milestone

The M002 code works in the happy path but has correctness and observability gaps that will compound with future development. A prompt that references nonexistent field names (`counterpart_ip`) causes LLM hallucination. Pipeline errors always report stage `"starting"` regardless of where they fail. Eight bare `except Exception` blocks silently swallow render errors. Template export with no matching columns silently produces empty files with success messages. These must be fixed before M004 adds secrets management on top.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `policyfoundry analyze --source excel --file traffic.xlsx` and see accurate per-stage token usage in the output footer
- See a clear error when providing a template with no matching columns (instead of a silent empty file)
- Get meaningful stage identification in error messages when the pipeline fails
- Trust that the LLM receives accurate data model descriptions in its prompts

### Entry point / environment

- Entry point: `policyfoundry` CLI
- Environment: local dev
- Live dependencies involved: none (all fixes are testable with mocks)

## Completion Class

- Contract complete means: all 14 issues have targeted tests proving the fix; full test suite passes (623+ tests)
- Integration complete means: none required — all fixes are internal correctness
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Full test suite passes with zero regressions
- Each of the 14 PR review issues has at least one test covering the specific failure mode
- `pytest` runs clean with no warnings related to the fixed areas

## Risks and Unknowns

- Subnet dedup logic (#13) is subtle — the `break`/`else: continue` pattern needs careful analysis to avoid changing correct behavior while fixing the bug
- Changing `RuleDecision.action` from bare `str` to enum (#10) could break existing tests or serialization boundaries

## Existing Codebase / Prior Art

- `src/policyfoundry/pipeline/excel_runner.py` — error handler reads `initial_state` instead of evolved state (#4)
- `src/policyfoundry/pipeline/excel_prompts/generate.py` — prompt references `counterpart_ip` instead of `dst_ip`/`src_ip` (#3)
- `src/policyfoundry/pipeline/excel_stages/*.py` — all 4 stages omit `stage=` parameter (#6)
- `src/policyfoundry/pipeline/stages/*.py` — all 4 VPC stages also omit `stage=` parameter (#6)
- `src/policyfoundry/output/rich_output.py` — 4 bare `except Exception` blocks (#2)
- `src/policyfoundry/output/excel_rich_output.py` — 4 bare `except Exception` blocks (#2)
- `src/policyfoundry/export/change_request.py` — silent return on template with no matching columns (#1)
- `src/policyfoundry/export/models.py` — orphaned decisions silently dropped (#5)
- `src/policyfoundry/adapters/registry.py` — `ImportError` swallowed with `pass` (#8)
- `src/policyfoundry/pipeline/excel_stages/validate.py` — rejected proposals dropped with no logging (#9)
- `src/policyfoundry/pipeline/schema.py` — `RuleDecision.action` is bare `str` (#10)
- `src/policyfoundry/analysis/models.py` — `SubnetGroup.member_count` no consistency validator (#11)
- `src/policyfoundry/output/models.py` — `dict[str, Any](usage_raw)` construction (#12)
- `src/policyfoundry/analysis/subnet.py` — dedup logic incorrectly drops groups (#13)
- `src/policyfoundry/main.py` — docstring lists 6 stages but pipeline has 5 (#14)

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R401 — No silent failures in output rendering or export
- R402 — LLM prompts reference correct data model field names
- R403 — Pipeline errors report the actual failing stage
- R404 — Token usage tracks per-stage metrics for all LLM calls
- R405 — Dropped/rejected data is logged, not silently discarded
- R406 — Type safety for control-flow fields and model consistency
- R407 — Code correctness in subnet dedup and construction patterns

## Scope

### In Scope

- Fix all 4 critical PR review issues (#1, #2, #3, #4)
- Fix all 10 important PR review issues (#5–#14)
- Add targeted tests for each fix
- Maintain full backward compatibility

### Out of Scope / Non-Goals

- PR review suggestions (#15–#26) — test gaps, computed properties, type dedup
- Refactoring beyond what's needed to fix the specific issues
- New features or capabilities

## Technical Constraints

- Fixes must not change public API surface or CLI behavior
- `RuleDecision.action` enum change must preserve serialization compatibility (LLM outputs `"CREATE"`, `"SKIP"` as strings)
- All existing 623 tests must continue to pass

## Integration Points

- None — all fixes are internal correctness

## Open Questions

- None remaining — all issues are well-specified in the PR review doc
