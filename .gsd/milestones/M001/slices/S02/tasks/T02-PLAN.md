# T02: 02-configuration-system 02

**Slice:** S02 — **Milestone:** M001

## Description

Add unknown key detection with "did you mean?" suggestions, config template generation for `policyfoundry init`, and source annotation utilities for `policyfoundry config show`.

Purpose: Completes CONF-01 by adding user-friendly warnings for typos in config files and enabling the init/show CLI commands (wired in Phase 9). Enhances CONF-02 by making config discoverable through the generated template.

Output: validation.py (unknown key detection), defaults.py (template + source annotations), updated loader.py (integrates unknown key warnings), and tests.

## Must-Haves

- [ ] "Unknown YAML config keys produce a warning message with 'did you mean?' suggestion"
- [ ] "Unknown keys do not cause config loading to fail -- valid config is still loaded"
- [ ] "policyfoundry init can generate a commented YAML template with all options and defaults"
- [ ] "Config values can be traced to their source (default, global YAML, local YAML, env var)"

## Files

- `src/policyfoundry/config/validation.py`
- `src/policyfoundry/config/defaults.py`
- `src/policyfoundry/config/__init__.py`
- `tests/test_config/test_validation.py`
