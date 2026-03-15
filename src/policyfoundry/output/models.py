"""Output data models for pipeline results and token usage tracking.

Provides :class:`TokenUsage` for accumulating LLM token counts and cost
across pipeline calls, and :class:`PipelineResult` for typed access to
pipeline stage outputs from a raw :class:`PipelineState` dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from policyfoundry.pipeline.schema import (
    PolicyProposal,
    RuleDecision,
    SecurityAssessment,
    TrafficAnalysis,
)
from policyfoundry.pipeline.excel_state import ExcelPipelineState
from policyfoundry.pipeline.state import PipelineState


@dataclass
class TokenUsage:
    """Tracks accumulated LLM token usage and cost across pipeline calls.

    Each call to :meth:`add_call` accumulates prompt/completion/total token
    counts and cost.  The :meth:`to_dict` method serializes to a dict
    suitable for storage in :class:`PipelineState`.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def add_call(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        stage: str | None = None,
    ) -> None:
        """Accumulate token counts and cost from a single LLM call.

        Args:
            prompt_tokens: Number of prompt tokens used.
            completion_tokens: Number of completion tokens generated.
            total_tokens: Total tokens (prompt + completion).
            cost: Estimated cost for this call.
            stage: Optional pipeline stage label (e.g. ``"analyze"``).
        """
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        self.total_cost += cost

        call_record = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
        }
        if stage is not None:
            call_record["stage"] = stage
        self.calls.append(call_record)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for PipelineState storage.

        Returns:
            Dict with accumulated counts and per-call breakdown under
            ``"per_stage"`` key.
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "per_stage": list(self.calls),
        }

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Sum two TokenUsage instances into a new combined instance."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            total_cost=self.total_cost + other.total_cost,
            calls=[*self.calls, *other.calls],
        )


class PipelineResult(BaseModel):
    """Structured result from a pipeline run.

    Wraps a raw :class:`PipelineState` dict with typed Pydantic stage
    outputs for clean serialization and programmatic access.

    Use :meth:`from_state` to construct from a ``PipelineState`` dict.
    """

    run_id: str = ""
    started_at: str = ""
    current_stage: str = ""
    analysis: TrafficAnalysis | None = None
    assessment: SecurityAssessment | None = None
    proposals: list[PolicyProposal] = []
    decisions: list[RuleDecision] = []
    token_usage: TokenUsage | None = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_state(cls, state: PipelineState) -> PipelineResult:
        """Construct a PipelineResult from a PipelineState dict.

        Reconstructs typed Pydantic models from the serialized dicts
        stored in state via ``model_validate()``.

        Args:
            state: A :class:`PipelineState` dict from pipeline execution.

        Returns:
            A fully typed :class:`PipelineResult` instance.
        """
        raw: dict[str, Any] = dict(state)

        analysis = None
        if raw.get("analysis") is not None:
            analysis = TrafficAnalysis.model_validate(raw["analysis"])

        assessment = None
        if raw.get("assessment") is not None:
            assessment = SecurityAssessment.model_validate(raw["assessment"])

        proposals: list[PolicyProposal] = []
        if raw.get("proposals") is not None:
            proposals = [
                PolicyProposal.model_validate(p) for p in raw["proposals"]
            ]

        decisions: list[RuleDecision] = []
        if raw.get("decisions") is not None:
            decisions = [
                RuleDecision.model_validate(d) for d in raw["decisions"]
            ]

        token_usage = None
        usage_raw = raw.get("token_usage")
        if usage_raw is not None and isinstance(usage_raw, dict):
            usage_dict: dict[str, Any] = dict[str, Any](usage_raw)
            token_usage = TokenUsage(
                prompt_tokens=int(usage_dict.get("prompt_tokens", 0)),
                completion_tokens=int(usage_dict.get("completion_tokens", 0)),
                total_tokens=int(usage_dict.get("total_tokens", 0)),
                total_cost=float(usage_dict.get("total_cost", 0.0)),
                calls=list(usage_dict.get("per_stage", [])),
            )

        return cls(
            run_id=raw.get("run_id", ""),
            started_at=raw.get("started_at", ""),
            current_stage=raw.get("current_stage", ""),
            analysis=analysis,
            assessment=assessment,
            proposals=proposals,
            decisions=decisions,
            token_usage=token_usage,
        )


class ExcelPipelineResult(BaseModel):
    """Structured result from an Excel pipeline run.

    Wraps a raw :class:`ExcelPipelineState` dict with typed Pydantic stage
    outputs for clean serialization and programmatic access.

    Use :meth:`from_state` to construct from an ``ExcelPipelineState`` dict.
    """

    run_id: str = ""
    started_at: str = ""
    current_stage: str = ""
    aggregated_flows: list[dict[str, Any]] = []
    subnet_groups: list[dict[str, Any]] = []
    analysis: TrafficAnalysis | None = None
    assessment: SecurityAssessment | None = None
    proposals: list[PolicyProposal] = []
    decisions: list[RuleDecision] = []
    token_usage: TokenUsage | None = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_state(cls, state: ExcelPipelineState) -> ExcelPipelineResult:
        """Construct an ExcelPipelineResult from an ExcelPipelineState dict.

        Reconstructs typed Pydantic models from the serialized dicts
        stored in state via ``model_validate()``.

        Args:
            state: An :class:`ExcelPipelineState` dict from pipeline execution.

        Returns:
            A fully typed :class:`ExcelPipelineResult` instance.
        """
        raw: dict[str, Any] = dict(state)

        analysis = None
        if raw.get("analysis") is not None:
            analysis = TrafficAnalysis.model_validate(raw["analysis"])

        assessment = None
        if raw.get("assessment") is not None:
            assessment = SecurityAssessment.model_validate(raw["assessment"])

        proposals: list[PolicyProposal] = []
        if raw.get("proposals") is not None:
            proposals = [
                PolicyProposal.model_validate(p) for p in raw["proposals"]
            ]

        decisions: list[RuleDecision] = []
        if raw.get("decisions") is not None:
            decisions = [
                RuleDecision.model_validate(d) for d in raw["decisions"]
            ]

        token_usage = None
        usage_raw = raw.get("token_usage")
        if usage_raw is not None and isinstance(usage_raw, dict):
            usage_dict: dict[str, Any] = dict[str, Any](usage_raw)
            token_usage = TokenUsage(
                prompt_tokens=int(usage_dict.get("prompt_tokens", 0)),
                completion_tokens=int(usage_dict.get("completion_tokens", 0)),
                total_tokens=int(usage_dict.get("total_tokens", 0)),
                total_cost=float(usage_dict.get("total_cost", 0.0)),
                calls=list(usage_dict.get("per_stage", [])),
            )

        return cls(
            run_id=raw.get("run_id", ""),
            started_at=raw.get("started_at", ""),
            current_stage=raw.get("current_stage", ""),
            aggregated_flows=raw.get("aggregated_flows", []),
            subnet_groups=raw.get("subnet_groups", []),
            analysis=analysis,
            assessment=assessment,
            proposals=proposals,
            decisions=decisions,
            token_usage=token_usage,
        )
