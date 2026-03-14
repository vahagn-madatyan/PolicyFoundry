"""E2E tests for `policyfoundry analyze` through real file I/O.

Exercises the full path: real flow log fixture → real ingestion →
real Parquet storage → real DuckDB queries → real output formatting.

LLM and adapter boundaries are mocked per D033 — no real API or AWS calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from policyfoundry.main import app


def _e2e_patches(config, llm_client, adapter):
    """Return context managers patching config/LLM/adapter for E2E runs."""
    return (
        patch("policyfoundry.main.load_config", return_value=config),
        patch("policyfoundry.main.create_llm_client", new_callable=AsyncMock, return_value=llm_client),
        patch("policyfoundry.main.AdapterRegistry.get_adapter", return_value=adapter),
    )


class TestE2ERichOutput:
    """E2E tests for `--format rich` through the real pipeline."""

    def test_rich_output_exits_zero(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Full E2E run with Rich output exits 0."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "rich"])
            assert result.exit_code == 0, (
                f"Exit code {result.exit_code}:\n{result.output}\n"
                f"Exception: {result.exception}"
            )

    def test_rich_output_contains_traffic_analysis(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Rich output includes traffic analysis section with real DuckDB data."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "rich"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            assert "Traffic Analysis" in result.output

    def test_rich_output_contains_risk_assessment(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Rich output includes risk level from the security assessment."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "rich"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            assert "MEDIUM" in result.output or "medium" in result.output.lower()

    def test_rich_output_contains_proposals(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Rich output includes policy proposals from the generate stage."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "rich"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            assert "Policy Proposals" in result.output or "restrict-ssh" in result.output

    def test_rich_output_contains_decisions(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Rich output includes decision table."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "rich"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            assert "Decisions" in result.output or "APPROVE" in result.output

    def test_rich_output_contains_token_usage(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Rich output includes token usage footer."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "rich"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            assert "Token Usage" in result.output


class TestE2EJsonOutput:
    """E2E tests for `--format json` through the real pipeline."""

    def test_json_output_exits_zero(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """Full E2E run with JSON output exits 0."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "json"])
            assert result.exit_code == 0, (
                f"Exit code {result.exit_code}:\n{result.output}\n"
                f"Exception: {result.exception}"
            )

    def test_json_output_is_valid_json(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """JSON output parses as valid JSON."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "json"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            parsed = json.loads(result.output)
            assert isinstance(parsed, dict)

    def test_json_output_has_pipeline_result_structure(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """JSON output matches PipelineResult schema keys."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "json"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            parsed = json.loads(result.output)

            # Top-level PipelineResult keys
            assert "run_id" in parsed
            assert "started_at" in parsed
            assert "current_stage" in parsed
            assert "analysis" in parsed
            assert "assessment" in parsed
            assert "proposals" in parsed
            assert "decisions" in parsed
            assert "token_usage" in parsed

    def test_json_output_analysis_populated(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """JSON analysis section has expected subfields."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "json"])
            parsed = json.loads(result.output)
            analysis = parsed["analysis"]
            assert "summary" in analysis
            assert "total_flows" in analysis
            assert "top_talkers" in analysis
            assert "anomalies" in analysis

    def test_json_output_proposals_populated(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """JSON proposals are a non-empty list with rule data."""
        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "json"])
            parsed = json.loads(result.output)
            proposals = parsed["proposals"]
            assert len(proposals) >= 1
            assert "proposal_id" in proposals[0]
            assert "rule" in proposals[0]
            assert "justification" in proposals[0]

    def test_json_output_matches_reference_structure(
        self, cli_runner, e2e_config, mock_e2e_llm_client, mock_e2e_adapter
    ):
        """JSON output matches the reference fixture's structural keys recursively."""
        ref_path = Path(__file__).parent.parent / "fixtures" / "sample_output" / "reference.json"
        reference = json.loads(ref_path.read_text())

        p1, p2, p3 = _e2e_patches(e2e_config, mock_e2e_llm_client, mock_e2e_adapter)
        with p1, p2, p3:
            result = cli_runner.invoke(app, ["analyze", "--format", "json"])
            assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
            actual = json.loads(result.output)

        _assert_structure_matches(reference, actual, path="$")


def _assert_structure_matches(
    reference: object, actual: object, path: str
) -> None:
    """Recursively assert that actual has at least the same keys/types as reference.

    Compares structure (key presence and value types), not exact values.
    Lists are checked by comparing the first element's structure.
    """
    if isinstance(reference, dict):
        assert isinstance(actual, dict), f"{path}: expected dict, got {type(actual).__name__}"
        for key in reference:
            assert key in actual, f"{path}.{key}: missing in actual output"
            _assert_structure_matches(reference[key], actual[key], f"{path}.{key}")
    elif isinstance(reference, list):
        assert isinstance(actual, list), f"{path}: expected list, got {type(actual).__name__}"
        if reference and actual:
            _assert_structure_matches(reference[0], actual[0], f"{path}[0]")
    else:
        # Leaf: just check type category (str, int/float, bool, None)
        if reference is None:
            return  # None in reference is permissive
        ref_type = type(reference)
        act_type = type(actual)
        # Allow int/float interchange
        numeric = (int, float)
        if isinstance(reference, numeric):
            assert isinstance(actual, numeric), (
                f"{path}: expected numeric, got {act_type.__name__}"
            )
        else:
            assert isinstance(actual, ref_type), (
                f"{path}: expected {ref_type.__name__}, got {act_type.__name__}"
            )
