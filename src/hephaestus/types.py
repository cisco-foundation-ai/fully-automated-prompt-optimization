# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Mapping, Optional

_EVALUATION_TRUST_TIERS = frozenset(
    {
        "trusted_feedback",
        "inferred_from_trusted_feedback",
        "synthetic_from_trusted_rubric",
    }
)


@dataclass
class PromptRenderResult:
    prompt_text: str
    prompt_messages: List[Dict[str, str]]
    diagnostics: List[str]


@dataclass
class EvalCase:
    case_id: str
    task_type: str
    context: Dict[str, str]
    expected: Dict[str, Any]
    metadata: Dict[str, Any]
    messages_template: Optional[Dict[str, str]] = None
    prompt_template_path: Optional[str] = None


@dataclass
class ChainConfig:
    """Configuration for a LangGraph chain."""

    path: str
    fn: str = "build_chain"
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalCaseResult:
    """Result of evaluating a single case through the chain and scorer."""

    case_id: str
    task_type: str
    diagnostics: List[str]
    score_breakdown: Dict[str, Any]
    composite_score: float
    output_text: str
    step_outputs: Dict[str, Any]
    step_timings: List[List] = field(default_factory=list)

    # Agentic workflow tracking (MCP integration)
    tool_call_history: Optional[List[Dict[str, Any]]] = None
    total_tool_calls: int = 0
    failed_tool_calls: int = 0

    # Persisted execution state contains only privacy-safe, allowlisted facts.
    execution_status: Literal["succeeded", "failed"] = "succeeded"
    execution_error: Optional[Dict[str, str]] = None
    evaluation_provenance: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.execution_status not in {"succeeded", "failed"}:
            raise ValueError("execution_status must be 'succeeded' or 'failed'")
        if self.execution_status == "succeeded" and self.execution_error is not None:
            raise ValueError("succeeded EvalCaseResult cannot carry execution_error")
        if self.execution_status == "failed" and self.execution_error is None:
            raise ValueError("failed EvalCaseResult requires execution_error")
        if self.execution_error is not None:
            from src.hephaestus.runs.errors import validate_execution_error

            self.execution_error = validate_execution_error(self.execution_error)
        self.evaluation_provenance = _sanitize_evaluation_provenance(
            self.evaluation_provenance
        )


@dataclass
class EvalProgress:
    """Snapshot of evaluation progress."""

    status: str  # "running" | "completed" | "degraded" | "failed"
    total_cases: int
    completed_cases: int
    started_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    avg_composite_score: Optional[float]
    score_breakdown_averages: Dict[str, float]
    failed_case_ids: List[str]
    in_flight_case_ids: List[str] = field(default_factory=list)
    run_id: str = ""
    successful_cases: int = 0
    attempted_case_ids: List[str] = field(default_factory=list)
    successful_case_ids: List[str] = field(default_factory=list)
    trust_tier_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class EvalConfig:
    tenant_id: str
    provider: str
    provider_settings: Dict[str, Any]
    dataset_path: str
    scoring_profile: Dict[str, Any]
    output_dir: str
    chain: ChainConfig
    max_workers: Optional[int] = None
    run_id: Optional[str] = None
    mcp: Optional[Any] = None  # MCPConfig from mcp.types, but avoid circular import
    comparison_variant_dimensions: List[str] = field(default_factory=list)


def _sanitize_evaluation_provenance(value: Mapping[str, Any] | None) -> Dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    trust_tier = value.get("trust_tier")
    if not isinstance(trust_tier, str) or trust_tier not in _EVALUATION_TRUST_TIERS:
        return {}
    return {"trust_tier": trust_tier}
