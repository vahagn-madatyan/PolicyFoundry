"""Subnet grouping: identify /N candidates from aggregated flows.

Groups IPs that share a common subnet *and* common traffic patterns
(same dst_ip + service_port + protocol). Produces ``SubnetGroup`` candidates
for the LLM in S03 to evaluate — these are suggestions, not final rules.
"""

from __future__ import annotations

import ipaddress
from collections import defaultdict

from policyfoundry.analysis.models import AggregatedFlow, SubnetGroup

# Minimum IPs required in a subnet to form a candidate group.
_MIN_MEMBERS: int = 2


def group_to_subnets(
    flows: list[AggregatedFlow],
    prefix_len: int = 24,
) -> list[SubnetGroup]:
    """Identify /N subnet candidates from aggregated flows.

    Groups both *source* and *destination* IPs:
    - **Source grouping:** src_ips sharing a /{prefix_len} that also share
      traffic patterns (same dst_ip + service_port + protocol).
    - **Destination grouping:** dst_ips sharing a /{prefix_len} receiving
      traffic with the same pattern (same src_ip + service_port + protocol).

    Only subnets with ≥ 2 member IPs are included.
    """
    groups: list[SubnetGroup] = []

    # --- Source-side grouping ---
    _collect_groups(
        flows=flows,
        ip_attr="src_ip",
        pattern_attrs=("dst_ip", "service_port", "protocol"),
        prefix_len=prefix_len,
        out=groups,
    )

    # --- Destination-side grouping ---
    _collect_groups(
        flows=flows,
        ip_attr="dst_ip",
        pattern_attrs=("src_ip", "service_port", "protocol"),
        prefix_len=prefix_len,
        out=groups,
    )

    # Deduplicate by (cidr, frozenset(member_ips), pattern)
    seen: set[tuple[str, frozenset[str], str]] = set()
    deduped: list[SubnetGroup] = []
    for sg in groups:
        for pattern in sg.shared_patterns:
            key = (sg.cidr, frozenset(sg.member_ips), str(sorted(pattern.items())))
            if key not in seen:
                seen.add(key)
                # Only add once per unique (cidr, members) — collect all patterns
                break
        else:
            continue
        deduped.append(sg)

    # Final dedup: merge groups with same cidr and member set
    merged = _merge_same_subnet(deduped)
    merged.sort(key=lambda sg: sg.member_count, reverse=True)
    return merged


def _collect_groups(
    *,
    flows: list[AggregatedFlow],
    ip_attr: str,
    pattern_attrs: tuple[str, ...],
    prefix_len: int,
    out: list[SubnetGroup],
) -> None:
    """Collect subnet group candidates for one side (src or dst).

    Builds a mapping: (subnet_cidr, pattern) → set of IPs, then creates
    ``SubnetGroup`` entries for groups with ≥ ``_MIN_MEMBERS`` IPs.
    """
    # Key: (subnet_cidr_str, pattern_tuple) → set of IPs
    mapping: dict[tuple[str, tuple[tuple[str, str | int], ...]], set[str]] = defaultdict(set)

    for flow in flows:
        ip_str: str = getattr(flow, ip_attr)
        try:
            network = ipaddress.ip_network(f"{ip_str}/{prefix_len}", strict=False)
        except ValueError:
            continue
        cidr = str(network)
        pattern = tuple(
            (attr, getattr(flow, attr)) for attr in pattern_attrs
        )
        mapping[(cidr, pattern)].add(ip_str)

    # Group by subnet CIDR, collecting all patterns that meet the threshold
    subnet_data: dict[str, dict[frozenset[str], list[dict[str, str | int]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (cidr, pattern_tuple), ips in mapping.items():
        if len(ips) >= _MIN_MEMBERS:
            frozen_ips = frozenset(ips)
            pattern_dict: dict[str, str | int] = dict(pattern_tuple)
            subnet_data[cidr][frozen_ips].append(pattern_dict)

    for cidr, ip_groups in subnet_data.items():
        for ips_frozen, patterns in ip_groups.items():
            member_ips = sorted(ips_frozen)
            out.append(
                SubnetGroup(
                    cidr=cidr,
                    member_ips=member_ips,
                    member_count=len(member_ips),
                    shared_patterns=patterns,
                )
            )


def _merge_same_subnet(groups: list[SubnetGroup]) -> list[SubnetGroup]:
    """Merge SubnetGroups that share the same cidr and member_ips set."""
    key_map: dict[tuple[str, frozenset[str]], SubnetGroup] = {}
    for sg in groups:
        k = (sg.cidr, frozenset(sg.member_ips))
        if k in key_map:
            existing = key_map[k]
            # Merge patterns
            existing_patterns_set = {
                str(sorted(p.items())) for p in existing.shared_patterns
            }
            for p in sg.shared_patterns:
                if str(sorted(p.items())) not in existing_patterns_set:
                    existing.shared_patterns.append(p)
                    existing_patterns_set.add(str(sorted(p.items())))
        else:
            key_map[k] = sg
    return list(key_map.values())
