"""Analyze stage prompts: system prompt and user message formatting."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policyfoundry.storage.models import (
        DeniedFlowResult,
        TopTalkerResult,
        TrafficByProtocolResult,
        TrafficSummary,
    )


ANALYZE_SYSTEM_PROMPT = """You are a network traffic analyst specializing in cloud security. Your task is to analyze pre-aggregated traffic statistics from VPC flow logs and produce a structured traffic analysis.

Given the traffic data provided, you must:

1. Summarize the overall traffic patterns observed, including volume, protocol distribution, and directional trends.
2. Identify the top talkers (highest-bandwidth source IPs) and assess whether their traffic volumes are expected or anomalous.
3. Examine denied flows for patterns that may indicate misconfigured security group rules, blocked legitimate traffic, or potential threats.
4. Identify anomalies such as unusual protocol usage, unexpected port access, bandwidth outliers, or traffic spikes.
5. Note any bandwidth outliers -- sources or destinations transferring significantly more data than peers.

If the data is empty or sparse, report that no data is available for analysis rather than hallucinating patterns. Describe only what the data actually shows.

Be precise and factual. Base every finding on the provided statistics."""


def format_analyze_user_message(
    summary: TrafficSummary,
    top_talkers: list[TopTalkerResult],
    denied_flows: list[DeniedFlowResult],
    protocol_breakdown: list[TrafficByProtocolResult],
) -> str:
    """Serialize all DuckDB query results to structured JSON for the LLM.

    Args:
        summary: Overall traffic summary statistics.
        top_talkers: Top N source IPs by bytes transferred.
        denied_flows: Denied flow patterns with counts and ports.
        protocol_breakdown: Traffic volume broken down by protocol.

    Returns:
        JSON string with all query results under descriptive keys.
    """
    data = {
        "traffic_summary": summary.model_dump(),
        "top_talkers": [t.model_dump() for t in top_talkers],
        "denied_flows": [d.model_dump() for d in denied_flows],
        "protocol_breakdown": [p.model_dump() for p in protocol_breakdown],
    }
    return json.dumps(data, indent=2)
