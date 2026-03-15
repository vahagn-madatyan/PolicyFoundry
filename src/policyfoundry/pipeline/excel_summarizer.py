"""Pre-summarizer: compact statistics from aggregated flow data.

Computes summary statistics from AggregatedFlow and SubnetGroup lists,
keeping the output small enough for LLM context windows (< 3K tokens
for a 600-flow sample). Used by S03 pipeline stages to inject a compact
traffic overview into LLM prompts instead of raw flow records.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from policyfoundry.analysis.models import AggregatedFlow, DirectionLabel, SubnetGroup


def summarize_flows(
    flows: list[AggregatedFlow],
    subnet_groups: list[SubnetGroup],
) -> dict[str, Any]:
    """Compute compact statistics from aggregated flows and subnet groups.

    Returns a dict with:
        total_flows: Sum of all flow_count values.
        unique_sources: Number of distinct source IPs.
        unique_destinations: Number of distinct destination IPs.
        direction_breakdown: Counts per DirectionLabel.
        top_talkers: Top 20 (src_ip, dst_ip) pairs by flow_count.
        port_distribution: Top 20 service ports by aggregate flow_count.
        subnet_candidates: SubnetGroup summaries for LLM evaluation.
    """
    if not flows:
        return {
            "total_flows": 0,
            "unique_sources": 0,
            "unique_destinations": 0,
            "direction_breakdown": {
                label.value: 0 for label in DirectionLabel
            },
            "top_talkers": [],
            "port_distribution": [],
            "subnet_candidates": [],
        }

    total_flows = sum(f.flow_count for f in flows)

    unique_sources = len({f.src_ip for f in flows})
    unique_destinations = len({f.dst_ip for f in flows})

    # Direction breakdown
    direction_counts: Counter[str] = Counter()
    for f in flows:
        direction_counts[f.direction.value] += f.flow_count
    direction_breakdown = {
        label.value: direction_counts.get(label.value, 0)
        for label in DirectionLabel
    }

    # Top talkers: (src_ip, dst_ip) pairs ranked by total flow_count
    talker_counts: Counter[tuple[str, str]] = Counter()
    for f in flows:
        talker_counts[(f.src_ip, f.dst_ip)] += f.flow_count
    top_talkers = [
        {"src_ip": src, "dst_ip": dst, "flow_count": count}
        for (src, dst), count in talker_counts.most_common(20)
    ]

    # Port distribution: service ports ranked by aggregate flow_count
    port_counts: Counter[int] = Counter()
    for f in flows:
        port_counts[f.service_port] += f.flow_count
    port_distribution = [
        {"port": port, "flow_count": count}
        for port, count in port_counts.most_common(20)
    ]

    # Subnet candidates from SubnetGroup list
    subnet_candidates = [
        {
            "cidr": sg.cidr,
            "member_count": sg.member_count,
            "shared_patterns": sg.shared_patterns,
        }
        for sg in subnet_groups
    ]

    return {
        "total_flows": total_flows,
        "unique_sources": unique_sources,
        "unique_destinations": unique_destinations,
        "direction_breakdown": direction_breakdown,
        "top_talkers": top_talkers,
        "port_distribution": port_distribution,
        "subnet_candidates": subnet_candidates,
    }


def format_flow_summary_message(summary: dict[str, Any]) -> str:
    """Serialize flow summary to compact JSON for LLM prompt injection.

    Uses separators without extra whitespace to minimize token usage.
    """
    return json.dumps(summary, separators=(",", ":"))
