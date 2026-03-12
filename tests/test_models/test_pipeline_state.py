"""Tests for PipelineState TypedDict."""

from __future__ import annotations

from typing import TYPE_CHECKING

from policyfoundry.pipeline.state import PipelineState


def test_pipeline_state_creation() -> None:
    """PipelineState can be created with run_id, started_at, current_stage."""
    state: PipelineState = {
        "run_id": "run-001",
        "started_at": "2026-03-08T12:00:00Z",
        "current_stage": "ingestion",
    }
    assert state["run_id"] == "run-001"
    assert state["started_at"] == "2026-03-08T12:00:00Z"
    assert state["current_stage"] == "ingestion"


def test_flow_log_path_is_string() -> None:
    """PipelineState stores flow_log_path as a string path, not raw data."""
    state: PipelineState = {
        "flow_log_path": "/data/logs/vpc-flow-2026-03-08.parquet",
    }
    assert isinstance(state["flow_log_path"], str)
    assert state["flow_log_path"] == "/data/logs/vpc-flow-2026-03-08.parquet"


def test_sg_ids_is_string_list() -> None:
    """PipelineState stores sg_ids as a list of string SG IDs."""
    state: PipelineState = {
        "sg_ids": ["sg-abc123", "sg-def456"],
    }
    assert isinstance(state["sg_ids"], list)
    assert all(isinstance(sg, str) for sg in state["sg_ids"])


def test_partial_construction() -> None:
    """PipelineState with total=False allows partial construction."""
    state: PipelineState = {"run_id": "run-002"}
    assert state["run_id"] == "run-002"
    assert "current_stage" not in state


def test_stage_outputs_are_dicts() -> None:
    """PipelineState stage outputs are typed as dict/list[dict]."""
    state: PipelineState = {
        "analysis": {"summary": "test", "total_flows": 100},
        "proposals": [
            {"proposal_id": "p1", "confidence": 0.9},
            {"proposal_id": "p2", "confidence": 0.8},
        ],
    }
    assert isinstance(state["analysis"], dict)
    assert isinstance(state["proposals"], list)
    assert len(state["proposals"]) == 2


def test_pipeline_state_is_dict() -> None:
    """PipelineState is a TypedDict and thus isinstance(state, dict) is True."""
    state: PipelineState = {"run_id": "run-003"}
    assert isinstance(state, dict)
