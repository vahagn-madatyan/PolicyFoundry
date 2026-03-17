"""Tests for export models: flatten_to_entries and related helpers."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from policyfoundry.adapters.schema import (
    Direction,
    NetworkEndpoint,
    PortRange,
    RiskLevel,
    RuleAction,
    UniversalRule,
)
from policyfoundry.export.models import flatten_to_entries
from policyfoundry.pipeline.excel_state import ExcelPipelineState
from policyfoundry.pipeline.schema import PolicyProposal, RuleDecision


class TestOrphanedDecisionLogging:
    """Tests for orphaned decision warning on missing proposal."""

    @pytest.fixture
    def state_with_orphan(self) -> ExcelPipelineState:
        """State where dec-orphan references a nonexistent proposal."""
        proposal = PolicyProposal(
            proposal_id="prop-001",
            rule=UniversalRule(
                name="allow-ssh",
                description="Allow SSH",
                action=RuleAction.ALLOW,
                direction=Direction.INBOUND,
                protocol="TCP",
                source=[NetworkEndpoint(is_any=True)],
                destination=[NetworkEndpoint(cidr="10.0.0.1/32")],
                port_range=PortRange(from_port=22, to_port=22),
            ),
            justification="SSH access needed",
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            impact_analysis="Allows SSH",
        )

        decisions = [
            RuleDecision(
                decision_id="dec-001",
                proposal_id="prop-001",
                action="CREATE",
                risk_level=RiskLevel.LOW,
                reason="Approved",
                approval_required=False,
            ),
            RuleDecision(
                decision_id="dec-orphan",
                proposal_id="prop-missing",
                action="CREATE",
                risk_level=RiskLevel.MEDIUM,
                reason="Orphaned",
                approval_required=True,
            ),
        ]

        state: ExcelPipelineState = {
            "run_id": "run-orphan-test",
            "started_at": "2026-03-15T09:00:00+00:00",
            "current_stage": "decide",
            "proposals": [proposal.model_dump()],
            "decisions": [d.model_dump() for d in decisions],
        }
        return state

    def test_orphaned_decision_logs_warning(
        self,
        state_with_orphan: ExcelPipelineState,
    ) -> None:
        """Orphaned decision logs warning with decision_id and proposal_id."""
        with patch("policyfoundry.export.models.logger") as mock_logger:
            entries = flatten_to_entries(state_with_orphan)

        # Only the valid decision should produce an entry
        assert len(entries) == 1
        assert entries[0].proposal_id == "prop-001"

        # Warning should have been logged for the orphan
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        msg = call_args[0][0] % call_args[0][1:]
        assert "dec-orphan" in msg
        assert "prop-missing" in msg
