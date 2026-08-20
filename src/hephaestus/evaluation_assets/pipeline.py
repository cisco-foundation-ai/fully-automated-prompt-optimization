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
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
)

from src.hephaestus.artifact_io import atomic_copy_file, atomic_write_text
from src.hephaestus.datasets.embedding_providers import (
    OpenAIEmbeddingProvider,
    validate_embedding_vectors,
)
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
    assert_unique_cluster_ids,
    build_intent_match_texts,
    cluster_records_fixed_count,
    cluster_to_dict,
    dense_vectors_to_sparse,
    match_clusters_to_trusted_intents,
    match_to_dict,
)
from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.evaluation_assets.durability import (
    STAGE_SPECIFICATIONS,
    EvaluationAssetImmutableError,
    EvaluationAssetLegacyError,
    build_stage_receipt,
    file_sha256,
    mutable_rebuild_boundary,
    verify_raw_snapshot_floor,
    verify_release_candidate,
    verify_released_asset,
)
from src.hephaestus.evaluation_assets.input_contract import (
    effective_route,
    validate_input_records,
)
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    compile_evaluation_guidelines as _compile_evaluation_guidelines,  # noqa: F401
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    expected_from_rubric as _expected,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    guidelines_by_source_record as _guidelines_by_source_record,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    normalize_guideline_criteria as _normalize_guideline_criteria,  # noqa: F401
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    normalize_guideline_response as _normalize_guideline_response,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    rubric_from_guidelines as _rubric_from_guidelines,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    trusted_case as _trusted_case,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    trusted_intent_from_guideline as _trusted_intent_from_guideline,
)
from src.hephaestus.evaluation_assets.workspace import (
    EvaluationAssetLayout,
    atomic_write_json,
    utc_now,
)

LABELING_QUEUE_SAMPLE_RATIO = 0.1
LABELING_QUEUE_MAX_PER_CLUSTER = 3
PUBLISHED_DATASET_SPLITS = (
    "train",
    "validation",
    "test",
    "regression_trusted",
)

EVIDENCE_EXTRACTION_PROMPT = """\
Extract atomic evaluation evidence from explicit user feedback. Return one JSON
object with an `evidence` array preserving every `record_id`. The feedback is
trusted evidence; the previous assistant output and tool calls are context, not
an answer key. Each item must contain record_id, intent_label, confidence (0..1),
observations, requested_corrections, and uncertainties. Each observation must
contain claim, evidence_type, evidence_pointer, and polarity. Record only claims
directly supported by the supplied feedback or correction. Do not generalize a
case-specific preference into a universal rule. Never invent environment facts,
private identifiers, tool results, or unsupported correctness requirements.
"""

GUIDELINE_SYNTHESIS_PROMPT = """\
Create reusable evaluation guidelines from trusted feedback evidence grouped by
route. Return one JSON object with a `guidelines` array. Every supplied record_id
must appear in at least one guideline's source_record_ids. Aggregate compatible
evidence and keep conflicting or case-specific evidence explicit rather than
silently resolving it. Each guideline must contain intent_label, description,
route, source_record_ids, confidence (0..1), criteria, tool_expectations, and
reference_output, conflicts, and uncertainties. Each criterion must contain
kind (required, prohibited, or preferred), statement, source_record_ids,
dimension, severity (critical, major, or minor), applicability, scoring,
evidence_required, and evaluator. Criterion source_record_ids must be a subset
of the guideline source_record_ids. Evaluator must contain type and fallback;
prefer state_check or deterministic_check when the evidence is
objectively verifiable, semantic_trajectory only when the path itself matters,
llm_judge for qualitative criteria, and human_review when evidence is
insufficient. Avoid literal tool names unless the feedback makes that exact tool
contract mandatory. Permit multiple valid solution paths. reference_output must
be a string or null and must never be copied from a previous assistant response.
"""

INFERENCE_PROMPT = """\
Infer reviewable case rubrics for unlabeled intent clusters using only the
supplied trusted evaluation guideline as correctness evidence. Return one JSON object with a
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

STAGE_PROMPTS = {
    PipelineStage.RUBRIC_EXTRACTION: {
        "evidence_extraction": EVIDENCE_EXTRACTION_PROMPT,
        "guideline_synthesis": GUIDELINE_SYNTHESIS_PROMPT,
    },
    PipelineStage.LABEL_INFERENCE: {"label_inference": INFERENCE_PROMPT},
    PipelineStage.SYNTHETIC_COVERAGE: {"synthetic_coverage": SYNTHETIC_PROMPT},
}

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DEFAULT_REGRESSION_FRACTION = 0.2
RubricResponseT = TypeVar("RubricResponseT")


class RubricProvider(Protocol):
    """JSON generation interface used by the pipeline."""

    provider_name: str
    model: str

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Return one JSON object."""


class EmbeddingProvider(Protocol):
    """Embedding interface used by clustering and coverage."""

    provider_name: str
    model: str

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one vector per input."""


class ProviderCallError(RuntimeError):
    """Safe provider failure whose original exception remains its cause."""

    def __init__(
        self,
        *,
        stage: PipelineStage,
        provider: str,
        model: str,
        cause: Exception,
    ) -> None:
        cause_name = _provider_cause_label(cause)
        summary = _provider_cause_summary(cause)
        super().__init__(
            "Provider call failed: "
            f"stage={stage.value}, provider={provider}, model={model}, "
            f"cause={cause_name}, summary={summary}"
        )


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
        self._injected_rubric_provider = rubric_provider
        self._injected_embedding_provider = embedding_provider
        self.rubric_provider = rubric_provider
        self.embedding_provider = embedding_provider
        self._provider_identities: dict[str, dict[str, Any]] = {}
        self.last_revision: Optional[Dict[str, Any]] = None

    def _configure_providers(self) -> None:
        """Resolve providers from the recovered, revised configuration under lock."""
        if self._injected_rubric_provider is not None:
            self.rubric_provider = self._injected_rubric_provider
            rubric_source = "injected"
        elif self.config.rubric_provider == "openai":
            self.rubric_provider = OpenAIRubricProvider(
                model=self.config.rubric_model,
                # Reasoning models consume reasoning tokens before emitting JSON.
                max_output_tokens=16384,
            )
            rubric_source = "default"
        else:
            raise ValueError(
                f"Unsupported rubric provider: {self.config.rubric_provider}"
            )

        if self._injected_embedding_provider is not None:
            self.embedding_provider = self._injected_embedding_provider
            embedding_source = "injected"
        elif self.config.embedding_provider == "openai":
            self.embedding_provider = OpenAIEmbeddingProvider(
                model=self.config.embedding_model
            )
            embedding_source = "default"
        elif self.config.embedding_provider == "tfidf":
            self.embedding_provider = None
            embedding_source = "default"
        else:
            raise ValueError(
                f"Unsupported embedding provider: {self.config.embedding_provider}"
            )

        self._provider_identities = {
            "rubric": self._actual_provider_identity(
                self.rubric_provider,
                configured_provider=self.config.rubric_provider,
                configured_model=self.config.rubric_model,
                source=rubric_source,
            ),
            "embedding": self._actual_provider_identity(
                self.embedding_provider,
                configured_provider=self.config.embedding_provider,
                configured_model=self.config.embedding_model,
                source=embedding_source,
            ),
        }

    @staticmethod
    def _actual_provider_identity(
        provider: Any,
        *,
        configured_provider: str,
        configured_model: str,
        source: str,
    ) -> dict[str, Any]:
        if source == "default":
            provider_name = configured_provider.strip()
            model = configured_model.strip()
            if not provider_name or not model:
                raise ValueError(
                    "Default provider identity requires non-empty provider and model"
                )
            return {"provider": provider_name, "model": model, "source": source}

        declared = {
            "provider_name": getattr(provider, "provider_name", None),
            "model": getattr(provider, "model", None),
        }
        unavailable_fields = [
            field
            for field, value in declared.items()
            if not isinstance(value, str) or not value.strip()
        ]
        if unavailable_fields:
            return {
                "provider": (
                    str(declared["provider_name"]).strip()
                    if "provider_name" not in unavailable_fields
                    else "unavailable"
                ),
                "model": (
                    str(declared["model"]).strip()
                    if "model" not in unavailable_fields
                    else "unavailable"
                ),
                "source": source,
                "status": "unavailable",
                "unavailable_fields": unavailable_fields,
            }
        return {
            "provider": str(declared["provider_name"]).strip(),
            "model": str(declared["model"]).strip(),
            "source": source,
        }

    def _validate_injected_provider_identities(self) -> None:
        """Reject incomplete injected identities before any authority mutation."""
        injected = {
            "rubric": (
                self._injected_rubric_provider,
                self.config.rubric_provider,
                self.config.rubric_model,
            ),
            "embedding": (
                self._injected_embedding_provider,
                self.config.embedding_provider,
                self.config.embedding_model,
            ),
        }
        for role, (provider, configured_provider, configured_model) in injected.items():
            if provider is None:
                continue
            identity = self._actual_provider_identity(
                provider,
                configured_provider=configured_provider,
                configured_model=configured_model,
                source="injected",
            )
            if identity.get("status") == "unavailable":
                missing = ", ".join(identity["unavailable_fields"])
                raise ValueError(
                    f"injected {role} provider identity is unavailable; "
                    f"declare non-empty {missing}"
                )

    def _provider_identity_for_stage(
        self,
        stage: PipelineStage,
    ) -> dict[str, Any]:
        roles = STAGE_SPECIFICATIONS[stage].provider_roles
        return (
            {role: dict(self._provider_identities[role]) for role in roles}
            if roles
            else {"status": "not_applicable"}
        )

    def _call_rubric_provider(
        self,
        stage: PipelineStage,
        system_prompt: str,
        payload: Mapping[str, Any],
        normalize: Callable[[Mapping[str, Any]], RubricResponseT],
    ) -> RubricResponseT:
        if self.rubric_provider is None:
            raise RuntimeError("Rubric provider is not configured")
        try:
            response = self.rubric_provider.generate_json(system_prompt, payload)
            if not isinstance(response, Mapping):
                raise ValueError("Rubric provider response must be a JSON object")
            return normalize(response)
        except Exception as exc:
            raise ProviderCallError(
                stage=stage,
                provider=self._provider_identities["rubric"]["provider"],
                model=self._provider_identities["rubric"]["model"],
                cause=exc,
            ) from exc

    def _call_embedding_provider(
        self,
        stage: PipelineStage,
        texts: Sequence[str],
    ) -> Sequence[Sequence[float]]:
        if self.embedding_provider is None:
            return []
        try:
            return self.embedding_provider.embed_texts(texts)
        except Exception as exc:
            raise ProviderCallError(
                stage=stage,
                provider=self._provider_identities["embedding"]["provider"],
                model=self._provider_identities["embedding"]["model"],
                cause=exc,
            ) from exc

    @classmethod
    def create(
        cls,
        tenants_root: Path,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        rubric_provider: Optional[RubricProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        initial_status: str = "draft",
    ) -> "EvaluationAssetPipeline":
        """Create a self-contained workspace by copying both source files."""
        layout = EvaluationAssetLayout(
            tenants_root=tenants_root,
            tenant_id=config.tenant_id,
            asset_id=config.asset_id,
        )
        layout.initialize(
            config,
            feedback_source,
            unlabeled_source,
            initial_status=initial_status,
        )
        return cls(layout, rubric_provider=rubric_provider, embedding_provider=embedding_provider)

    def run(
        self,
        *,
        config_updates: Optional[Mapping[str, Any]] = None,
        lock_timeout: float = 0,
        _lock_acquired_callback: Optional[Callable[[], None]] = None,
        _preflight_accepted_callback: Optional[Callable[[], None]] = None,
    ) -> PipelineState:
        """Run or resume all incomplete stages."""
        with self.layout.asset_lock(lock_timeout):
            if _lock_acquired_callback is not None:
                _lock_acquired_callback()
            self.layout._recover_locked()
            state = self.layout.load_state()
            if state.status == "released":
                verify_released_asset(self.layout, state)
                raise EvaluationAssetImmutableError(
                    self.layout.tenant_id,
                    self.layout.asset_id,
                )
            if state.legacy_completed:
                raise EvaluationAssetLegacyError(
                    self.layout.tenant_id,
                    self.layout.asset_id,
                    "explicit verification and adoption are required",
                )
            verify_raw_snapshot_floor(self.layout, state)
            self._validate_injected_provider_identities()
            self.last_revision = (
                self.layout._revise_config_locked(config_updates)
                if config_updates is not None
                else None
            )
            self.config = self.layout.load_config()
            self.lineage = (
                json.loads(self.layout.lineage_path.read_text(encoding="utf-8"))
                if self.layout.lineage_path.is_file()
                else {}
            )
            self._configure_providers()
            return self._run_locked(_preflight_accepted_callback)

    def _run_locked(
        self,
        preflight_accepted_callback: Optional[Callable[[], None]] = None,
    ) -> PipelineState:
        """Run while the caller holds the asset mutation lock."""
        state = self.layout.load_state()
        state.schema_version = "fapo-evaluation-asset-state-v2"
        boundary = mutable_rebuild_boundary(
            self.layout,
            state,
            self.config,
            STAGE_PROMPTS,
            {
                stage: self._provider_identity_for_stage(stage)
                for stage in PipelineStage
            },
        )
        if boundary is not None:
            boundary_index = list(PipelineStage).index(boundary)
            suffix_states = state.stages[boundary_index:]
            if any(
                item.status != "pending" or item.receipt_sha256
                for item in suffix_states
            ):
                state = self.layout._invalidate_checkpoints_locked(state, boundary)
        state.status = "running"
        state.error = None
        self.layout.save_state(state)
        self.layout.append_event("pipeline_started")
        if preflight_accepted_callback is not None:
            preflight_accepted_callback()

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
            completed_at = utc_now()
            receipt = build_stage_receipt(
                self.layout,
                stage,
                self.config,
                counts,
                completed_at=completed_at,
                prompt_values=STAGE_PROMPTS.get(stage, {}),
                provider_identity=self._provider_identity_for_stage(stage),
            )
            atomic_write_json(self.layout.receipt_path(stage), receipt)
            stage_state.receipt_sha256 = file_sha256(
                self.layout.receipt_path(stage)
            )
            stage_state.status = "completed"
            stage_state.completed_at = completed_at
            stage_state.message = _stage_message(stage, counts)
            self.layout.save_state(state)
            self.layout.append_event(
                "stage_completed",
                {"stage": stage.value, "counts": counts},
            )

        candidate = PipelineState.from_dict(state.to_dict())
        candidate.status = "released"
        candidate.current_stage = None
        candidate.error = None
        candidate.updated_at = utc_now()
        verify_release_candidate(self.layout, candidate)
        atomic_write_json(self.layout.state_path, candidate.to_dict())
        verify_released_asset(self.layout, candidate)
        self.layout.append_event(
            "pipeline_released",
            {"counts": candidate.counts},
        )
        return candidate

    def _run_stage(self, stage: PipelineStage) -> Dict[str, int]:
        handlers = {
            PipelineStage.RAW_INPUTS: self._validate_raw_inputs,
            PipelineStage.PREPARED_INPUTS: self._prepare_inputs,
            PipelineStage.RUBRIC_EXTRACTION: self._create_evaluation_guidelines,
            PipelineStage.INTENT_CLUSTERING: self._cluster_intents,
            PipelineStage.COVERAGE_DECISIONS: self._decide_coverage,
            PipelineStage.LABEL_INFERENCE: self._infer_labels,
            PipelineStage.SYNTHETIC_COVERAGE: self._generate_synthetic_coverage,
            PipelineStage.DATASET_SPLITS: self._build_splits,
        }
        return handlers[stage]()

    def _validate_raw_inputs(self) -> Dict[str, int]:
        feedback, feedback_row_numbers = _load_jsonl_with_line_numbers(
            self.layout.feedback_path
        )
        unlabeled, unlabeled_row_numbers = _load_jsonl_with_line_numbers(
            self.layout.unlabeled_path
        )
        if not feedback:
            raise ValueError("labeled feedback input is empty")
        if not unlabeled:
            raise ValueError("unlabeled input is empty")
        validate_input_records(
            feedback,
            labeled=True,
            path=self.layout.feedback_path,
            row_numbers=feedback_row_numbers,
        )
        validate_input_records(
            unlabeled,
            labeled=False,
            path=self.layout.unlabeled_path,
            row_numbers=unlabeled_row_numbers,
        )
        _validate_stage_one_feasibility(unlabeled, self.config.cluster_count)
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
        feedback_rows, feedback_row_numbers = _load_jsonl_with_line_numbers(
            self.layout.feedback_path
        )
        unlabeled_rows, unlabeled_row_numbers = _load_jsonl_with_line_numbers(
            self.layout.unlabeled_path
        )
        normalized = [_normalize_feedback(row) for row in feedback_rows]
        intents = [_normalize_intent(row) for row in unlabeled_rows]
        _validate_normalized_identity(
            normalized,
            feedback_rows,
            output_name="normalized feedback",
            row_numbers=feedback_row_numbers,
        )
        _validate_normalized_identity(
            intents,
            unlabeled_rows,
            output_name="normalized unlabeled intent",
            row_numbers=unlabeled_row_numbers,
        )
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

    def _create_evaluation_guidelines(self) -> Dict[str, int]:
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
        evidence_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_evidence.jsonl",
        )
        candidate_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "candidate_guidelines.jsonl",
        )
        guideline_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
        intent_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_intents.jsonl",
        )
        case_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_cases.jsonl",
        )
        incremental = bool(self.lineage) and evidence_path.is_file()
        existing_evidence = _load_jsonl(evidence_path) if incremental else []
        pending = (
            [
                row
                for row in normalized
                if str(row["record_id"]) in added_record_ids
            ]
            if incremental
            else normalized
        )
        new_evidence: List[Dict[str, Any]] = []
        for batch in _batches(pending, self.config.batch_size):
            new_evidence.extend(
                self._call_rubric_provider(
                    PipelineStage.RUBRIC_EXTRACTION,
                    EVIDENCE_EXTRACTION_PROMPT,
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
                    partial(
                        _normalize_feedback_evidence_response,
                        batch=batch,
                        rubric_provider=self._provider_identities["rubric"][
                            "provider"
                        ],
                        rubric_model=self._provider_identities["rubric"]["model"],
                    ),
                )
            )

        evidence = _replace_by_key(
            existing_evidence,
            new_evidence,
            key="record_id",
        )
        evidence_by_route: Dict[str, List[Dict[str, Any]]] = {}
        normalized_by_id = {str(row["record_id"]): row for row in normalized}
        for item in evidence:
            evidence_by_route.setdefault(str(item["route"]), []).append(item)

        candidates: List[Dict[str, Any]] = []
        guidelines: List[Dict[str, Any]] = []
        for route in sorted(evidence_by_route):
            route_evidence = sorted(
                evidence_by_route[route], key=lambda item: str(item["record_id"])
            )
            source_records = [
                normalized_by_id[str(item["record_id"])] for item in route_evidence
            ]
            route_candidates, route_guidelines = self._call_rubric_provider(
                PipelineStage.RUBRIC_EXTRACTION,
                GUIDELINE_SYNTHESIS_PROMPT,
                {
                    "route": route,
                    "evidence": route_evidence,
                    "examples": [
                        {
                            "record_id": row["record_id"],
                            "task_type": row["task_type"],
                            "user_input": row["user_input"],
                            "feedback_polarity": row["feedback"]["polarity"],
                        }
                        for row in source_records
                    ],
                },
                partial(
                    _normalize_guideline_response,
                    route=route,
                    evidence=route_evidence,
                    rubric_provider=self._provider_identities["rubric"][
                        "provider"
                    ],
                    rubric_model=self._provider_identities["rubric"]["model"],
                ),
            )
            candidates.extend(route_candidates)
            guidelines.extend(route_guidelines)
        guidelines.sort(key=lambda item: str(item["guideline_id"]))
        guideline_by_record = _guidelines_by_source_record(guidelines)
        trusted_intents = [
            _trusted_intent_from_guideline(guideline, normalized_by_id)
            for guideline in guidelines
        ]
        trusted_cases = [
            _trusted_case(
                row,
                _rubric_from_guidelines(
                    str(row["record_id"]),
                    guideline_by_record[str(row["record_id"])],
                    self._provider_identities["rubric"]["provider"],
                    self._provider_identities["rubric"]["model"],
                ),
                self.config.asset_id,
            )
            for row in normalized
        ]
        write_jsonl(evidence_path, evidence)
        write_jsonl(candidate_path, candidates)
        write_jsonl(guideline_path, guidelines)
        write_jsonl(
            intent_path,
            trusted_intents,
        )
        write_jsonl(
            case_path,
            trusted_cases,
        )
        return {
            "feedback_evidence": len(evidence),
            "candidate_guidelines": len(candidates),
            "evaluation_guidelines": len(guidelines),
            "trusted_cases": len(trusted_cases),
        }

    def _cluster_intents(self) -> Dict[str, int]:
        inventory_path = self.layout.artifact_path(
            PipelineStage.INTENT_CLUSTERING,
            "intent_inventory.jsonl",
        )
        lineage_path = self.layout.artifact_path(
            PipelineStage.INTENT_CLUSTERING,
            "cluster_lineage.jsonl",
        )
        if self.lineage.get("clustering_mode") == "keep":
            snapshot = self.layout.parent_snapshot / "parent_intent_inventory.jsonl"
            atomic_copy_file(snapshot, inventory_path)
            clusters = [_intent_cluster(row) for row in _load_jsonl(inventory_path)]
            assert_unique_cluster_ids(clusters)
            write_jsonl(
                lineage_path,
                [
                    {
                        "previous_cluster_id": cluster.cluster_id,
                        "new_cluster_id": cluster.cluster_id,
                        "member_overlap": 1.0,
                        "relationship": "reused",
                    }
                    for cluster in clusters
                ],
            )
            return {"intent_clusters": len(clusters)}
        rows = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            )
        )
        records = [_intent_record(row) for row in rows]
        vectors = None
        if self.embedding_provider is not None:
            texts = [record.text for record in records]
            embeddings = validate_embedding_vectors(
                self._call_embedding_provider(
                    PipelineStage.INTENT_CLUSTERING,
                    texts,
                ),
                expected_count=len(texts),
                source="embedding provider result",
            )
            vectors = dense_vectors_to_sparse(
                [record.record_id for record in records],
                embeddings,
            )
        clusters = cluster_records_fixed_count(
            records,
            cluster_count=self.config.cluster_count,
            vectors=vectors,
        )
        write_jsonl(
            inventory_path,
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
        assert_unique_cluster_ids(previous)
        assert_unique_cluster_ids(clusters)
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
            embedding_keys = list(match_texts)
            embeddings = validate_embedding_vectors(
                self._call_embedding_provider(
                    PipelineStage.COVERAGE_DECISIONS,
                    [match_texts[key] for key in embedding_keys]
                ),
                expected_count=len(embedding_keys),
                source="embedding provider result",
            )
            vectors = dense_vectors_to_sparse(
                embedding_keys,
                embeddings,
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
        guideline_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
        if guideline_path.is_file():
            evaluation_guidelines = _load_jsonl(guideline_path)
        else:
            evaluation_guidelines = [
                _legacy_guideline_from_rubric(row)
                for row in _load_jsonl(
                    self.layout.artifact_path(
                        PipelineStage.RUBRIC_EXTRACTION,
                        "feedback_rubrics.jsonl",
                    )
                )
            ]
        clusters = [
            _intent_cluster(row)
            for row in _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.INTENT_CLUSTERING,
                    "intent_inventory.jsonl",
                )
            )
        ]
        assert_unique_cluster_ids(clusters)
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
        guideline_by_id = {
            row["guideline_id"]: row for row in evaluation_guidelines
        }
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
            cluster_rubrics.extend(
                self._call_rubric_provider(
                    PipelineStage.LABEL_INFERENCE,
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
                                "trusted_requests": [
                                    normalized_by_id[record_id]["user_input"]
                                    for record_id in guideline_by_id[
                                        str(
                                            match_by_cluster[
                                                cluster.cluster_id
                                            ].matched_intent_id
                                        )
                                    ]["source_record_ids"]
                                ],
                                "trusted_evaluation_guideline": guideline_by_id[
                                    str(
                                        match_by_cluster[
                                            cluster.cluster_id
                                        ].matched_intent_id
                                    )
                                ],
                                "match_score": match_by_cluster[
                                    cluster.cluster_id
                                ].score,
                            }
                            for cluster in batch
                        ]
                    },
                    partial(
                        _normalize_inferred_rubric_response,
                        batch=batch,
                        rubric_provider=self._provider_identities["rubric"][
                            "provider"
                        ],
                        rubric_model=self._provider_identities["rubric"]["model"],
                    ),
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
        published_datasets = self.layout.publish_dataset_splits(
            PUBLISHED_DATASET_SPLITS
        )

        input_manifest = json.loads(
            self.layout.artifact_path(
                PipelineStage.RAW_INPUTS,
                "input_manifest.json",
            ).read_text(encoding="utf-8")
        )
        guideline_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
        guideline_count = (
            len(_load_jsonl(guideline_path)) if guideline_path.is_file() else 0
        )
        manifest = {
            "asset_id": self.config.asset_id,
            "tenant_id": self.config.tenant_id,
            "providers": {
                "rubric_provider": self._provider_identities["rubric"]["provider"],
                "rubric_model": self._provider_identities["rubric"]["model"],
                "embedding_provider": self._provider_identities["embedding"][
                    "provider"
                ],
                "embedding_model": self._provider_identities["embedding"]["model"],
            },
            "evaluation_guidelines": {
                "schema_version": (
                    "fapo-evaluation-guideline-v1"
                    if guideline_path.is_file()
                    else "legacy-feedback-rubric-v1"
                ),
                "count": guideline_count,
                "activation_status": (
                    "active_from_trusted_evidence"
                    if guideline_path.is_file()
                    else "legacy_compatibility"
                ),
                "calibration_status": (
                    "uncalibrated" if guideline_path.is_file() else "unavailable"
                ),
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
            "published_datasets": {
                "directory": self.layout.published_datasets.relative_to(
                    self.layout.tenant_root
                ).as_posix(),
                "files": published_datasets,
            },
            "split_counts": {name: len(rows) for name, rows in payloads.items()},
            "review_policy": {
                "evaluation_guidelines": "active_from_trusted_evidence",
                "guideline_calibration": "uncalibrated",
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
        assert_unique_cluster_ids(clusters)
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
            candidates.extend(
                self._call_rubric_provider(
                    PipelineStage.SYNTHETIC_COVERAGE,
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
                                "case_count": (
                                    self.config.synthetic_cases_per_cluster
                                ),
                            }
                            for cluster in batch
                        ]
                    },
                    partial(
                        _normalize_synthetic_response,
                        batch=batch,
                        rubric_by_cluster=rubric_by_cluster,
                        config=self.config,
                    ),
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
    rows, _ = _load_jsonl_with_line_numbers(path)
    return rows


def _load_jsonl_with_line_numbers(
    path: Path,
) -> tuple[List[Dict[str, Any]], List[int]]:
    rows: List[Dict[str, Any]] = []
    row_numbers: List[int] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{path}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object at {path}:{line_number}")
        rows.append(row)
        row_numbers.append(line_number)
    return rows, row_numbers


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
    prepared = _redact_record(row)
    if "request_id" not in prepared:
        prepared["request_id"] = prepared["record_id"]
    prepared["route"] = effective_route(prepared)
    return prepared


def _normalize_intent(row: Mapping[str, Any]) -> Dict[str, Any]:
    prepared = _redact_record(row)
    user_input = _string(prepared["user_input"])
    context = prepared["conversation_context"]
    tool_calls = prepared["tool_calls"]
    canonical = " ".join(
        part
        for part in (
            user_input,
            _latest_context_text(context),
            "tools " + " ".join(_tool_names(tool_calls)),
        )
        if part and part != "tools "
    )
    if "request_id" not in prepared:
        prepared["request_id"] = prepared["record_id"]
    prepared["route"] = effective_route(prepared)
    prepared["canonical_intent_text"] = canonical
    prepared["tool_names"] = _tool_names(tool_calls)
    return prepared


def _validate_normalized_identity(
    normalized_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    *,
    output_name: str,
    row_numbers: Optional[Sequence[int]] = None,
) -> None:
    """Reject canonical identity collisions with both source locations."""
    if row_numbers is not None and len(row_numbers) != len(source_rows):
        raise ValueError("row_numbers must identify every source record")
    seen: Dict[str, tuple[int, str]] = {}
    for logical_index, (normalized, source) in enumerate(
        zip(normalized_rows, source_rows)
    ):
        row_number = (
            row_numbers[logical_index]
            if row_numbers is not None
            else logical_index + 1
        )
        record_id = normalized.get("record_id")
        source_id = source.get("record_id", "<missing>")
        if record_id in seen:
            first_row, first_source_id = seen[record_id]
            raise ValueError(
                f"{output_name} duplicate record_id '{record_id}': "
                f"row {first_row} source record_id '{first_source_id}' and "
                f"row {row_number} source record_id '{source_id}'"
            )
        seen[record_id] = (row_number, source_id)


def _validate_stage_one_feasibility(
    unlabeled_rows: Sequence[Mapping[str, Any]],
    cluster_count: int,
) -> None:
    """Reject fixed-count route allocations that the data cannot satisfy."""
    record_count = len(unlabeled_rows)
    if cluster_count > record_count:
        raise ValueError(
            "cluster_count cannot exceed the number of unlabeled records "
            f"({record_count})"
        )
    routes = {effective_route(row) for row in unlabeled_rows}
    if cluster_count < len(routes):
        raise ValueError(
            "cluster_count must be at least the number of distinct effective "
            f"routes ({len(routes)}); one route-local cluster per route is required"
        )


def _normalize_feedback_evidence(
    raw: Mapping[str, Any],
    source: Mapping[str, Any],
    rubric_provider: str,
    rubric_model: str,
) -> Dict[str, Any]:
    observations = []
    for item in list(raw.get("observations") or []):
        if not isinstance(item, Mapping) or not _string(item.get("claim")):
            continue
        observations.append(
            {
                "claim": _string(item["claim"]),
                "evidence_type": _string(item.get("evidence_type"))
                or "explicit_feedback",
                "evidence_pointer": _string(item.get("evidence_pointer"))
                or "feedback.rationale",
                "polarity": _string(item.get("polarity"))
                or _string(source["feedback"].get("polarity")),
            }
        )
    return {
        "record_id": str(source["record_id"]),
        "group_id": str(source["group_id"]),
        "route": str(source["route"]),
        "task_type": str(source["task_type"]),
        "intent_label": _string(raw.get("intent_label")) or "unclassified",
        "confidence": _confidence(raw.get("confidence")),
        "observations": observations,
        "requested_corrections": _string_list(raw.get("requested_corrections")),
        "uncertainties": _string_list(raw.get("uncertainties")),
        "evidence_source": "trusted_feedback",
        "guideline_provider": rubric_provider,
        "guideline_model": rubric_model,
    }


def _normalize_feedback_evidence_response(
    response: Mapping[str, Any],
    *,
    batch: Sequence[Mapping[str, Any]],
    rubric_provider: str,
    rubric_model: str,
) -> List[Dict[str, Any]]:
    returned = _indexed_items(response, "evidence", "record_id")
    evidence: List[Dict[str, Any]] = []
    for row in batch:
        record_id = str(row["record_id"])
        if record_id not in returned:
            raise ValueError(f"Evidence response omitted {record_id}")
        evidence.append(
            _normalize_feedback_evidence(
                returned[record_id],
                row,
                rubric_provider,
                rubric_model,
            )
        )
    return evidence


def _legacy_guideline_from_rubric(rubric: Mapping[str, Any]) -> Dict[str, Any]:
    record_id = str(rubric["record_id"])
    criteria = []
    for kind, field in (
        ("required", "must"),
        ("prohibited", "must_not"),
        ("preferred", "should"),
    ):
        for statement in _string_list(rubric.get(field)):
            digest = hashlib.sha256(
                f"legacy:{record_id}:{kind}:{statement}".encode("utf-8")
            ).hexdigest()[:10]
            criteria.append(
                {
                    "criterion_id": f"criterion-{digest}",
                    "kind": kind,
                    "statement": statement,
                    "dimension": "task_success",
                    "severity": "major",
                    "applicability": "always",
                    "scoring": "binary",
                    "evidence_required": False,
                    "evaluator": {
                        "type": "llm_judge",
                        "fallback": "human_review",
                    },
                }
            )
    return {
        "guideline_id": record_id,
        "route": "",
        "intent_label": rubric.get("intent_label") or "unclassified",
        "description": rubric.get("intent_label") or "Legacy feedback rubric",
        "confidence": rubric.get("confidence", 0.5),
        "source_record_ids": [record_id],
        "criteria": criteria,
        "tool_expectations": _normalize_tool_expectations(
            rubric.get("tool_expectations")
        ),
        "reference_output": rubric.get("reference_output"),
        "calibration_status": "legacy_unavailable",
    }


def _confidence(value: Any) -> float:
    return max(0.0, min(1.0, float(value or 0.5)))


def _normalize_rubric(
    raw: Mapping[str, Any],
    identity_key: str,
    identity: str,
    label_source: str,
    rubric_provider: str,
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
        "rubric_provider": rubric_provider,
        "rubric_model": rubric_model,
        "oracle_version": "fapo-evaluation-asset-v1",
    }
    if review_status is not None:
        rubric["review_status"] = review_status
    return rubric


def _normalize_inferred_rubric_response(
    response: Mapping[str, Any],
    *,
    batch: Sequence[IntentCluster],
    rubric_provider: str,
    rubric_model: str,
) -> List[Dict[str, Any]]:
    returned = _indexed_items(response, "rubrics", "cluster_id")
    rubrics: List[Dict[str, Any]] = []
    for cluster in batch:
        if cluster.cluster_id not in returned:
            raise ValueError(
                f"Inferred rubric response omitted {cluster.cluster_id}"
            )
        rubrics.append(
            _normalize_rubric(
                returned[cluster.cluster_id],
                "cluster_id",
                cluster.cluster_id,
                "inferred_from_trusted_feedback",
                rubric_provider,
                rubric_model,
            )
        )
    return rubrics


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


def _normalize_synthetic_response(
    response: Mapping[str, Any],
    *,
    batch: Sequence[IntentCluster],
    rubric_by_cluster: Mapping[str, Mapping[str, Any]],
    config: EvaluationAssetConfig,
) -> List[Dict[str, Any]]:
    returned = _grouped_items(response, "cases", "cluster_id")
    cases: List[Dict[str, Any]] = []
    for cluster in batch:
        generated_cases = returned.get(cluster.cluster_id, [])
        if len(generated_cases) != config.synthetic_cases_per_cluster:
            raise ValueError(
                "Synthetic response returned "
                f"{len(generated_cases)} cases for {cluster.cluster_id}; "
                f"expected {config.synthetic_cases_per_cluster}"
            )
        for candidate_index, generated in enumerate(generated_cases, start=1):
            cases.append(
                _synthetic_case(
                    cluster,
                    generated,
                    rubric_by_cluster[cluster.cluster_id],
                    config.asset_id,
                    candidate_index,
                )
            )
    return cases


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
    atomic_write_text(path, "\n".join(lines) + "\n")


def _intent_record(row: Mapping[str, Any]) -> IntentRecord:
    return IntentRecord(
        record_id=str(row["record_id"]),
        text=str(row["canonical_intent_text"]),
        route=effective_route(row),
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
    messages = list(_redact_messages(prior) or []) + [
        {"role": "user", "content": _redact_text(_string(user_input))}
    ]
    return {
        "messages_json": json.dumps(messages, sort_keys=True),
        "tool_context_json": json.dumps(_redact_tool_calls(tools), sort_keys=True),
        "runtime_json": json.dumps(_redact_named_content(runtime), sort_keys=True),
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


def _provider_cause_summary(cause: Exception) -> str:
    """Return only an allowlisted provider-failure category."""
    if isinstance(cause, TimeoutError):
        return "provider request timed out"
    if isinstance(cause, PermissionError):
        return "provider access denied"
    if isinstance(cause, ConnectionError):
        return "provider connection failed"
    if isinstance(cause, ValueError):
        return "provider returned an invalid response"
    return "provider operation failed"


def _provider_cause_label(cause: Exception) -> str:
    """Map provider exceptions to fixed labels safe for persistence."""
    if isinstance(cause, TimeoutError):
        return "TimeoutError"
    if isinstance(cause, PermissionError):
        return "PermissionError"
    if isinstance(cause, ConnectionError):
        return "ConnectionError"
    if isinstance(cause, ValueError):
        return "ValueError"
    if isinstance(cause, RuntimeError):
        return "RuntimeError"
    return "ProviderError"


CONTENT_FIELD_NAMES = frozenset(
    {
        "arguments",
        "body",
        "content",
        "correction",
        "data",
        "description",
        "error",
        "input",
        "message",
        "messages",
        "note",
        "output",
        "payload",
        "prompt",
        "query",
        "rationale",
        "request",
        "response",
        "result",
        "results",
        "text",
    }
)
PRESERVED_NAMED_FIELDS = frozenset(
    {
        "application",
        "application_version",
        "call_id",
        "created_at",
        "deployment",
        "deployment_id",
        "environment",
        "group_id",
        "id",
        "intent_id",
        "intent_label",
        "model",
        "model_name",
        "provider",
        "provider_name",
        "record_id",
        "region",
        "request_id",
        "route",
        "schema_version",
        "session_id",
        "source",
        "source_system",
        "source_version",
        "span_id",
        "task_type",
        "timestamp",
        "tool",
        "tool_call_id",
        "tool_name",
        "trace_id",
        "type",
        "updated_at",
        "version",
    }
)
MESSAGE_STRUCTURE_FIELDS = frozenset(
    {"conversation_context", "message", "messages"}
)
STRUCTURAL_DESCRIPTOR_FIELDS = frozenset(
    {
        "application",
        "deployment",
        "environment",
        "model",
        "provider",
        "region",
        "source",
        "source_system",
    }
)
TOOL_STRUCTURE_FIELDS = frozenset(
    {
        "enabled_tools",
        "function",
        "tool",
        "tool_calls",
        "tool_names",
        "tools",
        "tools_available",
    }
)


def _is_composite_value(value: Any) -> bool:
    return isinstance(value, (Mapping, list))


def _redact_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Redact canonical content without rewriting identity or structure."""
    prepared = dict(row)
    for field in ("user_input", "assistant_output"):
        if field in prepared:
            prepared[field] = _redact_value(prepared[field])
    if "conversation_context" in prepared:
        prepared["conversation_context"] = _redact_messages(
            prepared["conversation_context"]
        )
    if "tool_calls" in prepared:
        prepared["tool_calls"] = _redact_tool_calls(prepared["tool_calls"])
    for field in ("runtime", "metadata"):
        if field in prepared:
            prepared[field] = _redact_named_content(prepared[field])
    if "feedback" in prepared:
        prepared["feedback"] = _redact_feedback(prepared["feedback"])
    for key, value in tuple(prepared.items()):
        if key in CONTENT_FIELD_NAMES:
            prepared[key] = _redact_value(value)
    return prepared


def _redact_messages(value: Any) -> Any:
    if isinstance(value, Mapping):
        value = [value]
        unwrap = True
    elif isinstance(value, list):
        unwrap = False
    else:
        return _redact_value(value)
    messages = []
    for item in value:
        if not isinstance(item, Mapping):
            messages.append(_redact_named_content(item))
            continue
        message = dict(item)
        for key, nested in tuple(message.items()):
            field = str(key).lower()
            if (
                key == "role" or field in PRESERVED_NAMED_FIELDS
            ) and not _is_composite_value(nested):
                continue
            if key in CONTENT_FIELD_NAMES:
                message[key] = _redact_value(nested)
            else:
                message[key] = _redact_named_content(
                    nested,
                    structural_descriptor=field in STRUCTURAL_DESCRIPTOR_FIELDS,
                )
        messages.append(message)
    return messages[0] if unwrap else messages


def _redact_tool_calls(value: Any) -> Any:
    if isinstance(value, Mapping):
        value = [value]
        unwrap = True
    elif isinstance(value, list):
        unwrap = False
    else:
        return value
    calls = []
    for item in value:
        if isinstance(item, list):
            calls.append(_redact_tool_calls(item))
            continue
        if not isinstance(item, Mapping):
            calls.append(item)
            continue
        call = dict(item)
        for key, nested in tuple(call.items()):
            field = str(key).lower()
            if field in TOOL_STRUCTURE_FIELDS:
                call[key] = _redact_tool_calls(nested)
                continue
            if (
                key in {"name", "tool"} or field in PRESERVED_NAMED_FIELDS
            ) and not _is_composite_value(nested):
                continue
            if key in {"arguments", "result", "error"}:
                call[key] = _redact_value(nested)
            else:
                call[key] = _redact_named_content(
                    nested,
                    structural_descriptor=field in STRUCTURAL_DESCRIPTOR_FIELDS,
                )
        calls.append(call)
    return calls[0] if unwrap else calls


def _redact_feedback(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    feedback = dict(value)
    for key, nested in tuple(feedback.items()):
        if key in {"rationale", "correction"}:
            feedback[key] = _redact_value(nested)
        elif key not in {"polarity", "source"}:
            feedback[key] = _redact_named_content(nested)
    return feedback


def _redact_named_content(
    value: Any,
    *,
    structural_descriptor: bool = False,
) -> Any:
    """Redact unknown runtime/metadata strings while preserving schema fields."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [
            _redact_named_content(
                item,
                structural_descriptor=structural_descriptor,
            )
            for item in value
        ]
    if isinstance(value, Mapping):
        redacted = {}
        for key, item in value.items():
            field = str(key).lower()
            if field in MESSAGE_STRUCTURE_FIELDS:
                redacted[key] = _redact_messages(item)
            elif field in TOOL_STRUCTURE_FIELDS:
                redacted[key] = _redact_tool_calls(item)
            elif field in CONTENT_FIELD_NAMES:
                redacted[key] = _redact_value(item)
            elif (
                field == "name"
                and structural_descriptor
                and not _is_composite_value(item)
            ):
                redacted[key] = item
            elif field in PRESERVED_NAMED_FIELDS and not _is_composite_value(item):
                redacted[key] = item
            else:
                redacted[key] = _redact_named_content(
                    item,
                    structural_descriptor=(
                        field in STRUCTURAL_DESCRIPTOR_FIELDS
                    ),
                )
        return redacted
    return value


def _redact_value(value: Any) -> Any:
    """Redact every string in an explicitly content-bearing subtree."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _redact_value(item) for key, item in value.items()}
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
