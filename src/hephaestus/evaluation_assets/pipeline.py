# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Deterministic, resumable core pipeline for evaluation asset creation."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence

from src.hephaestus.datasets.embedding_providers import OpenAIEmbeddingProvider
from src.hephaestus.datasets.evaluation_assets import (
    filter_synthetic_cases,
    sha256_file,
    split_cases_by_group,
    validate_fapo_case,
    write_coverage_report,
    write_jsonl,
)
from src.hephaestus.datasets.intent_assets import (
    CoveragePolicy,
    IntentCluster,
    IntentMatch,
    IntentRecord,
    TrustedIntent,
    build_intent_match_texts,
    cluster_records_fixed_count,
    cluster_to_dict,
    dense_vectors_to_sparse,
    match_clusters_to_trusted_intents,
    match_to_dict,
)
from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.evaluation_assets.input_contract import validate_input_records
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.workspace import (
    EvaluationAssetLayout,
    atomic_write_json,
    utc_now,
)

LABELING_QUEUE_SAMPLE_RATIO = 0.1
LABELING_QUEUE_MAX_PER_CLUSTER = 3

FEEDBACK_PROMPT = """\
Create reviewable evaluation rubrics from explicit user feedback. Return one JSON
object with a `rubrics` array preserving every `record_id`. User feedback is
trusted evidence; the previous assistant output is context, not an answer key.
Each rubric must contain record_id, intent_label, confidence (0..1), must,
must_not, should, deterministic_checks, tool_expectations, and reference_output.
The must, must_not, and should fields must be arrays of strings;
deterministic_checks must be an array; tool_expectations must be a JSON object,
never an array or string; and reference_output must be a string or null.
Never invent environment facts, private identifiers, tool results, or unsupported
correctness requirements.
"""

INFERENCE_PROMPT = """\
Infer reviewable rubrics for unlabeled intent clusters using only the supplied
trusted feedback rubric as correctness evidence. Return one JSON object with a
`rubrics` array preserving every `cluster_id`. Each item must contain cluster_id,
intent_label, confidence (0..1), must, must_not, should, deterministic_checks,
tool_expectations, and reference_output. Representative unlabeled requests may
shape slots and wording but are not correctness evidence. The must, must_not,
and should fields must be arrays of strings; deterministic_checks must be an
array; tool_expectations must be a JSON object, never an array or string; and
reference_output must be a string or null.
"""

SYNTHETIC_PROMPT = """\
Create exactly `case_count` synthetic evaluation inputs for each supplied,
already-matched intent cluster. Return one JSON object with a `cases` array;
every case must preserve its `cluster_id` and contain task_type, user_input, and
conversation_context. Requests must be realistic, self-contained,
non-attributable, mutually distinct, and materially different from
representatives. Do not include an answer, rubric, feedback rationale, private
identifier, secret, or invented tool result.
"""

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DEFAULT_REGRESSION_FRACTION = 0.2


class RubricProvider(Protocol):
    """JSON generation interface used by the pipeline."""

    model: str

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Return one JSON object."""


class EmbeddingProvider(Protocol):
    """Embedding interface used by clustering and coverage."""

    model: str

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one vector per input."""


class EvaluationAssetPipeline:
    """Run the fixed evaluation-asset stage graph with persisted checkpoints."""

    def __init__(
        self,
        layout: EvaluationAssetLayout,
        rubric_provider: Optional[RubricProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ) -> None:
        self.layout = layout
        self.config = layout.load_config()
        self.lineage = (
            json.loads(layout.lineage_path.read_text(encoding="utf-8"))
            if layout.lineage_path.is_file()
            else {}
        )
        if self.config.rubric_provider != "openai" and rubric_provider is None:
            raise ValueError(f"Unsupported rubric provider: {self.config.rubric_provider}")
        if (
            self.config.embedding_provider not in {"openai", "tfidf"}
            and embedding_provider is None
        ):
            raise ValueError(
                f"Unsupported embedding provider: {self.config.embedding_provider}"
            )
        self.rubric_provider = rubric_provider or OpenAIRubricProvider(
            model=self.config.rubric_model,
            # Reasoning models (e.g. gpt-5.x) count reasoning tokens against this
            # budget before any JSON is emitted. 8192 could be exhausted by a long
            # reasoning trace, yielding a 400 / empty response that fails the whole
            # rubric_extraction stage. Give reasoning ample headroom over the output.
            max_output_tokens=16384,
        )
        self.embedding_provider = embedding_provider
        if self.embedding_provider is None and self.config.embedding_provider == "openai":
            self.embedding_provider = OpenAIEmbeddingProvider(
                model=self.config.embedding_model
            )

    @classmethod
    def create(
        cls,
        tenants_root: Path,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        rubric_provider: Optional[RubricProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ) -> "EvaluationAssetPipeline":
        """Create a self-contained workspace by copying both source files."""
        layout = EvaluationAssetLayout(
            tenants_root=tenants_root,
            tenant_id=config.tenant_id,
            asset_id=config.asset_id,
        )
        layout.initialize(config, feedback_source, unlabeled_source)
        return cls(layout, rubric_provider=rubric_provider, embedding_provider=embedding_provider)

    def run(self) -> PipelineState:
        """Run or resume all incomplete stages."""
        state = self.layout.load_state()
        state.status = "running"
        state.error = None
        self.layout.save_state(state)
        self.layout.append_event("pipeline_started")

        for stage in PipelineStage:
            stage_state = next(item for item in state.stages if item.stage == stage.value)
            if stage_state.status == "completed":
                continue
            state.current_stage = stage.value
            stage_state.status = "running"
            stage_state.started_at = utc_now()
            stage_state.completed_at = None
            stage_state.message = ""
            self.layout.save_state(state)
            self.layout.append_event("stage_started", {"stage": stage.value})
            try:
                counts = self._run_stage(stage)
            except Exception as exc:
                stage_state.status = "failed"
                stage_state.message = str(exc)
                state.status = "failed"
                state.error = str(exc)
                self.layout.save_state(state)
                self.layout.append_event(
                    "stage_failed",
                    {"stage": stage.value, "error": str(exc)},
                )
                raise
            state.counts.update(counts)
            stage_state.status = "completed"
            stage_state.completed_at = utc_now()
            stage_state.message = _stage_message(stage, counts)
            self.layout.save_state(state)
            self.layout.append_event(
                "stage_completed",
                {"stage": stage.value, "counts": counts},
            )

        state.status = "completed"
        state.current_stage = None
        state.error = None
        self.layout.save_state(state)
        self.layout.append_event("pipeline_completed", {"counts": state.counts})
        return state

    def _run_stage(self, stage: PipelineStage) -> Dict[str, int]:
        handlers = {
            PipelineStage.RAW_INPUTS: self._validate_raw_inputs,
            PipelineStage.PREPARED_INPUTS: self._prepare_inputs,
            PipelineStage.RUBRIC_EXTRACTION: self._extract_rubrics,
            PipelineStage.INTENT_CLUSTERING: self._cluster_intents,
            PipelineStage.COVERAGE_DECISIONS: self._decide_coverage,
            PipelineStage.LABEL_INFERENCE: self._infer_labels,
            PipelineStage.SYNTHETIC_COVERAGE: self._generate_synthetic_coverage,
            PipelineStage.DATASET_SPLITS: self._build_splits,
        }
        return handlers[stage]()

    def _validate_raw_inputs(self) -> Dict[str, int]:
        feedback = _load_jsonl(self.layout.feedback_path)
        unlabeled = _load_jsonl(self.layout.unlabeled_path)
        if not feedback:
            raise ValueError("labeled feedback input is empty")
        if not unlabeled:
            raise ValueError("unlabeled input is empty")
        validate_input_records(
            feedback,
            labeled=True,
            path=self.layout.feedback_path,
        )
        validate_input_records(
            unlabeled,
            labeled=False,
            path=self.layout.unlabeled_path,
        )
        manifest = {
            "inputs": {
                "labeled_feedback": {
                    "file": self.layout.feedback_path.name,
                    "rows": len(feedback),
                    "sha256": sha256_file(self.layout.feedback_path),
                },
                "unlabeled": {
                    "file": self.layout.unlabeled_path.name,
                    "rows": len(unlabeled),
                    "sha256": sha256_file(self.layout.unlabeled_path),
                },
            }
        }
        atomic_write_json(
            self.layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json"),
            manifest,
        )
        return {"feedback_records": len(feedback), "unlabeled_records": len(unlabeled)}

    def _prepare_inputs(self) -> Dict[str, int]:
        feedback_rows = _load_jsonl(self.layout.feedback_path)
        unlabeled_rows = _load_jsonl(self.layout.unlabeled_path)
        normalized = [_normalize_feedback(row) for row in feedback_rows]
        intents = [_normalize_intent(row) for row in unlabeled_rows]
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "normalized_feedback.jsonl",
            ),
            normalized,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            ),
            intents,
        )
        return {"prepared_feedback": len(normalized), "prepared_intents": len(intents)}

    def _extract_rubrics(self) -> Dict[str, int]:
        normalized = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "normalized_feedback.jsonl",
            )
        )
        added_record_ids = {
            str(value)
            for value in self.lineage.get("added_labeled_record_ids", [])
        }
        incremental = bool(self.lineage)
        rubric_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_rubrics.jsonl",
        )
        intent_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_intents.jsonl",
        )
        case_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_cases.jsonl",
        )
        existing_rubrics = _load_jsonl(rubric_path) if incremental else []
        existing_intents = _load_jsonl(intent_path) if incremental else []
        existing_cases = _load_jsonl(case_path) if incremental else []
        pending = (
            [
                row
                for row in normalized
                if str(row["record_id"]) in added_record_ids
            ]
            if incremental
            else normalized
        )
        new_rubrics: List[Dict[str, Any]] = []
        for batch in _batches(pending, self.config.batch_size):
            response = self.rubric_provider.generate_json(
                FEEDBACK_PROMPT,
                {
                    "records": [
                        {
                            "record_id": row["record_id"],
                            "task_type": row["task_type"],
                            "user_input": row["user_input"],
                            "assistant_output": row["assistant_output"],
                            "tool_calls": row["tool_calls"],
                            "feedback": row["feedback"],
                        }
                        for row in batch
                    ]
                },
            )
            returned = _indexed_items(response, "rubrics", "record_id")
            for row in batch:
                record_id = str(row["record_id"])
                if record_id not in returned:
                    raise ValueError(f"Rubric response omitted {record_id}")
                new_rubrics.append(
                    _normalize_rubric(
                        returned[record_id],
                        "record_id",
                        record_id,
                        "human_feedback",
                        self.config.rubric_model,
                        review_status=None,
                    )
                )

        rubrics = _replace_by_key(
            existing_rubrics,
            new_rubrics,
            key="record_id",
        )
        rubric_by_id = {row["record_id"]: row for row in rubrics}
        new_trusted_intents = [
            {
                "intent_id": row["record_id"],
                "label": rubric_by_id[row["record_id"]]["intent_label"],
                "texts": [
                    row["user_input"],
                    " ".join(
                        rubric_by_id[row["record_id"]]["must"]
                        + rubric_by_id[row["record_id"]]["must_not"]
                    ),
                ],
                "route": row["route"],
                "metadata": {
                    "trusted_example_count": 1,
                    "trusted_group_count": 1,
                    "feedback_polarity": row["feedback"]["polarity"],
                },
            }
            for row in pending
        ]
        new_trusted_cases = [
            _trusted_case(
                row,
                rubric_by_id[row["record_id"]],
                self.config.asset_id,
            )
            for row in pending
        ]
        trusted_intents = _replace_by_key(
            existing_intents,
            new_trusted_intents,
            key="intent_id",
        )
        trusted_cases = _replace_by_key(
            [_case_for_asset(row, self.config.asset_id) for row in existing_cases],
            new_trusted_cases,
            key="case_id",
        )
        write_jsonl(
            rubric_path,
            rubrics,
        )
        write_jsonl(
            intent_path,
            trusted_intents,
        )
        write_jsonl(
            case_path,
            trusted_cases,
        )
        return {"feedback_rubrics": len(rubrics), "trusted_cases": len(trusted_cases)}

    def _cluster_intents(self) -> Dict[str, int]:
        rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            )
        )
        records = [_intent_record(row) for row in rows]
        vectors = None
        if self.embedding_provider is not None:
            vectors = dense_vectors_to_sparse(
                [record.record_id for record in records],
                self.embedding_provider.embed_texts(
                    [record.text for record in records]
                ),
            )
        clusters = cluster_records_fixed_count(
            records,
            cluster_count=self.config.cluster_count,
            vectors=vectors,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            ),
            [cluster_to_dict(cluster) for cluster in clusters],
        )
        if self.lineage:
            self._write_cluster_lineage(clusters)
        return {"intent_clusters": len(clusters)}

    def _write_cluster_lineage(
        self,
        clusters: Sequence[IntentCluster],
    ) -> None:
        parent_asset_id = str(self.lineage.get("parent_asset_id") or "")
        if not parent_asset_id:
            return
        parent_rows = _load_jsonl(
            self.layout.parent_snapshot / "parent_intent_inventory.jsonl"
        )
        previous = [_intent_cluster(row) for row in parent_rows]
        rows = _cluster_lineage(previous, clusters)
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "cluster_lineage.jsonl",
            ),
            rows,
        )

    def _changed_cluster_ids(
        self,
        matches: Sequence[IntentMatch],
    ) -> set[str]:
        if self.lineage.get("clustering_mode") != "keep":
            return {match.cluster_id for match in matches}
        snapshot = (
            self.layout.parent_snapshot / "parent_intent_matches.jsonl"
        )
        if not snapshot.is_file():
            return {match.cluster_id for match in matches}
        previous = {
            match.cluster_id: match
            for match in (
                _intent_match(row)
                for row in _load_jsonl(
                    snapshot
                )
            )
        }
        return {
            match.cluster_id
            for match in matches
            if match.cluster_id not in previous
            or previous[match.cluster_id].status != match.status
            or previous[match.cluster_id].matched_intent_id
            != match.matched_intent_id
        }

    def _decide_coverage(self) -> Dict[str, int]:
        intent_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            )
        )
        trusted_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "trusted_intents.jsonl",
            )
        )
        cluster_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            )
        )
        records = [_intent_record(row) for row in intent_rows]
        trusted = [_trusted_intent(row) for row in trusted_rows]
        clusters = [_intent_cluster(row) for row in cluster_rows]
        match_texts = build_intent_match_texts(clusters, records, trusted)
        vectors = None
        if self.embedding_provider is not None:
            vectors = dense_vectors_to_sparse(
                list(match_texts),
                self.embedding_provider.embed_texts(
                    [match_texts[key] for key in match_texts]
                ),
            )
        policy = CoveragePolicy(
            min_match_score=self.config.match_threshold,
            min_trusted_examples=self.config.min_trusted_examples,
            min_trusted_groups=self.config.min_trusted_groups,
            max_unlabeled_to_trusted_ratio=self.config.max_unlabeled_to_trusted_ratio,
        )
        matches = match_clusters_to_trusted_intents(
            clusters,
            records,
            trusted,
            coverage_policy=policy,
            vectors=vectors,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "intent_matches.jsonl",
            ),
            [match_to_dict(match) for match in matches],
        )
        write_coverage_report(
            self.layout.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "coverage_report.md",
            ),
            clusters,
            matches,
        )
        labeling_queue = _build_labeling_queue(
            clusters,
            matches,
            intent_rows,
            sample_ratio=LABELING_QUEUE_SAMPLE_RATIO,
            max_per_cluster=LABELING_QUEUE_MAX_PER_CLUSTER,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "review_queue/labeling_queue.jsonl",
            ),
            labeling_queue,
        )
        statuses = Counter(match.status for match in matches)
        return {
            "matched_clusters": statuses["matched_trusted_intent"],
            "needs_more_feedback_clusters": statuses[
                "needs_more_trusted_examples"
            ],
            "missing_label_clusters": statuses["missing_or_weak_labels"],
            "labeling_queue_clusters": len(
                {row["cluster_id"] for row in labeling_queue}
            ),
            "labeling_queue_traces": len(labeling_queue),
        }

    def _infer_labels(self) -> Dict[str, int]:
        intent_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            )
        )
        normalized = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "normalized_feedback.jsonl",
            )
        )
        raw_rows = _load_jsonl(self.layout.unlabeled_path)
        feedback_rubrics = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "feedback_rubrics.jsonl",
            )
        )
        clusters = [
            _intent_cluster(row)
            for row in _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.INTENT_CLUSTERING,
                    "intent_inventory.jsonl",
                )
            )
        ]
        matches = [
            _intent_match(row)
            for row in _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.COVERAGE_DECISIONS,
                    "intent_matches.jsonl",
                )
            )
        ]
        row_by_id = {row["record_id"]: row for row in intent_rows}
        normalized_by_id = {row["record_id"]: row for row in normalized}
        feedback_by_id = {row["record_id"]: row for row in feedback_rubrics}
        match_by_cluster = {match.cluster_id: match for match in matches}
        matched = [
            cluster
            for cluster in clusters
            if match_by_cluster[cluster.cluster_id].status
            == "matched_trusted_intent"
        ]
        changed_cluster_ids = self._changed_cluster_ids(matches)
        cluster_rubrics: List[Dict[str, Any]] = []
        if (
            self.lineage.get("clustering_mode") == "keep"
            and (
                self.layout.parent_snapshot
                / "parent_inferred_cluster_rubrics.jsonl"
            ).is_file()
        ):
            cluster_rubrics = [
                row
                for row in _load_jsonl(
                    self.layout.parent_snapshot
                    / "parent_inferred_cluster_rubrics.jsonl"
                )
                if str(row["cluster_id"]) not in changed_cluster_ids
                and str(row["cluster_id"]) in match_by_cluster
                and match_by_cluster[str(row["cluster_id"])].status
                == "matched_trusted_intent"
            ]
        changed_matched = [
            cluster
            for cluster in matched
            if cluster.cluster_id in changed_cluster_ids
        ]
        for batch in _batches(changed_matched, self.config.batch_size):
            response = self.rubric_provider.generate_json(
                INFERENCE_PROMPT,
                {
                    "clusters": [
                        {
                            "cluster_id": cluster.cluster_id,
                            "route": cluster.route,
                            "representative_requests": [
                                row_by_id[record_id]["user_input"]
                                for record_id in cluster.representative_ids
                            ],
                            "trusted_request": normalized_by_id[
                                str(match_by_cluster[cluster.cluster_id].matched_intent_id)
                            ]["user_input"],
                            "trusted_rubric": feedback_by_id[
                                str(match_by_cluster[cluster.cluster_id].matched_intent_id)
                            ],
                            "match_score": match_by_cluster[cluster.cluster_id].score,
                        }
                        for cluster in batch
                    ]
                },
            )
            returned = _indexed_items(response, "rubrics", "cluster_id")
            for cluster in batch:
                if cluster.cluster_id not in returned:
                    raise ValueError(
                        f"Inferred rubric response omitted {cluster.cluster_id}"
                    )
                cluster_rubrics.append(
                    _normalize_rubric(
                        returned[cluster.cluster_id],
                        "cluster_id",
                        cluster.cluster_id,
                        "inferred_from_trusted_feedback",
                        self.config.rubric_model,
                    )
                )

        labels, inferred_cases = _inferred_cases(
            clusters,
            matches,
            intent_rows,
            raw_rows,
            cluster_rubrics,
            self.config,
        )
        trusted_record_ids = {
            str(row["record_id"]) for row in normalized
        }
        labels = [
            row for row in labels if str(row["record_id"]) not in trusted_record_ids
        ]
        inferred_cases = [
            row
            for row in inferred_cases
            if str(row["case_id"]).removeprefix("inferred-")
            not in trusted_record_ids
        ]
        missing = _missing_clusters(clusters, matches, row_by_id)
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_unlabeled_cluster_rubrics.jsonl",
            ),
            cluster_rubrics,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_unlabeled_labels.jsonl",
            ),
            labels,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "missing_labeled_feedback_clusters.jsonl",
            ),
            missing,
        )
        _write_missing_report(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "missing_labeled_feedback_report.md",
            ),
            missing,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_cases.jsonl",
            ),
            inferred_cases,
        )
        return {
            "inferred_cases": len(inferred_cases),
            "review_clusters": len(missing),
        }

    def _build_splits(self) -> Dict[str, int]:
        trusted = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "trusted_cases.jsonl",
            )
        )
        inferred = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_cases.jsonl",
            )
        )
        synthetic = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_cases.jsonl",
            )
        )
        if self.lineage:
            payloads = _incremental_split_payloads(
                self.layout,
                trusted,
                inferred,
                synthetic,
                seed=self.config.split_seed,
            )
        else:
            payloads = _default_split_payloads(
                trusted,
                inferred,
                synthetic,
                seed=self.config.split_seed,
            )
        for name, rows in payloads.items():
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    f"{name}.jsonl",
                ),
                rows,
            )

        input_manifest = json.loads(
            self.layout.artifact_path(
                PipelineStage.RAW_INPUTS,
                "input_manifest.json",
            ).read_text(encoding="utf-8")
        )
        manifest = {
            "asset_id": self.config.asset_id,
            "tenant_id": self.config.tenant_id,
            "providers": {
                "rubric_provider": self.config.rubric_provider,
                "rubric_model": self.config.rubric_model,
                "embedding_provider": self.config.embedding_provider,
                "embedding_model": self.config.embedding_model,
            },
            "clustering": {
                "algorithm": "deterministic_cosine_fixed_count_v1",
                "requested_clusters": self.config.cluster_count,
            },
            "coverage": {
                "match_threshold": self.config.match_threshold,
                "min_trusted_examples": self.config.min_trusted_examples,
                "min_trusted_groups": self.config.min_trusted_groups,
                "max_unlabeled_to_trusted_ratio": (
                    self.config.max_unlabeled_to_trusted_ratio
                ),
                "labeling_queue": {
                    "statuses": [
                        "needs_more_trusted_examples",
                        "missing_or_weak_labels",
                    ],
                    "sample_ratio": LABELING_QUEUE_SAMPLE_RATIO,
                    "minimum_per_cluster": 1,
                    "maximum_per_cluster": LABELING_QUEUE_MAX_PER_CLUSTER,
                    "selection": "deterministic_centroid_nearest",
                },
            },
            "synthetic_coverage": {
                "enabled": self.config.synthetic_coverage_enabled,
                "cases_per_cluster": self.config.synthetic_cases_per_cluster,
            },
            "regression_gate": {
                "source": "trusted_feedback",
                "fraction": DEFAULT_REGRESSION_FRACTION,
                "selection": "deterministic_group_safe_random",
                "seed": self.config.split_seed,
            },
            "source_hashes": {
                name: details["sha256"]
                for name, details in input_manifest["inputs"].items()
            },
            "split_counts": {name: len(rows) for name, rows in payloads.items()},
            "review_policy": {
                "feedback_rubrics": "accepted_without_review",
                "inferred_labels": "review_required",
                "coverage_labeling_queue": "human_label_required",
                "regression_gate": "automatic_trusted_feedback_holdout",
                "regression_group_conflicts": "triage_hold",
            },
        }
        if self.lineage:
            manifest["lineage"] = dict(self.lineage)
        atomic_write_json(
            self.layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "dataset_manifest.json",
            ),
            manifest,
        )
        atomic_write_json(self.layout.manifest_path, manifest)
        return {
            "dataset_cases": len(trusted) + len(inferred) + len(synthetic),
            "train_cases": len(payloads["train"]),
            "validation_cases": len(payloads["validation"]),
            "test_cases": len(payloads["test"]),
            "regression_trusted_cases": len(payloads["regression_trusted"]),
            "triage_hold_cases": len(payloads["triage_hold"]),
        }

    def _generate_synthetic_coverage(self) -> Dict[str, int]:
        if not self.config.synthetic_coverage_enabled:
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.SYNTHETIC_COVERAGE,
                    "synthetic_candidates.jsonl",
                ),
                [],
            )
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.SYNTHETIC_COVERAGE,
                    "rejected_synthetic.jsonl",
                ),
                [],
            )
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.SYNTHETIC_COVERAGE,
                    "synthetic_filter_issues.jsonl",
                ),
                [],
            )
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.SYNTHETIC_COVERAGE,
                    "synthetic_cases.jsonl",
                ),
                [],
            )
            return {
                "synthetic_cases": 0,
                "rejected_synthetic_cases": 0,
            }

        intent_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            )
        )
        cluster_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            )
        )
        rubric_rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_unlabeled_cluster_rubrics.jsonl",
            )
        )
        clusters = [_intent_cluster(row) for row in cluster_rows]
        row_by_id = {row["record_id"]: row for row in intent_rows}
        rubric_by_cluster = {row["cluster_id"]: row for row in rubric_rows}
        matched = [
            cluster for cluster in clusters if cluster.cluster_id in rubric_by_cluster
        ]
        existing_synthetic: List[Dict[str, Any]] = []
        if (
            self.lineage.get("clustering_mode") == "keep"
            and (
                self.layout.parent_snapshot / "parent_synthetic_cases.jsonl"
            ).is_file()
        ):
            matches = [
                _intent_match(row)
                for row in _load_jsonl(
                    self.layout.artifact_path(
                        PipelineStage.COVERAGE_DECISIONS,
                        "intent_matches.jsonl",
                    )
                )
            ]
            changed_cluster_ids = self._changed_cluster_ids(matches)
            existing_synthetic = [
                _case_for_asset(row, self.config.asset_id)
                for row in _load_jsonl(
                    self.layout.parent_snapshot
                    / "parent_synthetic_cases.jsonl"
                )
                if str((row.get("metadata") or {}).get("source_cluster"))
                not in changed_cluster_ids
                and str((row.get("metadata") or {}).get("source_cluster"))
                in rubric_by_cluster
            ]
            matched = [
                cluster
                for cluster in matched
                if cluster.cluster_id in changed_cluster_ids
            ]
        candidates: List[Dict[str, Any]] = []
        for batch in _batches(matched, self.config.batch_size):
            response = self.rubric_provider.generate_json(
                SYNTHETIC_PROMPT,
                {
                    "clusters": [
                        {
                            "cluster_id": cluster.cluster_id,
                            "route": cluster.route,
                            "representatives": [
                                row_by_id[record_id]["user_input"]
                                for record_id in cluster.representative_ids
                            ],
                            "rubric": rubric_by_cluster[cluster.cluster_id],
                            "case_count": self.config.synthetic_cases_per_cluster,
                        }
                        for cluster in batch
                    ]
                },
            )
            returned = _grouped_items(response, "cases", "cluster_id")
            for cluster in batch:
                generated_cases = returned.get(cluster.cluster_id, [])
                if (
                    len(generated_cases)
                    != self.config.synthetic_cases_per_cluster
                ):
                    raise ValueError(
                        "Synthetic response returned "
                        f"{len(generated_cases)} cases for {cluster.cluster_id}; "
                        f"expected {self.config.synthetic_cases_per_cluster}"
                    )
                for candidate_index, generated in enumerate(
                    generated_cases,
                    start=1,
                ):
                    candidates.append(
                        _synthetic_case(
                            cluster,
                            generated,
                            rubric_by_cluster[cluster.cluster_id],
                            self.config.asset_id,
                            candidate_index,
                        )
                    )
        trusted = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "trusted_cases.jsonl",
            )
        )
        inferred = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_cases.jsonl",
            )
        )
        filtered = filter_synthetic_cases(
            candidates,
            existing_cases=trusted + inferred + existing_synthetic,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_candidates.jsonl",
            ),
            candidates,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "rejected_synthetic.jsonl",
            ),
            filtered.rejected,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_filter_issues.jsonl",
            ),
            [
                {
                    "case_id": issue.case_id,
                    "code": issue.code,
                    "message": issue.message,
                }
                for issue in filtered.issues
            ],
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_cases.jsonl",
            ),
            existing_synthetic + filtered.accepted,
        )
        return {
            "synthetic_cases": len(existing_synthetic) + len(filtered.accepted),
            "rejected_synthetic_cases": len(filtered.rejected),
        }


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object at {path}:{line_number}")
        rows.append(row)
    return rows


def _replace_by_key(
    existing: Sequence[Mapping[str, Any]],
    additions: Sequence[Mapping[str, Any]],
    *,
    key: str,
) -> List[Dict[str, Any]]:
    """Return a stable union where additions replace matching existing rows."""
    added_keys = {str(row[key]) for row in additions}
    rows = [
        dict(row)
        for row in existing
        if str(row[key]) not in added_keys
    ]
    rows.extend(dict(row) for row in additions)
    return rows


def _case_for_asset(
    case: Mapping[str, Any],
    asset_id: str,
) -> Dict[str, Any]:
    copied = dict(case)
    metadata = dict(copied.get("metadata") or {})
    metadata["dataset_version"] = asset_id
    copied["metadata"] = metadata
    return copied


def _cluster_lineage(
    previous: Sequence[IntentCluster],
    current: Sequence[IntentCluster],
) -> List[Dict[str, Any]]:
    """Describe cluster continuity using deterministic member overlap."""
    previous_members = {
        cluster.cluster_id: set(cluster.record_ids) for cluster in previous
    }
    provisional: List[Dict[str, Any]] = []
    matched_previous: Counter[str] = Counter()
    for cluster in current:
        current_members = set(cluster.record_ids)
        overlaps = []
        for previous_id, members in previous_members.items():
            intersection = len(current_members & members)
            if not intersection:
                continue
            union = len(current_members | members)
            overlaps.append(
                (
                    intersection / union if union else 0.0,
                    previous_id,
                )
            )
        overlaps.sort(key=lambda item: (-item[0], item[1]))
        if not overlaps:
            provisional.append(
                {
                    "previous_cluster_id": None,
                    "new_cluster_id": cluster.cluster_id,
                    "member_overlap": 0.0,
                    "relationship": "new",
                }
            )
            continue
        best_score, best_id = overlaps[0]
        matched_previous[best_id] += 1
        provisional.append(
            {
                "previous_cluster_id": best_id,
                "new_cluster_id": cluster.cluster_id,
                "member_overlap": round(best_score, 4),
                "relationship": "merged" if len(overlaps) > 1 else "continued",
            }
        )
    for row in provisional:
        previous_id = row["previous_cluster_id"]
        if previous_id and matched_previous[previous_id] > 1:
            row["relationship"] = "split"
    represented = {
        str(row["previous_cluster_id"])
        for row in provisional
        if row["previous_cluster_id"]
    }
    provisional.extend(
        {
            "previous_cluster_id": cluster.cluster_id,
            "new_cluster_id": None,
            "member_overlap": 0.0,
            "relationship": "retired",
        }
        for cluster in previous
        if cluster.cluster_id not in represented
    )
    return provisional


def _normalize_feedback(row: Mapping[str, Any]) -> Dict[str, Any]:
    prepared = dict(_redact_value(row))
    record_id = _string(prepared["record_id"])
    task_type = _string(row["task_type"])
    prepared["request_id"] = _string(prepared.get("request_id")) or record_id
    prepared["route"] = _string(prepared.get("route")) or task_type
    return prepared


def _normalize_intent(row: Mapping[str, Any]) -> Dict[str, Any]:
    prepared = dict(_redact_value(row))
    record_id = _string(prepared["record_id"])
    user_input = _string(prepared["user_input"])
    context = prepared["conversation_context"]
    tool_calls = prepared["tool_calls"]
    task_type = _string(prepared["task_type"])
    canonical = " ".join(
        part
        for part in (
            user_input,
            _latest_context_text(context),
            "tools " + " ".join(_tool_names(tool_calls)),
        )
        if part and part != "tools "
    )
    prepared["request_id"] = _string(prepared.get("request_id")) or record_id
    prepared["route"] = _string(prepared.get("route")) or task_type
    prepared["canonical_intent_text"] = canonical
    prepared["tool_names"] = _tool_names(tool_calls)
    return prepared


def _normalize_rubric(
    raw: Mapping[str, Any],
    identity_key: str,
    identity: str,
    label_source: str,
    rubric_model: str,
    review_status: Optional[str] = "review_required",
) -> Dict[str, Any]:
    rubric = {
        identity_key: identity,
        "intent_label": _string(raw.get("intent_label")) or "unclassified",
        "confidence": max(0.0, min(1.0, float(raw.get("confidence") or 0.5))),
        "must": _string_list(raw.get("must")),
        "must_not": _string_list(raw.get("must_not")),
        "should": _string_list(raw.get("should")),
        "deterministic_checks": list(raw.get("deterministic_checks") or []),
        "tool_expectations": _normalize_tool_expectations(
            raw.get("tool_expectations")
        ),
        "reference_output": (
            _string(raw.get("reference_output"))
            if raw.get("reference_output") is not None
            else None
        ),
        "label_source": label_source,
        "rubric_provider": "openai",
        "rubric_model": rubric_model,
        "oracle_version": "fapo-evaluation-asset-v1",
    }
    if review_status is not None:
        rubric["review_status"] = review_status
    return rubric


def _expected(rubric: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "label_source": rubric["label_source"],
        "confidence": rubric["confidence"],
        "rubric": {
            "must": list(rubric["must"]),
            "must_not": list(rubric["must_not"]),
            "should": list(rubric["should"]),
        },
        "deterministic_checks": list(rubric["deterministic_checks"]),
        "tool_expectations": dict(rubric["tool_expectations"]),
        "reference_output": rubric["reference_output"],
    }


def _trusted_case(
    row: Mapping[str, Any],
    rubric: Mapping[str, Any],
    asset_id: str,
) -> Dict[str, Any]:
    case = {
        "case_id": f"feedback-{row['record_id']}",
        "task_type": row["task_type"],
        "context": _context(
            row["user_input"],
            row["conversation_context"],
            row["tool_calls"],
            row["runtime"],
        ),
        "expected": {
            **_expected(rubric),
            "feedback_polarity": row["feedback"]["polarity"],
        },
        "metadata": {
            "source": "feedback_trace",
            "dataset_version": asset_id,
            "group_id": row["group_id"],
            "request_id": row["request_id"],
            "trust_tier": "trusted_feedback",
        },
    }
    validate_fapo_case(case)
    return case


def _synthetic_case(
    cluster: IntentCluster,
    generated: Mapping[str, Any],
    rubric: Mapping[str, Any],
    asset_id: str,
    candidate_index: int,
) -> Dict[str, Any]:
    user_input = _redact_text(_string(generated.get("user_input")))
    if not user_input:
        raise ValueError(f"Synthetic response has empty user_input for {cluster.cluster_id}")
    digest = hashlib.sha256(
        f"{cluster.cluster_id}:{candidate_index}".encode("utf-8")
    ).hexdigest()[:10]
    expected = _expected(rubric)
    expected["label_source"] = "synthetic_from_trusted_rubric"
    case = {
        "case_id": f"synthetic-{digest}",
        "task_type": _string(generated.get("task_type")) or cluster.route,
        "context": _context(
            user_input,
            list(generated.get("conversation_context") or []),
            [],
            {},
        ),
        "expected": expected,
        "metadata": {
            "source": "synthetic_generation",
            "source_cluster": cluster.cluster_id,
            "dataset_version": asset_id,
            "group_id": f"synthetic-{digest}",
            "request_id": f"synthetic-{digest}",
            "trust_tier": "synthetic_from_trusted_rubric",
            "review_status": "review_required",
        },
    }
    validate_fapo_case(case)
    return case


def _inferred_cases(
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
    intent_rows: Sequence[Mapping[str, Any]],
    raw_rows: Sequence[Mapping[str, Any]],
    rubrics: Sequence[Mapping[str, Any]],
    config: EvaluationAssetConfig,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    match_by_cluster = {match.cluster_id: match for match in matches}
    rubric_by_cluster = {row["cluster_id"]: row for row in rubrics}
    intent_by_id = {row["record_id"]: row for row in intent_rows}
    raw_by_id = {_string(row["record_id"]): row for row in raw_rows}
    labels: List[Dict[str, Any]] = []
    cases: List[Dict[str, Any]] = []
    for cluster in clusters:
        match = match_by_cluster[cluster.cluster_id]
        if match.status != "matched_trusted_intent":
            continue
        rubric = rubric_by_cluster[cluster.cluster_id]
        for record_id in cluster.record_ids:
            intent = intent_by_id[record_id]
            raw = raw_by_id[record_id]
            expected = _expected(rubric)
            expected["confidence"] = round(
                min(float(rubric["confidence"]), float(match.score)),
                4,
            )
            labels.append(
                {
                    "record_id": record_id,
                    "cluster_id": cluster.cluster_id,
                    "matched_intent_id": match.matched_intent_id,
                    "match_score": match.score,
                    "review_status": "review_required",
                    "expected": expected,
                }
            )
            case = {
                "case_id": f"inferred-{record_id}",
                "task_type": intent["task_type"],
                "context": _context(
                    _string(raw["user_input"]),
                    raw["conversation_context"],
                    raw["tool_calls"],
                    raw["runtime"],
                ),
                "expected": expected,
                "metadata": {
                    "source": "unlabeled_trace",
                    "source_cluster": cluster.cluster_id,
                    "matched_intent_id": match.matched_intent_id,
                    "match_score": match.score,
                    "dataset_version": config.asset_id,
                    "group_id": intent["group_id"],
                    "request_id": intent["request_id"],
                    "trust_tier": "inferred_from_trusted_feedback",
                    "review_status": "review_required",
                },
            }
            validate_fapo_case(case)
            cases.append(case)
    return labels, cases


def _build_labeling_queue(
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
    intent_rows: Sequence[Mapping[str, Any]],
    *,
    sample_ratio: float,
    max_per_cluster: int,
) -> List[Dict[str, Any]]:
    """Select deterministic representative traces for coverage-gap labeling."""
    if not 0.0 < sample_ratio <= 1.0:
        raise ValueError("sample_ratio must be greater than 0 and at most 1")
    if max_per_cluster < 1:
        raise ValueError("max_per_cluster must be at least 1")

    row_by_id = {str(row["record_id"]): row for row in intent_rows}
    match_by_cluster = {match.cluster_id: match for match in matches}
    queue: List[Dict[str, Any]] = []
    for cluster in clusters:
        match = match_by_cluster[cluster.cluster_id]
        if match.status == "matched_trusted_intent":
            continue
        target_count = min(
            max_per_cluster,
            len(cluster.representative_ids),
            max(1, math.ceil(cluster.size * sample_ratio)),
        )
        selected_ids = cluster.representative_ids[:target_count]
        for rank, record_id in enumerate(selected_ids, start=1):
            trace = row_by_id.get(record_id)
            if trace is None:
                raise ValueError(
                    f"Cluster {cluster.cluster_id} references unknown record {record_id}"
                )
            queue.append(
                {
                    "queue_id": f"{cluster.cluster_id}:{record_id}",
                    "annotation_status": "pending",
                    "cluster_id": cluster.cluster_id,
                    "route": cluster.route,
                    "coverage_status": match.status,
                    "coverage_reason": match.reason,
                    "match_score": match.score,
                    "cluster_size": cluster.size,
                    "sample_ratio": sample_ratio,
                    "sample_rank": rank,
                    "samples_from_cluster": len(selected_ids),
                    "trace": dict(trace),
                }
            )
    return queue


def _missing_clusters(
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
    row_by_id: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    match_by_cluster = {match.cluster_id: match for match in matches}
    output = []
    for cluster in clusters:
        match = match_by_cluster[cluster.cluster_id]
        if match.status == "matched_trusted_intent":
            continue
        output.append(
            {
                "cluster_id": cluster.cluster_id,
                "route": cluster.route,
                "size": cluster.size,
                "status": match.status,
                "reason": match.reason,
                "best_candidate_intent_id": match.matched_intent_id,
                "match_score": match.score,
                "representative_examples": [
                    {
                        "record_id": record_id,
                        "user_input": row_by_id[record_id]["user_input"],
                    }
                    for record_id in cluster.representative_ids
                ],
            }
        )
    return output


def _write_missing_report(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "<!--",
        "Copyright 2026 Cisco Systems, Inc. and its affiliates",
        "",
        "SPDX-License-Identifier: Apache-2.0",
        "-->",
        "",
        "# Missing Labeled Feedback",
        "",
        f"Clusters requiring review: {len(rows)}",
        "",
    ]
    for row in sorted(rows, key=lambda item: (-int(item["size"]), str(item["cluster_id"]))):
        lines.extend(
            [
                f"## `{row['cluster_id']}`",
                "",
                f"- Route: `{row['route']}`",
                f"- Size: {row['size']}",
                f"- Status: `{row['status']}`",
                f"- Reason: {row['reason']}",
                "- Representative requests:",
            ]
        )
        for example in row["representative_examples"]:
            lines.append(f"  - `{example['record_id']}`: {example['user_input']}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _intent_record(row: Mapping[str, Any]) -> IntentRecord:
    return IntentRecord(
        record_id=str(row["record_id"]),
        text=str(row["canonical_intent_text"]),
        route=str(row["route"]),
        group_id=str(row["group_id"]),
        metadata={"task_type": row["task_type"]},
    )


def _trusted_intent(row: Mapping[str, Any]) -> TrustedIntent:
    return TrustedIntent(
        intent_id=str(row["intent_id"]),
        label=str(row["label"]),
        texts=[str(item) for item in row["texts"]],
        route=str(row["route"]),
        metadata=dict(row.get("metadata") or {}),
    )


def _intent_cluster(row: Mapping[str, Any]) -> IntentCluster:
    return IntentCluster(
        cluster_id=str(row["cluster_id"]),
        route=str(row["route"]),
        record_ids=[str(item) for item in row["record_ids"]],
        representative_ids=[str(item) for item in row["representative_ids"]],
        top_terms=[str(item) for item in row["top_terms"]],
    )


def _intent_match(row: Mapping[str, Any]) -> IntentMatch:
    return IntentMatch(
        cluster_id=str(row["cluster_id"]),
        status=str(row["status"]),
        score=float(row["score"]),
        matched_intent_id=(
            str(row["matched_intent_id"]) if row.get("matched_intent_id") else None
        ),
        matched_label=(
            str(row["matched_label"]) if row.get("matched_label") else None
        ),
        cluster_size=int(row.get("cluster_size") or 0),
        trusted_example_count=int(row.get("trusted_example_count") or 0),
        trusted_group_count=int(row.get("trusted_group_count") or 0),
        unlabeled_to_trusted_ratio=(
            float(row["unlabeled_to_trusted_ratio"])
            if row.get("unlabeled_to_trusted_ratio") is not None
            else None
        ),
        reason=str(row.get("reason") or ""),
    )


def _context(user_input: Any, prior: Any, tools: Any, runtime: Any) -> Dict[str, str]:
    messages = list(_redact_value(prior) or []) + [
        {"role": "user", "content": _redact_text(_string(user_input))}
    ]
    return {
        "messages_json": json.dumps(messages, sort_keys=True),
        "tool_context_json": json.dumps(_redact_value(tools), sort_keys=True),
        "runtime_json": json.dumps(_redact_value(runtime), sort_keys=True),
    }


def _case_group_id(case: Mapping[str, Any]) -> str:
    metadata = case.get("metadata")
    if isinstance(metadata, Mapping):
        group_id = _string(metadata.get("group_id"))
        if group_id:
            return group_id
    return _string(case.get("case_id"))


def _default_split_payloads(
    trusted: Sequence[Dict[str, Any]],
    inferred: Sequence[Dict[str, Any]],
    synthetic: Sequence[Dict[str, Any]],
    *,
    seed: int,
) -> Dict[str, List[Dict[str, Any]]]:
    trusted_partition = split_cases_by_group(
        trusted,
        group_path="metadata.group_id",
        train_fraction=1.0 - DEFAULT_REGRESSION_FRACTION,
        validation_fraction=0.0,
        test_fraction=DEFAULT_REGRESSION_FRACTION,
        seed=seed,
    )
    trusted_standard = trusted_partition["train"]
    regression_trusted = trusted_partition["test"]
    regression_groups = {
        _case_group_id(case) for case in regression_trusted
    }
    inferred_standard, held_inferred = _hold_regression_group_conflicts(
        inferred,
        regression_groups,
    )
    synthetic_standard, held_synthetic = _hold_regression_group_conflicts(
        synthetic,
        regression_groups,
    )
    standard_splits = split_cases_by_group(
        trusted_standard + inferred_standard + synthetic_standard,
        group_path="metadata.group_id",
        seed=seed,
    )
    payloads = _provenance_split_payloads(
        standard_splits,
        trusted_standard,
        inferred_standard,
        synthetic_standard,
    )
    payloads["regression_trusted"] = regression_trusted
    payloads["triage_hold"] = held_inferred + held_synthetic
    return payloads


def _incremental_split_payloads(
    layout: EvaluationAssetLayout,
    trusted: Sequence[Dict[str, Any]],
    inferred: Sequence[Dict[str, Any]],
    synthetic: Sequence[Dict[str, Any]],
    *,
    seed: int,
) -> Dict[str, List[Dict[str, Any]]]:
    parent_assignments: Dict[str, str] = {}
    for split in ("train", "validation", "test"):
        path = layout.parent_snapshot / f"parent_{split}.jsonl"
        for case in _load_jsonl(path):
            parent_assignments[_case_group_id(case)] = split
    parent_regression = {
        _case_group_id(case)
        for case in _load_jsonl(
            layout.parent_snapshot / "parent_regression_trusted.jsonl"
        )
    }

    regression_trusted: List[Dict[str, Any]] = []
    trusted_standard: List[Dict[str, Any]] = []
    for case in trusted:
        group_id = _case_group_id(case)
        if group_id in parent_regression or (
            group_id not in parent_assignments
            and _stable_fraction(group_id, seed) < DEFAULT_REGRESSION_FRACTION
        ):
            regression_trusted.append(dict(case))
        else:
            trusted_standard.append(dict(case))
    regression_groups = parent_regression | {
        _case_group_id(case) for case in regression_trusted
    }
    inferred_standard, held_inferred = _hold_regression_group_conflicts(
        inferred,
        regression_groups,
    )
    synthetic_standard, held_synthetic = _hold_regression_group_conflicts(
        synthetic,
        regression_groups,
    )

    standard_splits: Dict[str, List[Dict[str, Any]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    for case in trusted_standard + inferred_standard + synthetic_standard:
        group_id = _case_group_id(case)
        split = parent_assignments.get(group_id)
        if split is None:
            value = _stable_fraction(group_id, seed)
            split = (
                "train"
                if value < 0.6
                else "validation"
                if value < 0.8
                else "test"
            )
        standard_splits[split].append(dict(case))
    for rows in standard_splits.values():
        rows.sort(key=lambda row: str(row["case_id"]))

    payloads = _provenance_split_payloads(
        standard_splits,
        trusted_standard,
        inferred_standard,
        synthetic_standard,
    )
    payloads["regression_trusted"] = sorted(
        regression_trusted,
        key=lambda row: str(row["case_id"]),
    )
    payloads["triage_hold"] = sorted(
        held_inferred + held_synthetic,
        key=lambda row: str(row["case_id"]),
    )
    return payloads


def _provenance_split_payloads(
    standard_splits: Mapping[str, Sequence[Dict[str, Any]]],
    trusted: Sequence[Dict[str, Any]],
    inferred: Sequence[Dict[str, Any]],
    synthetic: Sequence[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    trusted_ids = {str(case["case_id"]) for case in trusted}
    inferred_ids = {str(case["case_id"]) for case in inferred}
    synthetic_ids = {str(case["case_id"]) for case in synthetic}
    payloads: Dict[str, List[Dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        rows = [dict(row) for row in standard_splits[split]]
        payloads[f"{split}_trusted"] = [
            row for row in rows if str(row["case_id"]) in trusted_ids
        ]
        payloads[f"{split}_inferred"] = [
            row for row in rows if str(row["case_id"]) in inferred_ids
        ]
        payloads[f"{split}_synthetic"] = [
            row for row in rows if str(row["case_id"]) in synthetic_ids
        ]
        payloads[split] = rows
    return payloads


def _stable_fraction(group_id: str, seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{group_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def _hold_regression_group_conflicts(
    cases: Sequence[Mapping[str, Any]],
    regression_group_ids: set[str],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    standard: List[Dict[str, Any]] = []
    held: List[Dict[str, Any]] = []
    for case in cases:
        copied = dict(case)
        if _case_group_id(copied) not in regression_group_ids:
            standard.append(copied)
            continue
        metadata = dict(copied.get("metadata") or {})
        metadata["hold_reason"] = "group_id_reserved_for_regression"
        copied["metadata"] = metadata
        held.append(copied)
    return standard, held


def _indexed_items(
    raw: Mapping[str, Any],
    array_key: str,
    identity_key: str,
) -> Dict[str, Dict[str, Any]]:
    items = raw.get(array_key)
    if not isinstance(items, list):
        raise ValueError(f"Rubric response missing {array_key} array")
    return {
        str(item[identity_key]): dict(item)
        for item in items
        if isinstance(item, Mapping) and item.get(identity_key)
    }


def _grouped_items(
    raw: Mapping[str, Any],
    array_key: str,
    identity_key: str,
) -> Dict[str, List[Dict[str, Any]]]:
    items = raw.get(array_key)
    if not isinstance(items, list):
        raise ValueError(f"Rubric response missing {array_key} array")
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, Mapping) or not item.get(identity_key):
            continue
        grouped.setdefault(str(item[identity_key]), []).append(dict(item))
    return grouped


def _string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        values: Iterable[Any] = value.values()
    elif isinstance(value, Iterable):
        values = value
    else:
        values = (value,)
    return [str(item).strip() for item in values if str(item).strip()]


def _normalize_tool_expectations(value: Any) -> Dict[str, Any]:
    """Preserve model expectations in the object shape required by FAPO cases."""
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        requirements: List[Any] = _string_list(value)
    elif isinstance(value, Iterable):
        requirements = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, Mapping):
                requirements.append(dict(item))
                continue
            text = str(item).strip()
            if text:
                requirements.append(text)
    else:
        raise ValueError(
            "rubric tool_expectations must be a JSON object, array, string, or null"
        )
    return {"requirements": requirements}


def _redact_text(text: str) -> str:
    return IPV4_RE.sub("<ip_address>", EMAIL_RE.sub("<email>", text))


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _redact_value(item) for key, item in value.items()}
    return value


def _latest_context_text(context: Any) -> str:
    if not isinstance(context, list):
        return ""
    for item in reversed(context):
        if isinstance(item, Mapping) and item.get("content"):
            return _redact_text(_string(item["content"]))
    return ""


def _tool_names(calls: Any) -> List[str]:
    if not isinstance(calls, list):
        return []
    names = []
    for call in calls:
        if isinstance(call, str):
            names.append(call)
        elif isinstance(call, Mapping):
            name = call.get("name") or call.get("tool")
            if name:
                names.append(str(name))
    return sorted(set(names))


def _batches(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    if size < 1:
        raise ValueError("batch_size must be at least 1")
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _stage_message(stage: PipelineStage, counts: Mapping[str, int]) -> str:
    summary = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    return f"{stage.value} completed" + (f": {summary}" if summary else "")
