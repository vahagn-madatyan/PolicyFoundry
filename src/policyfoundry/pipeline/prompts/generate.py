"""Generate stage prompts: system prompt and user message formatting."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyfoundry.adapters.schema import AdapterCapabilities


GENERATE_SYSTEM_PROMPT = """You are a firewall policy engineer. Your task is to generate vendor-neutral rule proposals based on the security assessment and traffic analysis provided.

Guidelines:

1. Produce up to 20 rule proposals per run. Prioritize the most impactful gaps identified in the security assessment.
2. Every proposal must include an impact_analysis field explaining what traffic the rule covers, what services it enables or protects, and what could break if the rule is applied incorrectly.
3. Group similar traffic patterns into broader rules where sensible. For example, multiple IPs in the same /24 subnet should become one CIDR rule rather than individual IP rules.
4. Denied traffic with consistent patterns (repeated same src/dst/port combinations) should be flagged as ALLOW rule candidates when the traffic appears legitimate.
5. Respect the adapter constraints provided in the context. The adapter_constraints object describes vendor-specific limitations such as whether deny rules are supported, the maximum number of rules per direction, and whether L7 filtering is available.
6. Each proposal must have a unique proposal_id, a confidence score (0.0 to 1.0), and a risk_level classification.
7. Proposals should use the UniversalRule format with proper NetworkEndpoint source/destination, PortRange, direction, and protocol fields.

If the assessment shows no gaps or the risk is negligible, return an empty proposals list rather than inventing unnecessary rules."""


def format_generate_user_message(
    assessment: dict,
    capabilities: AdapterCapabilities,
    analysis: dict,
) -> str:
    """Serialize assessment, capabilities, and analysis as JSON.

    Args:
        assessment: Serialized SecurityAssessment dict from state.
        capabilities: Adapter capabilities from adapter.capabilities().
        analysis: Serialized TrafficAnalysis dict from state.

    Returns:
        JSON string with assessment, adapter constraints, and analysis.
    """
    data = {
        "security_assessment": assessment,
        "adapter_constraints": capabilities.model_dump(),
        "traffic_analysis": analysis,
    }
    return json.dumps(data, indent=2)
