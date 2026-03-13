---
id: T01
parent: S05
milestone: M001
provides:
  - Enriched UniversalRule with NetworkEndpoint source/destination
  - FirewallAdapter ABC (get_rules, validate, capabilities)
  - AdapterRegistry with entry_points plugin discovery
  - ValidationResult, ValidationIssue, AdapterCapabilities models
  - AdapterAuthenticationError, AdapterValidationError, AdapterNotFoundError exceptions
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 5min
verification_result: passed
completed_at: 2026-03-10
blocker_discovered: false
---
# T01: 05-firewall-adapter 01

**# Phase 5 Plan 01: Adapter Contracts Summary**

## What Happened

# Phase 5 Plan 01: Adapter Contracts Summary

**Enriched UniversalRule with NetworkEndpoint, FirewallAdapter ABC with 3 abstract methods, and AdapterRegistry with entry-point plugin discovery**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T15:46:59Z
- **Completed:** 2026-03-10T15:52:12Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Enriched UniversalRule schema: NetworkEndpoint replaces plain string CIDRs, RuleAction has 4 values (ALLOW/DENY/DROP/REJECT), zone and tags fields added, risk_level removed
- FirewallAdapter ABC defines read+validate contract with async get_rules(), async validate(), and sync capabilities()
- AdapterRegistry discovers adapters via setuptools entry_points with aws_sg direct-import fallback for development
- Full adapter test infrastructure: 26 adapter-specific tests + updated existing model tests (all 197 tests pass)
- Exception subclasses: AdapterAuthenticationError, AdapterValidationError, AdapterNotFoundError

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 RED: Enriched schema tests** - `bbfdc2f` (test)
2. **Task 1 GREEN: Enrich schema models** - `888b501` (feat)
3. **Task 2 RED: Registry/ABC tests** - `c5c7c2e` (test)
4. **Task 2 GREEN: FirewallAdapter ABC, AdapterRegistry, entry-points** - `f2d080a` (feat)

## Files Created/Modified
- `src/policyfoundry/adapters/schema.py` - Enriched with NetworkEndpoint, ValidationIssue, ValidationResult, AdapterCapabilities; 4-value RuleAction; removed risk_level from UniversalRule
- `src/policyfoundry/adapters/base.py` - FirewallAdapter ABC with 3 abstract methods
- `src/policyfoundry/adapters/registry.py` - AdapterRegistry with entry_points discovery and aws_sg fallback
- `src/policyfoundry/adapters/__init__.py` - Public exports for all adapter types
- `src/policyfoundry/exceptions.py` - AdapterAuthenticationError, AdapterValidationError, AdapterNotFoundError
- `pyproject.toml` - Entry-point registration for policyfoundry.adapters group
- `tests/test_adapters/test_schema.py` - Tests for NetworkEndpoint, ValidationResult, AdapterCapabilities, enriched UniversalRule
- `tests/test_adapters/test_registry.py` - Tests for AdapterRegistry discovery, fallback, error handling
- `tests/test_adapters/conftest.py` - Shared adapter test fixtures
- `tests/conftest.py` - Updated valid_universal_rule_data fixture for new schema shape
- `tests/test_models/test_universal_rule.py` - Updated for 4-value RuleAction, NetworkEndpoint source/destination, removed risk_level tests

## Decisions Made
- Used bare `[]` and `{}` defaults instead of `Field(default_factory=list/dict)` for pyright strict mode compatibility -- Pydantic v2 handles mutable defaults correctly
- Added `pyright: ignore[reportUnknownVariableType]` for AwsSecurityGroupAdapter import in registry fallback since the aws_sg module is created in Plan 02
- NetworkEndpoint uses `model_validator(mode="after")` for the at-least-one-identifier constraint rather than a root_validator or pre-validator

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pyright strict mode errors for Pydantic list/dict defaults**
- **Found during:** Task 2 (pyright verification step)
- **Issue:** `Field(default_factory=list)` produced `list[Unknown]` type in pyright strict mode
- **Fix:** Changed to bare `[]` and `{}` defaults which Pydantic v2 deep-copies correctly
- **Files modified:** src/policyfoundry/adapters/schema.py
- **Verification:** `uv run pyright src/policyfoundry/adapters/` passes with 0 errors
- **Committed in:** f2d080a (Task 2 commit)

**2. [Rule 1 - Bug] Fixed line-too-long in NetworkEndpoint validator**
- **Found during:** Task 2 (ruff check)
- **Issue:** model_validator condition and error message exceeded 88-char line limit
- **Fix:** Refactored to multi-line boolean expression and parenthesized string
- **Files modified:** src/policyfoundry/adapters/schema.py
- **Verification:** `uv run ruff check` passes
- **Committed in:** f2d080a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for CI compliance (pyright strict, ruff line-length). No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FirewallAdapter ABC and schema contracts are ready for Plan 02 (AWS SG adapter) to implement against
- AdapterRegistry will discover the aws_sg adapter once Plan 02 creates the module
- Entry-point registration already in pyproject.toml pointing to the future aws_sg module path

## Self-Check: PASSED

All 12 files verified present. All 4 task commits verified in git log.

---
*Phase: 05-firewall-adapter*
*Completed: 2026-03-10*
