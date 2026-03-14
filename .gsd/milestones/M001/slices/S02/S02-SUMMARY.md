---
id: S02
parent: M001
milestone: M001
provides:
  - "PolicyFoundryConfig root settings model with YAML + env var merge"
  - "LLMConfig, SourcesConfig, TargetsConfig, OutputConfig nested models"
  - "load_config() entry point with validation error handling"
  - "Comma-separated env var list parsing via NoDecode + field_validator"
  - "Unknown key detection with 'did you mean?' fuzzy suggestions via difflib"
  - "CONFIG_TEMPLATE for policyfoundry init command"
  - "ConfigSource enum and AnnotatedValue dataclass for source provenance"
  - "resolve_with_annotations() for policyfoundry config show command"
  - "warn_unknown_keys() integrated into config loader"
requires: []
affects: []
key_files: []
key_decisions:
  - "Used NoDecode + field_validator for comma-separated lists instead of JSON env var parsing"
  - "Nested models use BaseModel (not BaseSettings) -- only root PolicyFoundryConfig is BaseSettings"
  - "YAML sources only added to priority chain if file exists on disk (no FileNotFoundError)"
  - "Used cast() for pyright strict compliance on yaml.safe_load and model_dump output types"
  - "Extracted _build_warning helper to keep line lengths under 88 chars"
  - "resolve_with_annotations loads each source layer independently for source comparison"
patterns_established:
  - "Config test isolation: monkeypatch Path.home() and Path.cwd() to control YAML discovery"
  - "clean_env autouse fixture removes all POLICYFOUNDRY_ env vars before each test"
  - "type: ignore[misc] for Annotated[list[str], NoDecode] per Phase 1 pyright precedent"
  - "cast('dict[str, object]', ...) for yaml.safe_load output in pyright strict mode"
  - "Fuzzy match cutoff 0.6 for config key suggestions"
observability_surfaces: []
drill_down_paths: []
duration: 4min
verification_result: passed
completed_at: 2026-03-08
blocker_discovered: false
---
# S02: Configuration System

**# Phase 2 Plan 1: Config Models and Loader Summary**

## What Happened

# Phase 2 Plan 1: Config Models and Loader Summary

**Pydantic Settings config system with YAML file loading, env var overrides, and 4-layer merge priority chain (global YAML < local YAML < env vars < init kwargs)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T17:45:47Z
- **Completed:** 2026-03-08T17:49:07Z
- **Tasks:** 2 (TDD, 4 commits total)
- **Files modified:** 8

## Accomplishments
- Pydantic Settings models for LLM, sources, targets, and output configuration with sensible defaults (ollama, llama3.2, rich output)
- Config loader with 4-layer merge priority: global YAML < local YAML < env vars < init kwargs
- Comma-separated env var list parsing for security_group_ids and log_paths
- ConfigValidationError integration with field name extraction from Pydantic errors
- 22 config tests + 48 Phase 1 tests all passing (70 total)

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Config models with TDD tests**
   - `7b2d882` (test) - add failing tests for config models
   - `f363cb7` (feat) - implement config models with pydantic-settings

2. **Task 2: Config loader with source priority and TDD tests**
   - `50cba8d` (test) - add failing tests for config loader
   - `a4e1ecb` (feat) - implement config loader with source priority chain

## Files Created/Modified
- `src/policyfoundry/config/models.py` - Pydantic Settings models: LLMConfig, SourcesConfig, TargetsConfig, OutputConfig, PolicyFoundryConfig
- `src/policyfoundry/config/loader.py` - load_config() with ValidationError-to-ConfigValidationError wrapping
- `src/policyfoundry/config/__init__.py` - Public API re-exports for all models and load_config
- `tests/test_config/__init__.py` - Test package init
- `tests/test_config/conftest.py` - Shared fixtures: clean_env, tmp_config_dir, sample_yaml_content
- `tests/test_config/test_models.py` - 12 tests covering model defaults, custom values, comma-separated parsing
- `tests/test_config/test_loader.py` - 10 tests covering YAML loading, env overrides, merge priority, validation errors
- `pyproject.toml` - Added pydantic-settings[yaml]>=2.13 dependency

## Decisions Made
- Used NoDecode + field_validator for comma-separated lists -- this is the pydantic-settings native pattern, avoids requiring JSON syntax in env vars
- Nested models (LLMConfig, SourcesConfig, etc.) inherit from BaseModel not BaseSettings -- only the root PolicyFoundryConfig needs settings machinery
- YAML sources are conditionally added to the priority chain only if the file exists on disk -- avoids FileNotFoundError and matches user expectation that missing config files use defaults

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Config models and loader ready for Plan 02-02 (unknown key detection, config template, source annotations)
- All downstream phases (LLM integration, CLI) can import load_config() and PolicyFoundryConfig
- Test fixtures established for config isolation (clean_env, monkeypatch Path.home/cwd)

## Self-Check: PASSED

- All 8 created files exist on disk
- All 4 task commits verified (7b2d882, f363cb7, 50cba8d, a4e1ecb)
- 70 tests passing (22 config + 48 Phase 1)
- ruff: clean
- pyright: clean

---
*Phase: 02-configuration-system*
*Completed: 2026-03-08*

# Phase 2 Plan 2: Unknown Key Detection, Config Template, and Source Annotations Summary

**Unknown key detection with difflib fuzzy suggestions, YAML config template for init, and source annotation utilities for config show**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T17:51:48Z
- **Completed:** 2026-03-08T17:56:05Z
- **Tasks:** 2 (1 TDD with 2 commits, 1 standard with 1 commit)
- **Files modified:** 5

## Accomplishments
- Unknown YAML config keys produce "did you mean?" warnings using difflib.get_close_matches with 0.6 cutoff
- Unknown keys do NOT block config loading -- valid config values are still applied
- CONFIG_TEMPLATE provides a fully commented YAML template for policyfoundry init command
- ConfigSource enum and resolve_with_annotations() enable source provenance for config show
- All 77 tests passing (29 config + 48 Phase 1), ruff clean, pyright clean

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Unknown key detection with TDD tests**
   - `355bc4d` (test) - add failing tests for unknown key detection
   - `8dcb053` (feat) - implement unknown key detection with fuzzy suggestions

2. **Task 2: Config template and source annotation utilities**
   - `f08f80a` (feat) - add config template and source annotation utilities

## Files Created/Modified
- `src/policyfoundry/config/validation.py` - KNOWN_KEYS registry, warn_unknown_keys() with difflib fuzzy matching
- `src/policyfoundry/config/defaults.py` - CONFIG_TEMPLATE, ConfigSource enum, AnnotatedValue dataclass, resolve_with_annotations()
- `src/policyfoundry/config/loader.py` - Integrated warn_unknown_keys() call before config loading
- `src/policyfoundry/config/__init__.py` - Added exports: warn_unknown_keys, CONFIG_TEMPLATE, ConfigSource, AnnotatedValue, resolve_with_annotations
- `tests/test_config/test_validation.py` - 7 tests for unknown key detection and error messages

## Decisions Made
- Used `cast()` for pyright strict compliance on `yaml.safe_load` and `model_dump` output types -- these return `Any` which pyright strict mode rejects for iteration
- Extracted `_build_warning` helper in validation.py to keep line lengths under 88 chars while maintaining readable warning messages
- `resolve_with_annotations` loads each source layer independently and compares against the final config to determine provenance -- this is custom logic since pydantic-settings doesn't natively expose which source provided each value

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Full config system complete (models, loader, validation, template, source annotations)
- Phase 9 CLI integration can wire policyfoundry init (using CONFIG_TEMPLATE) and policyfoundry config show (using resolve_with_annotations)
- All downstream phases can import from policyfoundry.config for configuration access

## Self-Check: PASSED

- All 5 created/modified files exist on disk
- All 3 task commits verified (355bc4d, 8dcb053, f08f80a)
- 77 tests passing (29 config + 48 Phase 1)
- ruff: clean
- pyright: clean

---
*Phase: 02-configuration-system*
*Completed: 2026-03-08*
