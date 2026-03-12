---
estimated_steps: 4
estimated_files: 9
---

# T04: Reconstruct src storage and adapters core from bytecode

**Slice:** S09 — CLI Integration
**Milestone:** M001

## Description

Reconstructs the storage layer (Parquet writer, DuckDB queries) and the adapter framework (FirewallAdapter ABC, adapter schema with UniversalRule/RiskLevel, adapter registry). The adapter schema is one of the most widely imported modules — `RiskLevel`, `UniversalRule`, `Direction`, `RuleAction`, `PortRange`, `NetworkEndpoint` are used by pipeline stages, output formatters, and the CLI. The storage writer and queries are used by the pipeline runner.

## Steps

1. **Reconstruct storage module** (5 files):
   - `storage/__init__.py` — re-exports
   - `storage/models.py` — storage-specific data models (WriteResult, etc.)
   - `storage/parquet_schema.py` — PyArrow schema definition for Parquet files (per D014 filename format)
   - `storage/writer.py` — `async write_records(records, data_dir, source_files) -> WriteResult` using zstd-compressed Parquet via PyArrow
   - `storage/queries.py` — DuckDB analytics queries: `top_talkers`, `traffic_summary`, `denied_flows`, `traffic_by_protocol` with per-query connections (D013)

2. **Reconstruct adapter core** (4 files):
   - `adapters/__init__.py` — re-exports
   - `adapters/base.py` — `FirewallAdapter` ABC with abstract methods: `get_rules()`, `validate()`, `apply_rule()`, `apply_rules()`, `capabilities()`
   - `adapters/schema.py` — `RiskLevel` StrEnum, `Direction` StrEnum, `RuleAction` StrEnum, `PortRange`, `NetworkEndpoint` (with model_validator per D015), `UniversalRule`, `ValidationResult`, `AdapterCapabilities`
   - `adapters/registry.py` — `AdapterRegistry` with `get_adapter(name, **kwargs) -> FirewallAdapter` static method (entry_points + built-in aws_sg fallback)

3. **Verify imports and key types** — Check that `RiskLevel` has expected enum values (e.g., CRITICAL, HIGH, MEDIUM, LOW), `FirewallAdapter` has all abstract methods, `AdapterRegistry.get_adapter` is callable.

4. **Cross-verify** — Ensure storage models reference correct types from ingestion schema, and adapter schema types are consistent with what pipeline stages expect.

## Must-Haves

- [ ] `FirewallAdapter` ABC has abstract methods: `get_rules`, `validate`, `apply_rule`, `apply_rules`, `capabilities`
- [ ] `NetworkEndpoint` has model_validator enforcing at-least-one-identifier (D015)
- [ ] `AdapterRegistry.get_adapter(name, **kwargs)` returns instantiated adapter (not class)
- [ ] DuckDB queries use per-query connections (D013)
- [ ] All 9 files import without error

## Verification

- `uv run python -c "from policyfoundry.adapters.schema import RiskLevel, UniversalRule, Direction, RuleAction; print(list(RiskLevel)); print('OK')"`
- `uv run python -c "from policyfoundry.adapters.base import FirewallAdapter; from policyfoundry.adapters.registry import AdapterRegistry; print('OK')"`
- `uv run python -c "from policyfoundry.storage.writer import write_records; from policyfoundry.storage.queries import top_talkers, traffic_summary; print('OK')"`

## Observability Impact

- Signals added/changed: None (reconstruction only)
- How a future agent inspects this: Import `AdapterRegistry` and call `get_adapter('aws_sg', security_group_id='sg-test')` to verify registry works
- Failure state exposed: None

## Inputs

- `src/policyfoundry/storage/__pycache__/*.cpython-313.pyc` (5 files, 886–10059 bytes)
- `src/policyfoundry/adapters/__pycache__/*.cpython-313.pyc` (4 files, 746–5103 bytes)
- `tools/inspect_pyc.py` from T01
- Decisions D013, D014, D015, D016, D017
- `src/policyfoundry/exceptions.py` from T02 (StorageError, AdapterError subclasses)

## Expected Output

- `src/policyfoundry/storage/__init__.py`, `models.py`, `parquet_schema.py`, `writer.py`, `queries.py`
- `src/policyfoundry/adapters/__init__.py`, `base.py`, `schema.py`, `registry.py`
