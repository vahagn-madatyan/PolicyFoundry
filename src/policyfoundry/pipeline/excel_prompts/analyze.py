"""Analyze stage prompts for the Excel traffic pipeline.

Unlike M01's VPC flow-log prompts, these orient the LLM to work with
pre-summarized statistics from a firewall traffic export where direction
has been inferred (not natively tagged) and subnet grouping has already
been performed upstream.
"""

from __future__ import annotations

import json
from typing import Any


EXCEL_ANALYZE_SYSTEM_PROMPT = """\
You are a network traffic analyst specializing in firewall security. \
Your task is to analyze pre-summarized traffic statistics from a \
firewall traffic export (not VPC flow logs).

Key context about this data:
- Traffic direction (INBOUND / OUTBOUND) was inferred from port \
heuristics and interface metadata, not natively tagged. Some records \
may have direction UNKNOWN — these are flows where inference was \
ambiguous (e.g. both ports ephemeral, no interface signal). Treat \
UNKNOWN traffic as noteworthy rather than erroneous.
- Subnet grouping has already been performed upstream — the subnet \
candidates provided represent /24 groups with shared traffic patterns.
- Statistics are pre-aggregated: top talkers, port distribution, and \
direction breakdown are already computed. Do not re-derive them — \
analyze the patterns they reveal.

Given the traffic summary provided, you must:

1. Summarize overall traffic patterns: volume, direction distribution, \
and protocol tendencies (inferred from port usage).
2. Identify top talkers and assess whether their traffic volumes are \
expected or anomalous relative to peers.
3. Examine port distribution for unusual services, unexpected high-port \
traffic, or concentration on a single port.
4. Flag any anomalies: traffic to uncommon ports, high UNKNOWN-direction \
ratio, bandwidth outliers, or unexpected subnet groupings.
5. Note bandwidth outliers — sources or destinations with \
disproportionate flow counts.

If the data is empty or sparse, report that no data is available for \
analysis rather than hallucinating patterns. Describe only what the \
data actually shows.

Be precise and factual. Base every finding on the provided statistics."""


def format_excel_analyze_user_message(summary: dict[str, Any]) -> str:
    """Serialize pre-summarized flow statistics as JSON for the LLM.

    Args:
        summary: Output of ``summarize_flows()`` containing total_flows,
            unique_sources, unique_destinations, direction_breakdown,
            top_talkers, port_distribution, and subnet_candidates.

    Returns:
        Compact JSON string for prompt injection.
    """
    return json.dumps(summary, separators=(",", ":"))
