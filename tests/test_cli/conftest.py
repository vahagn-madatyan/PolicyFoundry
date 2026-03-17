"""Shared fixtures for CLI integration tests.

Provides:
- CliRunner instance for invoking Typer commands
- Mock LLM client factory (prevents real API calls)
- Mock adapter factory (prevents real AWS calls)
- Sample pipeline state for output verification
"""

from __future__ import annotations

import copy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from policyfoundry.adapters.schema import AdapterCapabilities
from policyfoundry.output.models import TokenUsage


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CLI test runner for invoking commands."""
    return CliRunner()


@pytest.fixture
def sample_pipeline_state() -> dict:
    """Complete pipeline state dict with all stage outputs populated.

    Fields match the actual Pydantic schema models:
    - TrafficAnalysis: requires port_distribution, anomalies, bandwidth_outliers
    - PolicyProposal: requires impact_analysis; rule needs description, source as list,
      port_range with from_port/to_port
    - RuleDecision: requires RiskLevel enum values
    """
    return {
        "run_id": "test-run-001",
        "started_at": "2025-01-15T10:00:00+00:00",
        "current_stage": "complete",
        "flow_log_path": "/tmp/test-data",
        "sg_ids": ["sg-12345"],
        "analysis": {
            "summary": "Test traffic analysis summary.",
            "total_flows": 1000,
            "unique_sources": 50,
            "unique_destinations": 25,
            "top_talkers": [
                {"ip": "10.0.1.1", "bytes": 50000},
                {"ip": "10.0.1.2", "bytes": 30000},
            ],
            "port_distribution": [
                {"port": 443, "protocol": "TCP", "count": 500},
                {"port": 22, "protocol": "TCP", "count": 200},
            ],
            "anomalies": [
                {"type": "high_denied_rate", "description": "5% denied flows"},
            ],
            "bandwidth_outliers": [
                {"ip": "10.0.1.1", "bytes": 50000, "z_score": 2.5},
            ],
        },
        "assessment": {
            "overall_risk": "MEDIUM",
            "risk_scores": [
                {"category": "exposure", "score": 0.6, "description": "Moderate exposure"},
                {"category": "complexity", "score": 0.3, "description": "Low complexity"},
            ],
            "rule_gaps": [
                {"severity": "HIGH", "description": "Wide open SSH access"},
            ],
            "recommendations": ["Restrict SSH to known IPs"],
            "compliance_findings": ["CIS 4.1: SSH access too broad"],
        },
        "proposals": [
            {
                "proposal_id": "PROP-001",
                "rule": {
                    "name": "restrict-ssh",
                    "description": "Restrict SSH to internal network only.",
                    "direction": "INBOUND",
                    "action": "ALLOW",
                    "protocol": "TCP",
                    "port_range": {"from_port": 22, "to_port": 22},
                    "source": [{"cidr": "10.0.0.0/8"}],
                    "destination": [],
                },
                "justification": "Restrict SSH to internal network.",
                "risk_level": "LOW",
                "confidence": 0.95,
                "impact_analysis": "Blocks SSH from external IPs; internal access unaffected.",
            },
        ],
        "decisions": [
            {
                "decision_id": "DEC-001",
                "proposal_id": "PROP-001",
                "action": "CREATE",
                "risk_level": "LOW",
                "reason": "Low risk, high confidence change.",
                "approval_required": False,
            },
        ],
        "token_usage": {
            "prompt_tokens": 1500,
            "completion_tokens": 500,
            "total_tokens": 2000,
            "total_cost": 0.0045,
            "per_stage": [
                {"prompt_tokens": 500, "completion_tokens": 150, "total_tokens": 650, "cost": 0.0015, "stage": "analyze"},
                {"prompt_tokens": 500, "completion_tokens": 150, "total_tokens": 650, "cost": 0.0015, "stage": "assess"},
                {"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700, "cost": 0.0015, "stage": "generate"},
            ],
        },
    }


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mock LLM client that returns deterministic pipeline responses."""
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock()
    return client


@pytest.fixture
def mock_llm_client_factory(mock_llm_client: MagicMock):
    """Factory fixture that returns the mock LLM client."""
    def _factory(*args, **kwargs):
        return mock_llm_client
    return _factory


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Mock adapter that returns deterministic security group data."""
    adapter = MagicMock()
    adapter.list_rules.return_value = []
    adapter.apply_rules.side_effect = NotImplementedError(
        "ReadOnlyAdapter should block writes"
    )
    return adapter


@pytest.fixture
def mock_adapter_factory(mock_adapter: MagicMock):
    """Factory fixture that returns the mock adapter."""
    def _factory(*args, **kwargs):
        return mock_adapter
    return _factory
