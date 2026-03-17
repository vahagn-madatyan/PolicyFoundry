"""Generate stage prompts for the Excel traffic pipeline.

Extends M01's generate prompt with Excel-specific context: SubnetGroup
candidates with shared_patterns keys, CIDR format guidance, and
subnet-rule preference when 2+ IPs share a pattern.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from policyfoundry.adapters.schema import AdapterCapabilities


EXCEL_GENERATE_SYSTEM_PROMPT = """\
You are a firewall policy engineer. Your task is to generate \
vendor-neutral rule proposals based on the security assessment \
and traffic analysis from a firewall traffic export.

Key context about this data:
- Traffic comes from an Excel/CSV export — there are no existing \
firewall rules to reference. All proposals are for NEW rules.
- Subnet grouping has been performed upstream. You will receive \
SubnetGroup candidates — groups of IPs that share a /24 network \
and common traffic patterns. Each SubnetGroup has a ``shared_patterns`` \
list where each entry is a dict with ``service_port`` (the shared \
destination port), ``protocol`` (TCP or UDP), and either ``dst_ip`` \
or ``src_ip`` depending on the grouping direction:
  - **Source-side groups** (member IPs are sources): patterns contain \
``dst_ip`` — the common destination IP they all talk to.
  - **Destination-side groups** (member IPs are destinations): patterns \
contain ``src_ip`` — the common source IP sending to all of them.

CIDR format guidance:
- Use 10.1.2.3/32 for individual IP addresses.
- Use 10.1.2.0/24 for subnets (when a SubnetGroup with 2+ member IPs \
shares a traffic pattern).
- Prefer subnet rules (/24) when 2 or more IPs in the same group share \
a pattern — this reduces rule count and is more maintainable.
- Only use /32 when an IP has a unique pattern not shared by its subnet.

Guidelines:
1. Produce up to 20 rule proposals per run. Prioritize the most \
impactful gaps identified in the security assessment.
2. Every proposal must include an ``impact_analysis`` field explaining \
what traffic the rule covers, what services it enables or protects, \
and what could break if applied incorrectly.
3. Every proposal must include a ``justification`` explaining WHY \
this rule is needed, grounded in the assessment and traffic data.
4. Every proposal must include a ``risk_level`` classification \
(LOW, MEDIUM, HIGH, or CRITICAL).
5. Use the SubnetGroup candidates to generate efficient subnet-level \
rules instead of per-IP rules wherever possible.
6. Respect the adapter constraints provided. The ``adapter_constraints`` \
object describes vendor-specific limitations (deny rule support, \
max rules per direction, L7 filtering availability).
7. Each proposal must have a unique ``proposal_id``, a ``confidence`` \
score (0.0 to 1.0), and use the UniversalRule format with proper \
NetworkEndpoint source/destination, PortRange, direction, and \
protocol fields.
8. If the assessment shows no gaps or risk is negligible, return an \
empty proposals list rather than inventing unnecessary rules."""


def format_excel_generate_user_message(
    assessment: dict[str, Any],
    capabilities: AdapterCapabilities,
    analysis: dict[str, Any],
    subnet_groups: list[dict[str, Any]],
) -> str:
    """Serialize assessment, capabilities, analysis, and subnet groups as JSON.

    Args:
        assessment: Serialized SecurityAssessment dict from state.
        capabilities: Adapter capabilities from adapter.capabilities().
        analysis: Serialized TrafficAnalysis dict from state.
        subnet_groups: SubnetGroup dicts from state, each containing
            cidr, member_ips, member_count, and shared_patterns.

    Returns:
        JSON string with all four data sections.
    """
    data = {
        "security_assessment": assessment,
        "adapter_constraints": capabilities.model_dump(),
        "traffic_analysis": analysis,
        "subnet_group_candidates": subnet_groups,
    }
    return json.dumps(data, indent=2)
