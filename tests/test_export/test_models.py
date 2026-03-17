"""Tests for export models: format helpers and flatten_to_entries."""

from __future__ import annotations

from typing import Any

import pytest

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
)
from policyfoundry.export.models import (
    ChangeRequestEntry,
    flatten_to_entries,
    format_endpoints,
    format_port_range,
)
from policyfoundry.pipeline.excel_state import ExcelPipelineState
from policyfoundry.pipeline.schema import PolicyProposal, RuleDecision


class TestFormatEndpoints:
    """Tests for format_endpoints()."""

    def test_multiple_cidrs(self) -> None:
        endpoints = [
            NetworkEndpoint(cidr="10.0.1.0/24"),
            NetworkEndpoint(cidr="10.0.2.0/24"),
        ]
        assert format_endpoints(endpoints) == "10.0.1.0/24, 10.0.2.0/24"

    def test_is_any(self) -> None:
        endpoints = [NetworkEndpoint(is_any=True)]
        assert format_endpoints(endpoints) == "any"

    def test_security_group_id(self) -> None:
        endpoints = [NetworkEndpoint(security_group_id="sg-abc123")]
        assert format_endpoints(endpoints) == "sg-abc123"

    def test_tag(self) -> None:
        endpoints = [NetworkEndpoint(tag={"env": "prod"})]
        assert format_endpoints(endpoints) == "env=prod"

    def test_empty_list(self) -> None:
        assert format_endpoints([]) == "any"

    def test_mixed_endpoints(self) -> None:
        endpoints = [
            NetworkEndpoint(cidr="10.0.1.0/24"),
            NetworkEndpoint(security_group_id="sg-xyz"),
        ]
        assert format_endpoints(endpoints) == "10.0.1.0/24, sg-xyz"


class TestFormatPortRange:
    """Tests for format_port_range()."""

    def test_single_port(self) -> None:
        assert format_port_range(PortRange(from_port=443, to_port=443)) == "443"

    def test_port_range(self) -> None:
        assert format_port_range(PortRange(from_port=8000, to_port=8080)) == "8000-8080"

    def test_none(self) -> None:
        assert format_port_range(None) == "any"


class TestFlattenToEntries:
    """Tests for flatten_to_entries()."""

    def test_correct_field_mapping(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Verify flattened entries have correct field values."""
        entries = flatten_to_entries(sample_excel_state)

        # Should have 2 entries (prop-001 CREATE + prop-002 UPDATE, not prop-003 SKIP)
        assert len(entries) == 2

        e1 = entries[0]
        assert e1.source == "10.0.1.0/24, 10.0.2.0/24"
        assert e1.destination == "10.0.3.10/32"
        assert e1.port == "22"
        assert e1.protocol == "TCP"
        assert e1.direction == "INBOUND"
        assert e1.action == "CREATE"
        assert e1.justification == "Repeated denied SSH from bastion subnet"
        assert e1.risk == "MEDIUM"
        assert e1.proposal_id == "prop-001"
        assert e1.approval_required is True

        e2 = entries[1]
        assert e2.source == "any"
        assert e2.destination == "sg-abc123"
        assert e2.port == "443"
        assert e2.action == "UPDATE"
        assert e2.approval_required is False

    def test_skip_filtering(
        self, sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Decisions with SKIP action are excluded."""
        entries = flatten_to_entries(sample_excel_state)
        actions = [e.action for e in entries]
        assert "SKIP" not in actions

    def test_empty_proposals(
        self, sample_excel_state_empty: ExcelPipelineState,
    ) -> None:
        """Empty state produces zero entries."""
        entries = flatten_to_entries(sample_excel_state_empty)
        assert entries == []

    def test_missing_proposal_for_decision(self) -> None:
        """Decision referencing a nonexistent proposal is skipped gracefully."""
        decisions = [
            RuleDecision(
                decision_id="dec-099",
                proposal_id="prop-nonexistent",
                action="CREATE",
                risk_level=RiskLevel.LOW,
                reason="Orphan decision",
                approval_required=False,
            ),
        ]
        state: ExcelPipelineState = {
            "run_id": "run-orphan-001",
            "started_at": "2026-03-15T09:00:00+00:00",
            "current_stage": "decide",
            "proposals": [],
            "decisions": [d.model_dump() for d in decisions],
        }
        entries = flatten_to_entries(state)
        assert entries == []
