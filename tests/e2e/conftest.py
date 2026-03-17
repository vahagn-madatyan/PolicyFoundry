"""Shared E2E test fixtures.

Provides:
- Flow log fixture path
- Real ingestion → Parquet write into a temp data directory
- Mock LLM client returning deterministic structured outputs per stage
- Mock adapter with no-op get_rules / validate / capabilities
- Temp config YAML pointing at real fixture data
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    ValidationResult,
)
from policyfoundry.config.models import PolicyFoundryConfig
from policyfoundry.ingestion.local import ingest_local_files
from policyfoundry.output.models import TokenUsage
from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)
from policyfoundry.pipeline.stages.generate import PolicyProposalList
from policyfoundry.pipeline.stages.decide import RuleDecisionList
from policyfoundry.storage.writer import write_records

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "sample_flowlogs"
SAMPLE_LOG = FIXTURE_DIR / "vpc_flow_sample.log"

T = TypeVar("T", bound=BaseModel)


# ── Deterministic LLM responses per stage ────────────────────────────

_TRAFFIC_ANALYSIS = TrafficAnalysis(
    summary="Test traffic analysis: 16 flows across 8 unique sources to 6 destinations. "
    "Predominantly TCP traffic on ports 443, 22, 80, 3306, 8080. "
    "4 denied flows from external IPs targeting SSH and SMB. "
    "ICMP probes detected between internal hosts.",
    total_flows=16,
    unique_sources=8,
    unique_destinations=6,
    top_talkers=[
        {"ip": "10.0.7.7", "bytes": 8000},
        {"ip": "10.0.5.1", "bytes": 5000},
        {"ip": "10.0.2.10", "bytes": 4400},
    ],
    port_distribution=[
        {"port": 443, "protocol": "TCP", "count": 3},
        {"port": 22, "protocol": "TCP", "count": 4},
        {"port": 80, "protocol": "TCP", "count": 2},
        {"port": 53, "protocol": "UDP", "count": 1},
    ],
    anomalies=[
        {"type": "external_ssh_attempts", "description": "SSH access attempts from 203.0.113.0/24"},
        {"type": "smb_blocked", "description": "SMB (445) blocked from external IP"},
    ],
    bandwidth_outliers=[
        {"ip": "10.0.7.7", "bytes": 8000, "z_score": 2.1},
    ],
)

_SECURITY_ASSESSMENT = SecurityAssessment(
    overall_risk="MEDIUM",
    risk_scores=[
        {"category": "external_exposure", "score": 0.6, "description": "SSH exposed to external IPs"},
        {"category": "lateral_movement", "score": 0.3, "description": "Internal ICMP allowed broadly"},
    ],
    rule_gaps=[
        {"severity": "HIGH", "description": "SSH (22) accessible from 203.0.113.0/24"},
        {"severity": "MEDIUM", "description": "SMB (445) attempted from external network"},
    ],
    compliance_findings=["CIS 4.1: SSH access too broad", "CIS 4.3: SMB should be internal only"],
)

_PROPOSALS = PolicyProposalList(
    proposals=[
        PolicyProposal(
            proposal_id="PROP-001",
            rule={
                "name": "restrict-ssh-external",
                "description": "Block SSH from external 203.0.113.0/24.",
                "direction": "INBOUND",
                "action": "DENY",
                "protocol": "TCP",
                "port_range": {"from_port": 22, "to_port": 22},
                "source": [{"cidr": "203.0.113.0/24"}],
                "destination": [],
            },
            justification="Deny SSH from known external probing network.",
            risk_level="LOW",
            confidence=0.92,
            impact_analysis="Blocks 2 denied SSH flows; no legitimate traffic affected.",
        ),
        PolicyProposal(
            proposal_id="PROP-002",
            rule={
                "name": "restrict-smb-external",
                "description": "Block SMB from external IPs.",
                "direction": "INBOUND",
                "action": "DENY",
                "protocol": "TCP",
                "port_range": {"from_port": 445, "to_port": 445},
                "source": [{"cidr": "198.51.100.0/24"}],
                "destination": [],
            },
            justification="Deny SMB from external network to prevent lateral movement.",
            risk_level="LOW",
            confidence=0.88,
            impact_analysis="Blocks 1 denied SMB flow; internal SMB unaffected.",
        ),
    ]
)

_DECISIONS = RuleDecisionList(
    decisions=[
        RuleDecision(
            decision_id="DEC-001",
            proposal_id="PROP-001",
            action="CREATE",
            risk_level="LOW",
            reason="Low risk SSH deny rule targeting known probing source.",
            approval_required=False,
        ),
        RuleDecision(
            decision_id="DEC-002",
            proposal_id="PROP-002",
            action="CREATE",
            risk_level="LOW",
            reason="Low risk SMB deny rule for external network.",
            approval_required=False,
        ),
    ]
)

# Map response_model type → deterministic response
_LLM_RESPONSE_MAP: dict[type, BaseModel] = {
    TrafficAnalysis: _TRAFFIC_ANALYSIS,
    SecurityAssessment: _SECURITY_ASSESSMENT,
    PolicyProposalList: _PROPOSALS,
    RuleDecisionList: _DECISIONS,
}


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def e2e_data_dir(tmp_path: Path) -> Path:
    """Ingest fixture flow logs into real Parquet in a temp directory.

    Returns the data directory containing at least one .parquet file
    ready for DuckDB queries.
    """
    data_dir = tmp_path / "data"

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            ingest_local_files([str(SAMPLE_LOG)])
        )
        assert len(result.records) > 0, f"Ingestion produced 0 records from {SAMPLE_LOG}"

        write_result = loop.run_until_complete(
            write_records(result.records, data_dir, result.source_files)
        )
        assert write_result.records_written > 0, "Parquet write produced 0 records"
    finally:
        loop.close()

    # Verify parquet files exist
    parquet_files = list(data_dir.glob("*.parquet"))
    assert len(parquet_files) >= 1, f"Expected parquet files in {data_dir}"

    return data_dir


@pytest.fixture
def e2e_config(e2e_data_dir: Path) -> PolicyFoundryConfig:
    """Real PolicyFoundryConfig pointing at the temp Parquet data directory."""
    return PolicyFoundryConfig(
        llm={"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test-fake"},
        sources={"log_paths": [str(SAMPLE_LOG)]},
        targets={"security_group_ids": ["sg-e2e-test-001"]},
        output={"data_dir": str(e2e_data_dir)},
    )


@pytest.fixture
def mock_e2e_llm_client() -> MagicMock:
    """Mock LLM client that dispatches on response_model type.

    Returns the correct deterministic Pydantic model for each pipeline stage.
    Also provides get_usage() returning realistic token counts.
    """
    client = MagicMock()

    async def _complete(
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float | None = None,
        stage: str = "unknown",
    ) -> T:
        result = _LLM_RESPONSE_MAP.get(response_model)
        if result is None:
            raise ValueError(
                f"E2E mock LLM has no response for {response_model.__name__}. "
                f"Known types: {list(_LLM_RESPONSE_MAP.keys())}"
            )
        return result  # type: ignore[return-value]

    client.complete = AsyncMock(side_effect=_complete)
    client.get_usage.return_value = TokenUsage(
        prompt_tokens=1200,
        completion_tokens=400,
        total_tokens=1600,
        total_cost=0.0032,
        calls=[
            {"prompt_tokens": 400, "completion_tokens": 120, "total_tokens": 520, "cost": 0.001, "stage": "analyze"},
            {"prompt_tokens": 400, "completion_tokens": 140, "total_tokens": 540, "cost": 0.0011, "stage": "assess"},
            {"prompt_tokens": 400, "completion_tokens": 140, "total_tokens": 540, "cost": 0.0011, "stage": "generate"},
        ],
    )

    return client


@pytest.fixture
def mock_e2e_adapter() -> MagicMock:
    """Mock adapter with no-op operations for E2E testing.

    - get_rules returns empty list (no existing rules)
    - validate approves all proposals
    - capabilities returns standard AWS SG limits
    """
    adapter = MagicMock()
    adapter.get_rules = AsyncMock(return_value=[])
    adapter.validate = AsyncMock(
        return_value=ValidationResult(valid=True, errors=[], warnings=[])
    )
    adapter.capabilities = MagicMock(
        return_value=AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
        )
    )
    return adapter
