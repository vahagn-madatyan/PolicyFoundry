# Project Knowledge

Append-only register of project-specific rules, patterns, and lessons learned.
Agents read this before every unit. Add entries when you discover something worth remembering.

## Rules

| # | Scope | Rule | Why | Added |
|---|-------|------|-----|-------|
| K001 | pipeline/schema | LLM structured-output enums must use `StrEnum`, not plain `Enum` | Instructor serializes model output as JSON — `StrEnum` produces plain strings; `Enum` produces `{"value": "X"}`. Downstream code also calls `.upper()` on action values. | 2026-03-16 |

## Patterns

| # | Pattern | Where | Notes |
|---|---------|-------|-------|
| P001 | `StrEnum` for constrained string fields on Pydantic LLM output models | `pipeline/schema.py` `DecisionAction` | Gives Pydantic validation + string serialization. Use this pattern for any future enum-like fields on Instructor response models. |

## Lessons Learned

| # | What Happened | Root Cause | Fix | Scope |
|---|--------------|------------|-----|-------|
| L001 | Adding `DecisionAction` enum broke e2e/CLI tests — fixtures used `"APPROVE"` as an action | `RuleDecision.action` was `str` so any string was accepted; test fixtures drifted from valid domain values | Fixed fixtures to use `"CREATE"`. The enum caught exactly the kind of bug it was designed to prevent. | tests/e2e, tests/test_cli |
