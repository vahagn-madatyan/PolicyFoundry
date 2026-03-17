---
sliceId: S01
uatType: artifact-driven
verdict: PASS
date: 2026-03-17T02:45:00Z
---

# UAT Result — S01

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| Smoke test: 152 pipeline tests pass | PASS | 152 passed, 0 failed (7.60s) |
| TC1: Token usage per-stage (stage= kwarg asserted) | PASS | 2/2 tests pass |
| TC1 coverage: `grep 'stage="'` in stage files | PASS | 8 lines — analyze, assess, generate, decide × 2 pipelines |
| TC2: Runner error handler reports correct stage | PASS | 8/8 tests pass (4 per runner) |
| TC3: Generate prompt references correct field names | PASS | 5/5 tests pass (dst_ip, src_ip, no counterpart_ip, both directions, service_port+protocol) |
| TC3 verify: no stale counterpart_ip references in source | PASS | No source file matches (only __pycache__ bytecache) |
| TC4: Rejected proposals are logged | PASS | 7/7 tests pass (warning on rejection, fallback reason, no warning when valid, multi-error join) |
| TC5: Stage functions wrap exceptions with stage identity | PASS | 11/11 tests pass (all stages wrap, PipelineError not double-wrapped) |
| TC5 coverage: `grep 'except Exception'` in stage files | PASS | 10 lines — one per stage function across both pipelines |
| TC6: Full suite regression | PASS | 636 passed, 0 failed (31.55s) |
| Edge: PipelineError cause chain depth | PASS | test_wrapped_pipeline_error_extracts_stage passes |
| Edge: Empty validation errors fallback | PASS | test_logs_fallback_reason_when_no_errors passes |
| Edge: Stage-level wrapping vs runner catch-all | PASS | 4/4 tests pass (test_excel_pipeline + test_graph error handling) |

## Overall Verdict

PASS — All 13 checks passed. 152 pipeline tests, 636 full regression tests, all grep coverage assertions confirmed. No failures or regressions.

## Notes

- `rg` was not available on this system; used `grep -rn` as equivalent. The `counterpart_ip` grep matched only in `__pycache__/generate.cpython-313.pyc` (stale bytecache), not in any `.py` source file — this is expected and not a concern.
- AWS-dependent tests (`test_aws_sg_adapter.py`, `test_ingestion/test_s3.py`) excluded per UAT spec.
