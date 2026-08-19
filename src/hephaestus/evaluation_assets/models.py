# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Serializable models for the evaluation asset pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional

from src.hephaestus.datasets.embedding_providers import DEFAULT_OPENAI_EMBEDDING_MODEL
from src.hephaestus.datasets.rubric_providers import DEFAULT_OPENAI_RUBRIC_MODEL


class PipelineStage(str, Enum):
    """Ordered stages in the core evaluation asset pipeline."""

    RAW_INPUTS = "raw_inputs"
    PREPARED_INPUTS = "prepared_inputs"
    RUBRIC_EXTRACTION = "rubric_extraction"
    INTENT_CLUSTERING = "intent_clustering"
    COVERAGE_DECISIONS = "coverage_decisions"
    LABEL_INFERENCE = "label_inference"
    SYNTHETIC_COVERAGE = "synthetic_coverage"
    DATASET_SPLITS = "dataset_splits"


STAGE_LABELS = {
    PipelineStage.RAW_INPUTS: "Validate raw inputs",
    PipelineStage.PREPARED_INPUTS: "Prepare canonical inputs",
    PipelineStage.RUBRIC_EXTRACTION: "Create evaluation guidelines",
    PipelineStage.INTENT_CLUSTERING: "Mine intent clusters",
    PipelineStage.COVERAGE_DECISIONS: "Apply coverage decisions",
    PipelineStage.LABEL_INFERENCE: "Infer reviewable labels",
    PipelineStage.SYNTHETIC_COVERAGE: "Optional synthetic coverage",
    PipelineStage.DATASET_SPLITS: "Build dataset splits",
}

CONFIG_STAGE_DEPENDENCIES = {
    "rubric_provider": PipelineStage.RUBRIC_EXTRACTION,
    "rubric_model": PipelineStage.RUBRIC_EXTRACTION,
    "batch_size": PipelineStage.RUBRIC_EXTRACTION,
    "embedding_provider": PipelineStage.INTENT_CLUSTERING,
    "embedding_model": PipelineStage.INTENT_CLUSTERING,
    "cluster_count": PipelineStage.INTENT_CLUSTERING,
    "match_threshold": PipelineStage.COVERAGE_DECISIONS,
    "min_trusted_examples": PipelineStage.COVERAGE_DECISIONS,
    "min_trusted_groups": PipelineStage.COVERAGE_DECISIONS,
    "max_unlabeled_to_trusted_ratio": PipelineStage.COVERAGE_DECISIONS,
    "synthetic_coverage_enabled": PipelineStage.SYNTHETIC_COVERAGE,
    "synthetic_cases_per_cluster": PipelineStage.SYNTHETIC_COVERAGE,
    "split_seed": PipelineStage.DATASET_SPLITS,
}

STAGE_COUNT_KEYS = {
    PipelineStage.RAW_INPUTS: {"feedback_records", "unlabeled_records"},
    PipelineStage.PREPARED_INPUTS: {"prepared_feedback", "prepared_intents"},
    PipelineStage.RUBRIC_EXTRACTION: {
        "feedback_evidence",
        "candidate_guidelines",
        "evaluation_guidelines",
        "trusted_cases",
    },
    PipelineStage.INTENT_CLUSTERING: {"intent_clusters"},
    PipelineStage.COVERAGE_DECISIONS: {
        "matched_clusters",
        "needs_more_feedback_clusters",
        "missing_label_clusters",
        "labeling_queue_clusters",
        "labeling_queue_traces",
    },
    PipelineStage.LABEL_INFERENCE: {"inferred_cases", "review_clusters"},
    PipelineStage.SYNTHETIC_COVERAGE: {
        "synthetic_cases",
        "rejected_synthetic_cases",
    },
    PipelineStage.DATASET_SPLITS: {
        "dataset_cases",
        "train_cases",
        "validation_cases",
        "test_cases",
        "regression_trusted_cases",
        "triage_hold_cases",
    },
}


@dataclass(frozen=True)
class EvaluationAssetConfig:
    """Configuration persisted with one self-contained asset."""

    tenant_id: str
    asset_id: str = "v1"
    rubric_provider: str = "openai"
    rubric_model: str = DEFAULT_OPENAI_RUBRIC_MODEL
    embedding_provider: str = "openai"
    embedding_model: str = DEFAULT_OPENAI_EMBEDDING_MODEL
    cluster_count: int = 50
    batch_size: int = 3
    match_threshold: float = 0.6
    min_trusted_examples: int = 1
    min_trusted_groups: int = 1
    max_unlabeled_to_trusted_ratio: Optional[float] = 20.0
    synthetic_coverage_enabled: bool = False
    synthetic_cases_per_cluster: int = 1
    split_seed: int = 42

    def __post_init__(self) -> None:
        if self.cluster_count < 1:
            raise ValueError("cluster_count must be at least 1")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if not 0.0 <= self.match_threshold <= 1.0:
            raise ValueError("match_threshold must be between 0 and 1")
        if self.min_trusted_examples < 1:
            raise ValueError("min_trusted_examples must be at least 1")
        if self.min_trusted_groups < 0:
            raise ValueError("min_trusted_groups must be at least 0")
        if (
            self.max_unlabeled_to_trusted_ratio is not None
            and self.max_unlabeled_to_trusted_ratio <= 0
        ):
            raise ValueError("max_unlabeled_to_trusted_ratio must be positive")
        if not 1 <= self.synthetic_cases_per_cluster <= 100:
            raise ValueError(
                "synthetic_cases_per_cluster must be between 1 and 100"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration for persistence and APIs."""
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "EvaluationAssetConfig":
        """Load configuration from a validated mapping."""
        return cls(
            tenant_id=str(raw["tenant_id"]),
            asset_id=str(raw.get("asset_id") or "v1"),
            rubric_provider=str(raw.get("rubric_provider") or "openai"),
            rubric_model=str(raw.get("rubric_model") or DEFAULT_OPENAI_RUBRIC_MODEL),
            embedding_provider=str(raw.get("embedding_provider") or "openai"),
            embedding_model=str(
                raw.get("embedding_model") or DEFAULT_OPENAI_EMBEDDING_MODEL
            ),
            cluster_count=int(
                raw["cluster_count"] if raw.get("cluster_count") is not None else 50
            ),
            batch_size=int(
                raw["batch_size"] if raw.get("batch_size") is not None else 3
            ),
            match_threshold=float(
                raw["match_threshold"]
                if raw.get("match_threshold") is not None
                else 0.6
            ),
            min_trusted_examples=int(
                raw["min_trusted_examples"]
                if raw.get("min_trusted_examples") is not None
                else 1
            ),
            min_trusted_groups=int(
                raw["min_trusted_groups"]
                if raw.get("min_trusted_groups") is not None
                else 1
            ),
            max_unlabeled_to_trusted_ratio=(
                float(raw["max_unlabeled_to_trusted_ratio"])
                if raw.get("max_unlabeled_to_trusted_ratio") is not None
                else (
                    None
                    if "max_unlabeled_to_trusted_ratio" in raw
                    else 20.0
                )
            ),
            synthetic_coverage_enabled=bool(
                raw.get("synthetic_coverage_enabled", False)
            ),
            synthetic_cases_per_cluster=int(
                raw["synthetic_cases_per_cluster"]
                if raw.get("synthetic_cases_per_cluster") is not None
                else 1
            ),
            split_seed=int(raw["split_seed"] if raw.get("split_seed") is not None else 42),
        )


@dataclass
class StageState:
    """Persisted state for one pipeline stage."""

    stage: str
    label: str
    status: str = "pending"
    message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class PipelineState:
    """Persisted, restart-safe state for an evaluation asset run."""

    tenant_id: str
    asset_id: str
    status: str = "queued"
    current_stage: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    error: Optional[str] = None
    counts: Dict[str, int] = field(default_factory=dict)
    stages: List[StageState] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize run state for persistence and APIs."""
        return asdict(self)

    @classmethod
    def new(cls, config: EvaluationAssetConfig, timestamp: str) -> "PipelineState":
        """Create the initial ordered stage state."""
        return cls(
            tenant_id=config.tenant_id,
            asset_id=config.asset_id,
            created_at=timestamp,
            updated_at=timestamp,
            stages=[
                StageState(stage=stage.value, label=STAGE_LABELS[stage])
                for stage in PipelineStage
            ],
        )

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PipelineState":
        """Load state written by :meth:`to_dict`."""
        stages = [
            StageState(**dict(item))
            for item in list(raw.get("stages") or [])
            if isinstance(item, Mapping)
        ]
        labels_by_value = {stage.value: label for stage, label in STAGE_LABELS.items()}
        for stage_state in stages:
            if stage_state.stage in labels_by_value:
                stage_state.label = labels_by_value[stage_state.stage]
        existing_stages = {item.stage for item in stages}
        stages.extend(
            StageState(stage=stage.value, label=STAGE_LABELS[stage])
            for stage in PipelineStage
            if stage.value not in existing_stages
        )
        return cls(
            tenant_id=str(raw["tenant_id"]),
            asset_id=str(raw["asset_id"]),
            status=str(raw.get("status") or "queued"),
            current_stage=(
                str(raw["current_stage"]) if raw.get("current_stage") else None
            ),
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            error=str(raw["error"]) if raw.get("error") else None,
            counts={
                str(key): int(value)
                for key, value in dict(raw.get("counts") or {}).items()
            },
            stages=stages,
        )
