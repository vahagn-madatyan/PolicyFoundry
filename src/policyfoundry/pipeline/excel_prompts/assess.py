"""Assess stage prompts for the Excel traffic pipeline.

The most novel prompt in the Excel pipeline: with NullAdapter returning
empty rules, the LLM must *infer* likely existing rules from traffic
patterns rather than comparing against a known ruleset.
"""

from __future__ import annotations

import json
from typing import Any

from policyfoundry.adapters.schema import UniversalRule


EXCEL_ASSESS_SYSTEM_PROMPT = """\
You are a cloud security assessor specializing in firewall rule gap \
analysis. Your task is to assess security risks from observed traffic \
patterns and the current set of firewall rules.

Important: No existing firewall rules may be available for comparison. \
When the current ruleset is empty, you must infer likely existing rules \
from traffic patterns:
- High-volume traffic on well-known ports (443, 80, 53, 22) is likely \
already permitted by existing rules — these represent established \
services.
- Consistent traffic from specific subnets to specific services \
suggests intentional allow rules.
- Focus on identifying gaps — traffic that is probably NOT covered by \
existing rules and would need new rules.
- Low-volume traffic on unusual ports, sporadic connections, or \
connections from unexpected sources are more likely to represent \
gaps or unauthorized access.

When rules ARE provided, compare observed traffic against them directly \
and identify mismatches.

Given the traffic analysis and current rules (possibly empty), you must:

1. Identify rule gaps — traffic patterns with no corresponding rule \
(or, when rules are empty, traffic that likely lacks explicit rules).
2. Flag traffic that appears legitimate but is probably not covered — \
candidates for new ALLOW rules.
3. Assess overall risk by evaluating gap severity, traffic volume, and \
port/protocol types involved.
4. Produce risk scores for categories such as open ports, unmatched \
traffic, protocol anomalies, and UNKNOWN-direction exposure.
5. Note compliance findings — practices that deviate from security \
best practices (e.g. broad access patterns, missing segmentation).

Flows with direction UNKNOWN should be assessed conservatively — they \
may represent misconfigured or unexpected traffic paths.

Be precise and factual. Every finding must be supported by the provided \
data. If no gaps are found, report a clean assessment rather than \
fabricating issues."""


def format_excel_assess_user_message(
    analysis: dict[str, Any],
    current_rules: list[UniversalRule],
) -> str:
    """Serialize traffic analysis and current rules as JSON for the LLM.

    Args:
        analysis: Serialized TrafficAnalysis dict from pipeline state.
        current_rules: Current firewall rules from adapter.get_rules().
            Will be an empty list when using NullAdapter.

    Returns:
        JSON string with traffic analysis and current rules.
    """
    data = {
        "traffic_analysis": analysis,
        "current_rules": [r.model_dump() for r in current_rules],
    }
    return json.dumps(data, indent=2)
