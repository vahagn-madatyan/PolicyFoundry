"""Tests for prompt template formatting."""

from __future__ import annotations

import json

from policyfoundry.adapters.schema import (
    AdapterCapabilities,
    Direction,
    NetworkEndpoint,
    PortRange,
    RuleAction,
    UniversalRule,
)
from policyfoundry.pipeline.prompts.analyze import (
    ANALYZE_SYSTEM_PROMPT,
    format_analyze_user_message,
)
from policyfoundry.pipeline.prompts.assess import (
    ASSESS_SYSTEM_PROMPT,
    format_assess_user_message,
)
from policyfoundry.pipeline.prompts.generate import (
    GENERATE_SYSTEM_PROMPT,
    format_generate_user_message,
)
from policyfoundry.pipeline.schema import PolicyProposal, SecurityAssessment
from policyfoundry.storage.models import (
    DeniedFlowResult,
    TopTalkerResult,
    TrafficByProtocolResult,
    TrafficSummary,
)


class TestAnalyzePrompt:
    """Tests for analyze stage prompt formatting."""

    def test_format_analyze_user_message_produces_valid_json(
        self,
        sample_top_talkers: list[TopTalkerResult],
        sample_denied_flows: list[DeniedFlowResult],
        sample_traffic_by_protocol: list[TrafficByProtocolResult],
        sample_traffic_summary: TrafficSummary,
    ) -> None:
        """format_analyze_user_message returns valid JSON string."""
        result = format_analyze_user_message(
            sample_traffic_summary, sample_top_talkers, sample_denied_flows, sample_traffic_by_protocol,
        )
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_format_analyze_user_message_includes_all_sections(
        self,
        sample_top_talkers: list[TopTalkerResult],
        sample_denied_flows: list[DeniedFlowResult],
        sample_traffic_by_protocol: list[TrafficByProtocolResult],
        sample_traffic_summary: TrafficSummary,
    ) -> None:
        """Output JSON has all 4 DuckDB result categories."""
        result = format_analyze_user_message(
            sample_traffic_summary, sample_top_talkers, sample_denied_flows, sample_traffic_by_protocol,
        )
        parsed = json.loads(result)
        assert "traffic_summary" in parsed
        assert "top_talkers" in parsed
        assert "denied_flows" in parsed
        assert "protocol_breakdown" in parsed

    def test_format_analyze_user_message_empty_data(self) -> None:
        """Empty inputs produce valid JSON with empty arrays."""
        empty_summary = TrafficSummary(
            total_records=0, total_bytes=0,
            unique_sources=0, unique_destinations=0,
            allowed_count=0, denied_count=0,
        )
        result = format_analyze_user_message(empty_summary, [], [], [])
        parsed = json.loads(result)
        assert parsed["top_talkers"] == []
        assert parsed["denied_flows"] == []
        assert parsed["protocol_breakdown"] == []
        assert parsed["traffic_summary"]["total_records"] == 0

    def test_analyze_system_prompt_not_empty(self) -> None:
        """ANALYZE_SYSTEM_PROMPT is a non-empty string with key terms."""
        assert isinstance(ANALYZE_SYSTEM_PROMPT, str)
        assert len(ANALYZE_SYSTEM_PROMPT) > 0

        prompt_lower = ANALYZE_SYSTEM_PROMPT.lower()
        assert "traffic" in prompt_lower
        assert ("analysis" in prompt_lower or "analyze" in prompt_lower) and ("pattern" in prompt_lower)


class TestAssessPrompt:
    """Tests for assess stage prompt formatting."""

    def test_format_assess_user_message_includes_analysis_and_rules(
        self,
        sample_traffic_analysis_dict: dict,
        sample_universal_rules: list[UniversalRule],
    ) -> None:
        """format_assess_user_message includes analysis and rules."""
        result = format_assess_user_message(sample_traffic_analysis_dict, sample_universal_rules)
        parsed = json.loads(result)
        assert "traffic_analysis" in parsed
        assert "current_rules" in parsed
        assert len(parsed["current_rules"]) == len(sample_universal_rules)

    def test_format_assess_user_message_empty_rules(
        self,
        sample_traffic_analysis_dict: dict,
    ) -> None:
        """Empty rules list produces valid JSON with empty rules array."""
        result = format_assess_user_message(sample_traffic_analysis_dict, [])
        parsed = json.loads(result)
        assert parsed["current_rules"] == []

    def test_assess_system_prompt_not_empty(self) -> None:
        """ASSESS_SYSTEM_PROMPT mentions gap analysis, security, risk."""
        assert isinstance(ASSESS_SYSTEM_PROMPT, str)
        assert len(ASSESS_SYSTEM_PROMPT) > 0

        prompt_lower = ASSESS_SYSTEM_PROMPT.lower()
        assert "gap" in prompt_lower
        assert "risk" in prompt_lower
        assert ("security" in prompt_lower and "assessment" in prompt_lower)


class TestGeneratePrompt:
    """Tests for generate stage prompt formatting."""

    def test_format_generate_user_message_includes_capabilities(
        self,
        sample_security_assessment: SecurityAssessment,
        sample_traffic_analysis_dict: dict,
    ) -> None:
        """format_generate_user_message includes adapter capabilities."""
        caps = AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
        )

        result = format_generate_user_message(
            sample_security_assessment.model_dump(), caps, sample_traffic_analysis_dict,
        )
        parsed = json.loads(result)
        assert "adapter_constraints" in parsed
        assert parsed["adapter_constraints"]["vendor"] == "AWS"
        assert parsed["adapter_constraints"]["max_rules_per_direction"] == 60

    def test_format_generate_user_message_includes_assessment(
        self,
        sample_security_assessment: SecurityAssessment,
        sample_traffic_analysis_dict: dict,
    ) -> None:
        """format_generate_user_message includes assessment data."""
        caps = AdapterCapabilities(
            name="aws_sg",
            vendor="AWS",
            supports_deny_rules=False,
            max_rules_per_direction=60,
        )

        result = format_generate_user_message(
            sample_security_assessment.model_dump(), caps, sample_traffic_analysis_dict,
        )
        parsed = json.loads(result)
        assert "security_assessment" in parsed
        assert "traffic_analysis" in parsed

    def test_generate_system_prompt_mentions_proposal_cap(self) -> None:
        """GENERATE_SYSTEM_PROMPT mentions proposal cap and impact."""
        assert isinstance(GENERATE_SYSTEM_PROMPT, str)
        assert len(GENERATE_SYSTEM_PROMPT) > 0

        prompt_lower = GENERATE_SYSTEM_PROMPT.lower()
        assert "20" in GENERATE_SYSTEM_PROMPT
        assert "impact" in prompt_lower
        assert "proposal" in prompt_lower


class TestDecidePrompt:
    """Tests for decide stage prompt formatting."""

    def test_decide_system_prompt_mentions_actions(self) -> None:
        """DECIDE_SYSTEM_PROMPT mentions CREATE, UPDATE, SKIP actions."""
        from policyfoundry.pipeline.prompts.decide import DECIDE_SYSTEM_PROMPT

        assert isinstance(DECIDE_SYSTEM_PROMPT, str)
        assert len(DECIDE_SYSTEM_PROMPT) > 0

        assert "CREATE" in DECIDE_SYSTEM_PROMPT
        assert "UPDATE" in DECIDE_SYSTEM_PROMPT
        assert "SKIP" in DECIDE_SYSTEM_PROMPT

        prompt_lower = DECIDE_SYSTEM_PROMPT.lower()
        assert "risk" in prompt_lower
        assert ("cross-proposal" in prompt_lower or "cross" in prompt_lower)

    def test_format_decide_user_message_summarizes_proposals(
        self,
        sample_policy_proposals: list[PolicyProposal],
    ) -> None:
        """format_decide_user_message summarizes proposals (not full JSON)."""
        from policyfoundry.pipeline.prompts.decide import format_decide_user_message

        result = format_decide_user_message(
            [p.model_dump() for p in sample_policy_proposals]
        )
        parsed = json.loads(result)
        assert "proposals" in parsed
        assert len(parsed["proposals"]) == len(sample_policy_proposals)

        first = parsed["proposals"][0]
        assert "proposal_id" in first
        assert "rule_name" in first
        assert "justification_summary" in first
        # Summaries should not contain the full rule dict
        assert "source" not in first or not isinstance(first.get("source"), list)

    def test_format_decide_user_message_empty_proposals(self) -> None:
        """format_decide_user_message with empty list produces valid JSON."""
        from policyfoundry.pipeline.prompts.decide import format_decide_user_message

        result = format_decide_user_message([])
        parsed = json.loads(result)
        assert "proposals" in parsed
        assert parsed["proposals"] == []
