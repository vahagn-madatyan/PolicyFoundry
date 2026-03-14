"""Assess stage prompts: system prompt and user message formatting."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyfoundry.adapters.schema import UniversalRule


ASSESS_SYSTEM_PROMPT = """You are a cloud security assessor specializing in firewall rule gap analysis. Your task is to compare observed VPC traffic patterns against the current set of security group rules and produce a structured security assessment.

Given the traffic analysis and current rules, you must:

1. Identify rule gaps -- traffic patterns observed in the flow logs that have no corresponding allow or deny rule in the current ruleset. Flag allowed traffic with no explicit rule as potential oversights.
2. Flag denied traffic that appears legitimate and consistent (repeated same src/dst/port patterns) as candidates for new ALLOW rules.
3. Assess overall risk by evaluating the gap severity, the volume of unmatched traffic, and the types of ports and protocols involved.
4. Produce risk scores for categories such as open ports, denied traffic volume, unmatched outbound traffic, and protocol anomalies.
5. Note any compliance findings -- practices that deviate from security best practices (e.g., SSH open to 0.0.0.0/0, no bastion host, overly broad CIDR ranges).

Be precise and factual. Every finding must be supported by the provided data. If no gaps are found, report a clean assessment rather than fabricating issues."""


def format_assess_user_message(
    analysis: dict,
    current_rules: list[UniversalRule],
) -> str:
    """Serialize traffic analysis and current rules as JSON for the LLM.

    Args:
        analysis: Serialized TrafficAnalysis dict from pipeline state.
        current_rules: Current firewall rules from adapter.get_rules().

    Returns:
        JSON string with traffic analysis and current rules.
    """
    data = {
        "traffic_analysis": analysis,
        "current_rules": [r.model_dump() for r in current_rules],
    }
    return json.dumps(data, indent=2)
