"""Decide stage prompts: system prompt and user message formatting."""

from __future__ import annotations

import json
from typing import Any


DECIDE_SYSTEM_PROMPT = """You are a security policy decision-maker. Your task is to review all proposed firewall rule changes and make a final decision on each one.

You will receive a summarized list of proposals generated from traffic analysis and security assessment. For each proposal, you must assign:

1. **action**: One of CREATE, UPDATE, or SKIP.
   - CREATE: Approve the proposal as a new firewall rule.
   - UPDATE: Approve the proposal as a modification to an existing rule.
   - SKIP: Reject the proposal with a documented reason. SKIP means\
      "considered but rejected" -- always explain why.

2. **risk_level**: Classify as LOW, MEDIUM, HIGH, or CRITICAL based on\
    the scope and sensitivity of the traffic the rule covers.

3. **approval_required**: Set to true for HIGH/CRITICAL risk or rules\
    that open access to sensitive ports (SSH, RDP, databases). Set to\
    false for LOW risk and well-scoped rules.

Process all proposals in a single pass. You see the full picture for cross-proposal reasoning. Specifically:

- Detect **redundant proposals** (overlapping CIDRs, same port/protocol)\
   and SKIP duplicates, keeping the most specific rule.
- Detect **conflicting proposals** (one allows what another implicitly\
   denies or vice versa) and resolve by choosing the safer option.
- Consider cumulative risk: many LOW-risk rules can compound into\
   MEDIUM overall exposure.

Every decision must include a clear reason grounded in the proposal data provided. Do not fabricate traffic patterns or security concerns not present in the input."""


def format_decide_user_message(proposals: list[dict[str, Any]]) -> str:
    """Summarize proposals for the LLM decision prompt.

    Per RESEARCH.md Pitfall 3 (token budget), this function extracts
    essential fields from each proposal rather than passing full JSON.
    For each proposal:
      - Extracts proposal_id, rule name, direction, protocol, risk_level
      - Collects source and destination CIDRs from nested endpoints
      - Truncates justification to 100 chars

    Args:
        proposals: List of serialized PolicyProposal dicts from state.

    Returns:
        JSON string with summarized proposal list.
    """
    summaries: list[dict[str, Any]] = []
    for p in proposals:
        rule = p.get("rule", {})

        source_cidrs = [
            s.get("cidr", "unknown")
            for s in rule.get("source", [])
            if s.get("cidr")
        ]

        dest_cidrs = [
            d.get("cidr", "unknown")
            for d in rule.get("destination", [])
            if d.get("cidr")
        ]

        justification = p.get("justification", "")
        summaries.append({
            "proposal_id": p.get("proposal_id", ""),
            "rule_name": rule.get("name", ""),
            "direction": rule.get("direction", ""),
            "protocol": rule.get("protocol", ""),
            "source_cidrs": source_cidrs,
            "destination_cidrs": dest_cidrs,
            "justification_summary": justification[:100],
            "risk_level": p.get("risk_level", ""),
        })

    data = {"proposals": summaries}
    return json.dumps(data, indent=2)
