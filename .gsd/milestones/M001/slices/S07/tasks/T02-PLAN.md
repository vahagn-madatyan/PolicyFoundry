# T02: 07-pipeline-core 02

**Slice:** S07 — **Milestone:** M001

## Description

Implement Assess (Stage 2), Generate (Stage 3), and Validate (adapter filtering step) replacing the stubs created in Plan 01. These three stages form the analysis-to-proposal pipeline: Assess identifies gaps between traffic and rules, Generate creates proposals, and Validate filters out invalid proposals before the Decide stage.

Purpose: Delivers the middle of the pipeline where the core intelligence lives -- comparing traffic to rules, generating proposals with justification, and ensuring proposals are valid before decision-making.

Output: Three fully implemented stage modules with prompts and tests.

## Must-Haves

- [ ] "Assess stage compares TrafficAnalysis patterns against current SG rules and produces SecurityAssessment with rule_gaps"
- [ ] "Generate stage produces up to 20 vendor-neutral PolicyProposals with impact_analysis, respecting adapter capabilities"
- [ ] "Validate step filters proposals through adapter.validate() and removes invalid ones before Decide"
- [ ] "Assess prompt includes full rules list from adapter.get_rules()"
- [ ] "Generate prompt includes adapter capabilities so LLM knows constraints (allow-only, max 60 rules)"
- [ ] "Denied traffic with consistent patterns flagged as ALLOW rule candidates in Generate prompt"

## Files

- `src/policyfoundry/pipeline/stages/assess.py`
- `src/policyfoundry/pipeline/stages/generate.py`
- `src/policyfoundry/pipeline/stages/validate.py`
- `src/policyfoundry/pipeline/prompts/assess.py`
- `src/policyfoundry/pipeline/prompts/generate.py`
- `src/policyfoundry/pipeline/prompts/__init__.py`
- `src/policyfoundry/pipeline/stages/__init__.py`
