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
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
)

from src.hephaestus.artifact_io import atomic_write_text
from src.hephaestus.datasets.embedding_providers import (
    OpenAIEmbeddingProvider,
    validate_embedding_vectors,
)
from src.hephaestus.datasets.evaluation_assets import (
    filter_synthetic_cases,
    has_scoreable_rubric,
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
    build_episode_guideline_candidate_rows,
    build_episode_guideline_candidate_texts,
    cluster_records_fixed_count,
    cluster_to_dict,
    dense_vectors_to_sparse,
    match_clusters_to_trusted_intents,
    match_to_dict,
)
from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.control_jsonl import (
    parse_strict_json_object,
    read_strict_jsonl_objects,
    resolve_local_authority_file,
)
from src.hephaestus.evaluation_assets.dependencies import (
    build_stage_seven_dependency,
    build_stage_six_dependency,
    dependency_matches,
    fingerprinted_members,
)
from src.hephaestus.evaluation_assets.durability import (
    STAGE_SPECIFICATIONS,
    EvaluationAssetImmutableError,
    EvaluationAssetIntegrityError,
    EvaluationAssetLegacyError,
    build_stage_receipt,
    load_completed_release_handoff_control,
    mutable_rebuild_boundary,
    persisted_json_sha256,
    validate_stage_receipt_payload,
    verify_completed_release_candidate,
    verify_raw_snapshot_floor,
    verify_released_asset,
    verify_stage_receipt,
)
from src.hephaestus.evaluation_assets.input_contract import (
    canonical_user_intent_text,
    effective_route,
    episode_tool_names,
    record_user_messages,
    redact_correctness_signals,
    validate_input_records,
)
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.provenance import (
    PROMPT_REVISIONS,
    build_algorithm_inventory,
    build_provenance,
    build_provider_call,
    build_stage_provenance,
    not_applicable,
    provider_settings,
    sanitize_call_metadata,
    unavailable,
    validate_build_provenance,
    validate_current_stage_provenance,
    working_source_identity,
    write_provider_call_ledger,
)
from src.hephaestus.evaluation_assets.publication import (
    InstalledGeneration,
    install_generation,
    validate_historical_generation,
)
from src.hephaestus.evaluation_assets.review import (
    ReviewIntegrityError,
    build_duplicate_families,
    build_review_finalization,
    build_review_item,
    case_content_fingerprint,
    decision_set_fingerprint,
    inherit_review_decision,
    parse_review_finalization,
    record_review_decision,
    review_set_fingerprint,
    validate_duplicate_family,
    validate_review_finalization,
)
from src.hephaestus.evaluation_assets.split_isolation import (
    assess_correctness_eligibility_records,
    build_trusted_split_plan,
    eligibility_by_record_id,
    expand_trusted_split_plan,
    model_visible_context,
    parent_assignments_by_group_id,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    compile_evaluation_guidelines as _compile_evaluation_guidelines,  # noqa: F401
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    compile_applicability_contract,
    evaluate_applicability_contract,
    extract_episode_facts,
    normalize_applicability_contract,
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
from src.hephaestus.evaluation_assets.stage_three_contract import (
    validate_stage_three_identities as _validate_stage_three_identities,
)
from src.hephaestus.evaluation_assets.trust_tiers import (
    INFERRED_FROM_TRUSTED_FEEDBACK,
    SYNTHETIC_FROM_TRUSTED_RUBRIC,
    TRUSTED_FEEDBACK,
)
from src.hephaestus.evaluation_assets.workspace import (
    EvaluationAssetLayout,
    utc_now,
)

LABELING_QUEUE_SAMPLE_RATIO = 0.1
LABELING_QUEUE_MAX_PER_CLUSTER = 3
LABELING_QUEUE_ACQUISITION = {
    "purpose": "correctness_label_acquisition",
    "method": "deterministic_centroid_nearest",
    "sampling_semantics": "non_probability",
}
GUIDELINE_CANDIDATE_CLUSTER_TOP_K = 9
GUIDELINE_CANDIDATE_EPISODE_TOP_K = 9
GUIDELINE_CANDIDATE_MAX_PER_EPISODE = 10
GUIDELINE_CANDIDATE_EXHAUSTIVE_ROUTE_LIMIT = 20
GUIDELINE_APPLICABILITY_MAX_GROUPS_PER_CALL = 12
GUIDELINE_APPLICABILITY_MAX_CANDIDATE_PAIRS_PER_CALL = 72
PUBLISHED_DATASET_SPLITS = (
    "train",
    "validation",
    "test",
    "regression_trusted",
)


def _local_authority_bytes(
    layout: EvaluationAssetLayout,
    path: Path,
) -> bytes:
    """Read one exact pipeline authority file through its bound local handle."""
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read",
    )
    if authority.data is None:
        raise ValueError("pipeline authority read did not return bytes")
    return authority.data


def _optional_local_authority_json(
    layout: EvaluationAssetLayout,
    path: Path,
) -> dict[str, Any]:
    """Read one optional strict control object without split presence probes."""
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read_optional",
    )
    if not authority.exists:
        return {}
    if authority.data is None:
        raise ValueError("optional pipeline authority read did not return bytes")
    return parse_strict_json_object(authority.data)


def _local_authority_json(
    layout: EvaluationAssetLayout,
    path: Path,
) -> dict[str, Any]:
    """Parse one required strict pipeline control object from bound bytes."""
    return parse_strict_json_object(_local_authority_bytes(layout, path))


def _local_authority_sha256(
    layout: EvaluationAssetLayout,
    path: Path,
) -> str:
    """Hash the exact bytes returned by one bound pipeline authority read."""
    return hashlib.sha256(_local_authority_bytes(layout, path)).hexdigest()


EVIDENCE_EXTRACTION_PROMPT = """\
Extract atomic evaluation evidence from explicit user feedback. Return one JSON
object with an `evidence` array preserving every `record_id`. The feedback is
trusted evidence; the prior conversation, previous assistant output, ordered
episode, and tool calls are context, not an answer key. When an episode is
present, use its event order to interpret multi-turn behavior, tool arguments,
tool results, and tool errors. Use the observed tool trajectory to ground which
action or outcome the feedback refers to and cite precise `tool_calls` or
`episode.events` pointers when relevant. A returned tool result proves only
that an outcome was observed; it does not prove that the tool choice, arguments,
state change, or overall behavior was correct. Record ambiguity as uncertainty.
Each item must contain record_id, intent_label, confidence (0..1), observations,
requested_corrections, and uncertainties. Each observation must contain claim,
evidence_type, evidence_pointer, and polarity. Record only claims directly
supported by the supplied feedback or correction. Do not generalize a
case-specific preference into a universal rule. Never invent environment facts,
private identifiers, tool results, or unsupported correctness requirements.
"""

GUIDELINE_SYNTHESIS_PROMPT = """\
Create reusable evaluation guidelines from trusted feedback evidence grouped by
route. Return one JSON object with a `guidelines` array. Every supplied record_id
must appear in at least one guideline's source_record_ids. Aggregate compatible
evidence and keep conflicting or case-specific evidence explicit rather than
silently resolving it. Use only record_id values present in the supplied
evidence: never invent, transform, or copy an ID from another field. Each
guideline's source_record_ids must be a nonempty subset of those supplied IDs.
Only group records when every criterion is supported by every source record in
the guideline. Do not emit source_record_ids inside criterion objects; criteria
inherit the validated parent guideline's complete source_record_ids. The
supplied record_id values are short opaque aliases; preserve them exactly even
when the example content resembles another task. Each guideline must contain
intent_label, description, route,
source_record_ids, confidence (0..1), criteria, tool_expectations,
reference_output, conflicts, and uncertainties. Each criterion must contain
kind (required, prohibited, or preferred), statement, dimension, severity
(critical, major, or minor), applicability, scoring, evidence_required, and
evaluator. applicability must be a nonempty string or a
JSON object, scoring must be a nonempty string, and evidence_required must be a
JSON boolean (`true` or `false`), never a string, number, array, or object.
intent_label, description, route, criterion statements, and criterion dimensions
must be nonempty strings. source_record_ids and criteria must be nonempty JSON
arrays. conflicts and uncertainties must be JSON arrays containing only strings;
use `[]` when there are none. tool_expectations must be a JSON object; use `{}`
when there are none. reference_output must be a string or null. Evaluator must
contain exactly type and fallback, both strings selected from the evaluator
types below;
prefer state_check or deterministic_check when the evidence is
objectively verifiable, semantic_trajectory only when the path itself matters,
llm_judge for qualitative criteria, and human_review when evidence is
insufficient. Every example includes `observed_tool_calls` with the actual
redacted arguments and an outcome_status of result_returned, error_returned, or
not_recorded. Consider those calls when defining tool expectations, evaluator
plans, evidence requirements, applicability, state-change criteria, and failure
conditions; do not ignore them when the feedback concerns task completion or a
tool-backed action. These calls are observed context, not independent
correctness evidence: result_returned does not establish that the tool, its
arguments, or the resulting state was correct. Prefer semantic tool expectations
and permit multiple valid solution paths. Require a literal tool name only when
the supplied evidence establishes that exact contract. reference_output must
never be copied from a previous assistant response. Return only the JSON object,
with no markdown or explanatory text.
"""

EPISODE_GUIDELINE_APPLICABILITY_PROMPT = """\
Return exactly one applicability decision for every supplied `decision_id`.
Do not omit, merge, rename, invent, or duplicate a decision. Evaluate every
candidate guideline independently.

A guideline applies only when the episode creates a distinct, user-facing
evaluation obligation within that guideline's core target scenario.
Applicability does not mean the agent handled the obligation correctly.

For each candidate:

1. Read all user messages in order and identify the concrete request, question,
   constraint, authorization, correction, or withdrawal that could activate
   the guideline. Evaluate an earlier requirement while it was active even if
   the user later changed direction.
2. Derive the core activation conditions from the intent label, description,
   required or prohibited criteria, and their applicability. If the core
   scenario combines conditions, require all defining conditions unless the
   guideline explicitly presents them as alternatives.
3. Do not activate a guideline from one incidental, preferred, or subordinate
   criterion; from a broad topical resemblance; or from only one fragment of a
   compound scenario. The episode must match the guideline as a whole.
4. Tool calls, arguments, results, errors, state summaries, and
   `structured_episode_facts` may resolve state, entity, timing, or scope for a
   user-anchored requirement. They cannot create user intent, combine unrelated
   branches, or prove correct behavior.
5. A guideline for delivering information requires that the user explicitly
   ask to receive that information, accept an offer to receive it, or require
   it as the user-facing result. Merely specifying desired properties, answering
   a clarification, or requiring an internal lookup for another action does
   not create a separate information-delivery obligation.
6. A request for an unavailable or unsupported action can activate a guideline
   requiring a limitation or alternative. Independent obligations can activate
   multiple guidelines; never force one best match.

Exclude a guideline when its core activation evidence is absent or comes from
different requests, entities, branches, or times. In the reason, identify the
user requirement supporting each selected guideline.

Return only one JSON object with a `decisions` array. Every item must contain
`decision_id`, `applicable_guideline_ids`, `confidence`, `reason`, and
`evidence_pointers`. Use only IDs from that decision's
`candidate_guideline_ids`. The two pointer fields must be arrays of strings and
`confidence` must be between 0 and 1. Before returning, verify that the output
contains the exact set of supplied `decision_id` values.
"""

INFERENCE_PROMPT = EPISODE_GUIDELINE_APPLICABILITY_PROMPT + """\

When mode is `legacy_cluster_rubric`, infer reviewable case rubrics for
unlabeled intent clusters using only the supplied trusted evaluation guideline
as correctness evidence. Return one JSON object with a `rubrics` array
preserving every `cluster_id`. Each item must contain cluster_id, intent_label,
confidence (0..1), must, must_not, should, deterministic_checks,
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

SCHEMA_REGENERATION_PROMPT = """\
The previous response failed strict schema validation. Generate a new response
from scratch from the same user payload; do not attempt to quote, patch, or
refer to the previous response. Preserve every required input identifier
exactly, use only identifiers supplied in the payload, emit every required
field with the exact requested JSON type, and return only the requested JSON
object. If the evidence cannot support a field, use the contract's explicit
empty or null value rather than inventing content.
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
        applicability_contracts: Optional[
            Mapping[str, Mapping[str, Any]]
        ] = None,
        applicability_unknown_policy: Optional[str] = None,
        applicability_semantic_review_intent_labels: Optional[
            Collection[str]
        ] = None,
    ) -> None:
        self.layout = layout
        self.config: EvaluationAssetConfig | None = None
        self.lineage: dict[str, Any] = {}
        self._injected_rubric_provider = rubric_provider
        self._injected_embedding_provider = embedding_provider
        self._injected_applicability_contracts = (
            {
                str(intent_label): normalize_applicability_contract(contract)
                for intent_label, contract in applicability_contracts.items()
            }
            if applicability_contracts is not None
            else None
        )
        if applicability_unknown_policy is None:
            applicability_unknown_policy = (
                "not_supported"
                if applicability_contracts is not None
                else "llm_fallback"
            )
        if applicability_unknown_policy not in {
            "llm_fallback",
            "not_supported",
        }:
            raise ValueError(
                "applicability_unknown_policy must be 'llm_fallback' or "
                "'not_supported'"
            )
        self._applicability_unknown_policy = applicability_unknown_policy
        raw_review_labels = applicability_semantic_review_intent_labels or ()
        review_labels = frozenset(str(item).strip() for item in raw_review_labels)
        if "" in review_labels:
            raise ValueError(
                "applicability_semantic_review_intent_labels cannot contain "
                "an empty label"
            )
        self._applicability_semantic_review_intent_labels = review_labels
        self.rubric_provider = rubric_provider
        self.embedding_provider = embedding_provider
        self._provider_identities: dict[str, dict[str, Any]] = {}
        self._provider_settings: dict[str, dict[str, Any]] = {}
        self._stage_call_rows: list[dict[str, Any]] = []
        self._stage_eight_manifest: dict[str, Any] = {}
        self._pending_generation: InstalledGeneration | None = None
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
            raise ValueError(f"Unsupported rubric provider: {self.config.rubric_provider}")

        if self._injected_embedding_provider is not None:
            self.embedding_provider = self._injected_embedding_provider
            embedding_source = "injected"
        elif self.config.embedding_provider == "openai":
            self.embedding_provider = OpenAIEmbeddingProvider(model=self.config.embedding_model)
            embedding_source = "default"
        elif self.config.embedding_provider == "tfidf":
            self.embedding_provider = None
            embedding_source = "default"
        else:
            raise ValueError(f"Unsupported embedding provider: {self.config.embedding_provider}")

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
        self._provider_settings = {
            "rubric": provider_settings(
                self.rubric_provider,
                role="rubric",
                identity=self._provider_identities["rubric"],
                pipeline_batch_size=self.config.batch_size,
            ),
            "embedding": provider_settings(
                self.embedding_provider,
                role="embedding",
                identity=self._provider_identities["embedding"],
                pipeline_batch_size=self.config.batch_size,
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
                raise ValueError("Default provider identity requires non-empty provider and model")
            return {"provider": provider_name, "model": model, "source": source}

        declared = {
            "provider_name": getattr(provider, "provider_name", None),
            "model": getattr(provider, "model", None),
        }
        unavailable_fields = [
            field for field, value in declared.items() if not isinstance(value, str) or not value.strip()
        ]
        if unavailable_fields:
            return {
                "provider": (
                    str(declared["provider_name"]).strip()
                    if "provider_name" not in unavailable_fields
                    else "unavailable"
                ),
                "model": (
                    str(declared["model"]).strip() if "model" not in unavailable_fields else "unavailable"
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
        """Validate complete injected bindings before any authority mutation."""
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
                    f"injected {role} provider identity is unavailable; " f"declare non-empty {missing}"
                )
            provider_settings(
                provider,
                role=role,
                identity=identity,
                pipeline_batch_size=self.config.batch_size,
            )

    def _provider_identity_for_stage(
        self,
        stage: PipelineStage,
    ) -> dict[str, Any]:
        roles = STAGE_SPECIFICATIONS[stage].provider_roles
        return (
            {role: dict(self._provider_settings[role]) for role in roles}
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
            identity = self._provider_identities["rubric"]
            settings = self._provider_settings["rubric"]["settings"]
            for schema_attempt in range(2):
                call_prompt = (
                    system_prompt
                    if schema_attempt == 0
                    else f"{system_prompt}\n\n{SCHEMA_REGENERATION_PROMPT}"
                )
                _discard_provider_metadata(self.rubric_provider)
                response = self.rubric_provider.generate_json(call_prompt, payload)
                metadata = _drain_provider_metadata(self.rubric_provider)
                self._stage_call_rows.append(
                    build_provider_call(
                        stage=stage.value,
                        ordinal=len(self._stage_call_rows) + 1,
                        provider_role="rubric",
                        provider=identity["provider"],
                        model=identity["model"],
                        request={
                            "interface": "generate_json-v1",
                            "system_prompt": call_prompt,
                            "payload": dict(payload),
                            "provider": identity["provider"],
                            "model": identity["model"],
                            "settings": settings,
                        },
                        response=response,
                        metadata=metadata,
                    )
                )
                try:
                    if not isinstance(response, Mapping):
                        raise ValueError(
                            "Rubric provider response must be a JSON object"
                        )
                    return normalize(response)
                except ValueError:
                    if schema_attempt == 0:
                        continue
                    raise
            raise AssertionError("schema regeneration loop did not return")
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
            _discard_provider_metadata(self.embedding_provider)
            response = self.embedding_provider.embed_texts(texts)
            metadata = _drain_provider_metadata(self.embedding_provider)
        except Exception as exc:
            raise ProviderCallError(
                stage=stage,
                provider=self._provider_identities["embedding"]["provider"],
                model=self._provider_identities["embedding"]["model"],
                cause=exc,
            ) from exc
        normalized = validate_embedding_vectors(
            response,
            expected_count=len(texts),
            source="embedding provider result",
        )
        identity = self._provider_identities["embedding"]
        settings = self._provider_settings["embedding"]["settings"]
        self._stage_call_rows.append(
            build_provider_call(
                stage=stage.value,
                ordinal=len(self._stage_call_rows) + 1,
                provider_role="embedding",
                provider=identity["provider"],
                model=identity["model"],
                request={
                    "interface": "embed_texts-v1",
                    "texts": [str(text) for text in texts],
                    "provider": identity["provider"],
                    "model": identity["model"],
                    "settings": settings,
                },
                response=normalized,
                metadata=metadata,
            )
        )
        return normalized

    @classmethod
    def create(
        cls,
        tenants_root: Path,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        rubric_provider: Optional[RubricProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        applicability_contracts: Optional[
            Mapping[str, Mapping[str, Any]]
        ] = None,
        applicability_unknown_policy: Optional[str] = None,
        applicability_semantic_review_intent_labels: Optional[
            Collection[str]
        ] = None,
        initial_status: str = "draft",
        *,
        repository_base: Path | None = None,
    ) -> "EvaluationAssetPipeline":
        """Create a self-contained workspace by copying both source files."""
        layout = EvaluationAssetLayout(
            tenants_root=tenants_root,
            tenant_id=config.tenant_id,
            asset_id=config.asset_id,
            repository_base=(repository_base if repository_base is not None else Path.cwd()),
        )
        layout.initialize(
            config,
            feedback_source,
            unlabeled_source,
            initial_status=initial_status,
        )
        return cls(
            layout,
            rubric_provider=rubric_provider,
            embedding_provider=embedding_provider,
            applicability_contracts=applicability_contracts,
            applicability_unknown_policy=applicability_unknown_policy,
            applicability_semantic_review_intent_labels=(
                applicability_semantic_review_intent_labels
            ),
        )

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
            handoff_control = load_completed_release_handoff_control(self.layout)
            recovered = self.layout._recover_locked()
            if recovered:
                handoff_control = load_completed_release_handoff_control(self.layout)
            state = handoff_control[0] if handoff_control is not None else self.layout.load_state()
            if state.status == "released":
                verify_released_asset(self.layout, state)
                if recovered:
                    if _preflight_accepted_callback is not None:
                        _preflight_accepted_callback()
                    return state
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
            if handoff_control is None:
                verify_raw_snapshot_floor(self.layout, state)
            if handoff_control is not None and not config_updates:
                self.config = handoff_control[1]
                self.lineage = _optional_local_authority_json(
                    self.layout,
                    self.layout.lineage_path,
                )
                return self._run_locked(
                    _preflight_accepted_callback,
                    completed_release_candidate=True,
                )
            self.config = handoff_control[1] if handoff_control is not None else self.layout.load_config()
            current_config = self.config
            prospective_config = (
                self.layout._resolve_config_updates(current_config, config_updates)
                if config_updates is not None
                else current_config
            )
            self.config = prospective_config
            try:
                self._validate_injected_provider_identities()
            finally:
                self.config = current_config
            self.last_revision = (
                self.layout._revise_config_locked(config_updates) if config_updates is not None else None
            )
            self.config = self.layout.load_config()
            self.lineage = _optional_local_authority_json(
                self.layout,
                self.layout.lineage_path,
            )
            self._configure_providers()
            return self._run_locked(
                _preflight_accepted_callback,
                completed_release_candidate=False,
                review_authorized=False,
            )

    def finalize_review(
        self,
        *,
        reviewer: str,
        expected_review_set_fingerprint: str,
        expected_decision_set_fingerprint: str,
        note: str | None = None,
        lock_timeout: float = 0,
        _lock_acquired_callback: Optional[Callable[[], None]] = None,
        _preflight_accepted_callback: Optional[Callable[[], None]] = None,
    ) -> PipelineState:
        """Freeze the exact current review set and continue into Stage 8."""
        with self.layout.asset_lock(lock_timeout):
            if _lock_acquired_callback is not None:
                _lock_acquired_callback()
            self.layout._recover_locked()
            state = self.layout.load_state()
            if state.legacy_completed:
                raise EvaluationAssetLegacyError(
                    self.layout.tenant_id,
                    self.layout.asset_id,
                    "explicit verification and adoption are required",
                )
            if state.status == "released":
                verify_released_asset(self.layout, state)
            elif state.status not in {"awaiting_review", "failed"}:
                raise ValueError("review finalization requires an awaiting-review asset")
            self.config = self.layout.load_config()
            self.lineage = _optional_local_authority_json(
                self.layout,
                self.layout.lineage_path,
            )
            self._configure_providers()
            authority = self._current_review_authority(
                state,
                compare_current_dependencies=state.status != "released",
            )
            current_set = str(authority["review_set_fingerprint"])
            if expected_review_set_fingerprint != current_set:
                raise ReviewIntegrityError("review set changed before finalization")
            current_decisions = str(authority["decision_set_fingerprint"])
            if expected_decision_set_fingerprint != current_decisions:
                raise ReviewIntegrityError("decision set changed before finalization")
            finalization = self._current_review_finalization(authority)
            if finalization is None:
                if state.status == "released":
                    raise ReviewIntegrityError("released review finalization authority is missing")
                finalization = build_review_finalization(
                    review_items=authority["review_items"],
                    dependencies=authority["dependencies"],
                    decisions=authority["decisions"],
                    held_cases=authority["held_cases"],
                    stage7_receipt_sha256=str(authority["stage7_receipt_sha256"]),
                    trusted_count=int(authority["trusted_count"]),
                    reviewer=reviewer,
                    timestamp=utc_now(),
                    note=note,
                )
                self.layout._append_jsonl_once(
                    self.layout.review_finalizations_path,
                    finalization,
                    identity_fields=("finalization_id",),
                )
                authority = {
                    **authority,
                    "finalizations": [
                        *authority["finalizations"],
                        finalization,
                    ],
                }
            if state.status == "released":
                if _preflight_accepted_callback is not None:
                    _preflight_accepted_callback()
                return state
            return self._run_locked(
                _preflight_accepted_callback,
                completed_release_candidate=False,
                review_authorized=True,
            )

    def _run_locked(
        self,
        preflight_accepted_callback: Optional[Callable[[], None]] = None,
        *,
        completed_release_candidate: bool,
        review_authorized: bool = False,
    ) -> PipelineState:
        """Run while the caller holds the asset mutation lock."""
        if completed_release_candidate:
            handoff_control = load_completed_release_handoff_control(self.layout)
            if handoff_control is None:
                raise EvaluationAssetIntegrityError(
                    self.layout.tenant_id,
                    self.layout.asset_id,
                    "completed release candidate control disappeared under lock",
                )
            state = handoff_control[0]
            self._pending_generation = verify_completed_release_candidate(
                self.layout,
                state,
            )
            boundary = None
        else:
            state = self.layout.load_state()
            boundary = mutable_rebuild_boundary(
                self.layout,
                state,
                self.config,
                STAGE_PROMPTS,
                {stage: self._provider_identity_for_stage(stage) for stage in PipelineStage},
            )
            state.schema_version = "fapo-evaluation-asset-state-v2"
        if boundary is not None:
            boundary_index = list(PipelineStage).index(boundary)
            suffix_states = state.stages[boundary_index:]
            if any(item.status != "pending" or item.receipt_sha256 for item in suffix_states):
                state = self.layout._invalidate_checkpoints_locked(state, boundary)
        if not review_authorized and boundary == PipelineStage.DATASET_SPLITS:
            authority = self._current_review_authority(
                state,
                compare_current_dependencies=True,
            )
            finalization = self._current_review_finalization(authority)
            if finalization is None:
                if (
                    state.status != "awaiting_review"
                    or state.current_stage is not None
                    or state.error is not None
                ):
                    state.status = "awaiting_review"
                    state.current_stage = None
                    state.error = None
                    self.layout.save_state(state)
                    self.layout.append_event(
                        "review_required",
                        {"stage": PipelineStage.SYNTHETIC_COVERAGE.value},
                    )
                return state
            review_authorized = True
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
            self._stage_call_rows = []
            try:
                counts = self._run_stage(stage)
                self._finalize_stage_outputs(stage)
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
            validate_stage_receipt_payload(
                receipt,
                expected_stage=stage,
                expected_origin="native",
                expected_counts=counts,
                expected_provider_identity=self._provider_identity_for_stage(stage),
            )
            self.layout._write_authority_json(
                self.layout.receipt_path(stage),
                receipt,
            )
            receipt_sha256 = _local_authority_sha256(
                self.layout,
                self.layout.receipt_path(stage),
            )
            if receipt_sha256 != persisted_json_sha256(receipt):
                raise ValueError("persisted stage receipt authority is inconsistent")
            stage_state.receipt_sha256 = receipt_sha256
            stage_state.status = "completed"
            stage_state.completed_at = completed_at
            stage_state.message = _stage_message(stage, counts)
            self.layout.save_state(state)
            if stage == PipelineStage.SYNTHETIC_COVERAGE:
                _publication_fault_point(
                    "after_stage_7_receipt_state_complete"
                )
            if stage == PipelineStage.DATASET_SPLITS:
                self._pending_generation = verify_completed_release_candidate(
                    self.layout,
                    state,
                )
                _publication_fault_point("after_stage_8_receipt_state_complete")
            self.layout.append_event(
                "stage_completed",
                {"stage": stage.value, "counts": counts},
            )
            if stage == PipelineStage.SYNTHETIC_COVERAGE and not review_authorized:
                state.status = "awaiting_review"
                state.current_stage = None
                state.error = None
                self.layout.save_state(state)
                self.layout.append_event(
                    "review_required",
                    {"stage": stage.value},
                )
                return state

        state.current_stage = None
        state.error = None
        self.layout.save_state(state)
        generation = self._pending_generation
        if generation is None:
            manifest = _local_authority_json(
                self.layout,
                self.layout.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "generation_manifest.json",
                ),
            )
            generation_id = str(manifest.get("generation_id") or "")
            generation = validate_historical_generation(
                self.layout.generations_root / generation_id,
                expected_tenant_id=self.layout.tenant_id,
                expected_asset_id=self.layout.asset_id,
                trusted_root=self.layout.tenant_root,
            )
        return self.layout._publish_release_locked(state, generation)

    def _current_review_authority(
        self,
        state: PipelineState,
        *,
        compare_current_dependencies: bool,
    ) -> Dict[str, Any]:
        """Load and authenticate the complete review authority for Stage 7."""
        stage = PipelineStage.SYNTHETIC_COVERAGE
        stage_state = next(item for item in state.stages if item.stage == stage.value)
        if stage_state.status != "completed" or not stage_state.receipt_sha256:
            raise ReviewIntegrityError("review authority requires a completed Stage 7 receipt")
        verify_stage_receipt(
            self.layout,
            state,
            stage,
            self.config,
            prompt_values=STAGE_PROMPTS[stage],
            provider_identity=(
                self._provider_identity_for_stage(stage) if compare_current_dependencies else None
            ),
            compare_current_dependencies=compare_current_dependencies,
        )
        review_items = _load_jsonl(self.layout.artifact_path(stage, "derived_review_items.jsonl"))
        held_cases = _load_jsonl(self.layout.artifact_path(stage, "held_derived_cases.jsonl"))
        dependencies = _review_dependencies_by_case(
            self.layout,
            review_items,
        )
        decisions = self.layout._read_control_log(self.layout.review_decisions_path)
        finalizations = self.layout._read_control_log(self.layout.review_finalizations_path)
        trusted_cases = [
            *_load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "trusted_cases.jsonl",
                )
            ),
            *_load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "protected_trusted_cases.jsonl",
                )
            ),
        ]
        held_ids = {str(row.get("case_id")) for row in held_cases}
        trusted_count = sum(str(case["case_id"]) not in held_ids for case in trusted_cases)
        receipt_sha256 = "sha256:" + stage_state.receipt_sha256
        current_set = review_set_fingerprint(
            stage7_receipt_sha256=receipt_sha256,
            review_items=review_items,
            held_cases=held_cases,
            dependencies=dependencies,
        )
        current_decisions = decision_set_fingerprint(
            review_set_fingerprint=current_set,
            review_items=review_items,
            dependencies=dependencies,
            decisions=decisions,
        )
        return {
            "review_items": review_items,
            "held_cases": held_cases,
            "dependencies": dependencies,
            "decisions": decisions,
            "finalizations": finalizations,
            "stage7_receipt_sha256": receipt_sha256,
            "trusted_count": trusted_count,
            "review_set_fingerprint": current_set,
            "decision_set_fingerprint": current_decisions,
        }

    @staticmethod
    def _current_review_finalization(
        authority: Mapping[str, Any],
    ) -> Dict[str, Any] | None:
        """Return the sole finalization matching every current authority input."""
        current_set = str(authority["review_set_fingerprint"])
        valid: List[Dict[str, Any]] = []
        for raw in authority["finalizations"]:
            parsed = parse_review_finalization(raw)
            if parsed["review_set_fingerprint"] != current_set:
                continue
            try:
                candidate = validate_review_finalization(
                    parsed,
                    review_items=authority["review_items"],
                    dependencies=authority["dependencies"],
                    decisions=authority["decisions"],
                    held_cases=authority["held_cases"],
                    stage7_receipt_sha256=str(authority["stage7_receipt_sha256"]),
                )
            except (ReviewIntegrityError, TypeError, ValueError):
                continue
            if candidate["counts"]["trusted"] != authority["trusted_count"]:
                continue
            valid.append(candidate)
        if len(valid) > 1:
            raise ReviewIntegrityError("multiple current review finalizations exist")
        return valid[0] if valid else None

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

    def _finalize_stage_outputs(self, stage: PipelineStage) -> None:
        """Persist stage-local provenance and complete Stage 8 release inputs."""
        specification = STAGE_SPECIFICATIONS[stage]
        calls: Sequence[Mapping[str, Any]] | None = None
        if specification.provider_roles:
            calls = list(self._stage_call_rows)
            write_provider_call_ledger(
                self.layout.artifact_path(stage, "provider_calls.jsonl"),
                calls,
                stage=stage.value,
                trusted_root=self.layout.tenants_root,
            )
        provider_identity = self._provider_identity_for_stage(stage)
        prompt_values = STAGE_PROMPTS.get(stage, {})
        code = working_source_identity(Path(__file__).resolve().parents[3])
        seeds = _stage_seeds(
            stage,
            self.config,
            call_count=len(calls or []),
        )
        algorithms = _stage_algorithms(
            stage,
            self.config,
            extension=bool(self.lineage),
        )
        stage_provenance = build_stage_provenance(
            stage=stage.value,
            provider_identity=provider_identity,
            prompt_values=prompt_values,
            calls=calls,
            code=code,
            seeds=seeds,
            algorithms=algorithms,
        )
        validate_current_stage_provenance(
            stage_provenance,
            stage=stage.value,
            provider_identity=provider_identity,
            prompt_values=prompt_values,
            calls=calls,
            code=code,
            seeds=seeds,
            algorithms=algorithms,
        )
        self.layout._write_authority_json(
            self.layout.stage_provenance_path(stage),
            stage_provenance,
        )
        if stage == PipelineStage.DATASET_SPLITS:
            self._finalize_stage_eight_artifacts()

    def _finalize_stage_eight_artifacts(self) -> None:
        """Build provenance, install a generation, and write immutable paths."""
        calls: list[dict[str, Any]] = []
        for stage in tuple(PipelineStage)[2:7]:
            calls.extend(
                read_strict_jsonl_objects(
                    self.layout.artifact_path(stage, "provider_calls.jsonl"),
                    trusted_root=self.layout.tenants_root,
                )
            )
        input_manifest = _local_authority_json(
            self.layout,
            self.layout.artifact_path(
                PipelineStage.RAW_INPUTS,
                "input_manifest.json",
            ),
        )
        copied_inputs = {}
        for name, path in (
            ("labeled_feedback", self.layout.feedback_path),
            ("unlabeled", self.layout.unlabeled_path),
        ):
            details = input_manifest["inputs"][name]
            source_bytes = _local_authority_bytes(self.layout, path)
            if hashlib.sha256(source_bytes).hexdigest() != details["sha256"]:
                raise ValueError("copied input authority changed after validation")
            copied_inputs[name] = {
                "path": path.relative_to(self.layout.root).as_posix(),
                "bytes": len(source_bytes),
                "rows": details["rows"],
                "sha256": details["sha256"],
            }
        review_snapshot_path = self.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "review_snapshot.json",
        )
        review_snapshot_bytes = _local_authority_bytes(
            self.layout,
            review_snapshot_path,
        )
        copied_inputs["review_snapshot"] = {
            "path": review_snapshot_path.relative_to(self.layout.root).as_posix(),
            "bytes": len(review_snapshot_bytes),
            "rows": 1,
            "sha256": hashlib.sha256(review_snapshot_bytes).hexdigest(),
        }
        lineage_files = None
        if self.lineage:
            lineage_files = {
                "lineage_sha256": _local_authority_sha256(
                    self.layout,
                    self.layout.lineage_path,
                ),
                "reuse_manifest_sha256": _local_authority_sha256(
                    self.layout, self.layout.reuse_manifest_path
                ),
                "parent_release": dict(self.lineage.get("parent_release") or {}),
            }
        prompts = {
            name: value for stage_prompts in STAGE_PROMPTS.values() for name, value in stage_prompts.items()
        }
        provenance = build_provenance(
            repository_root=Path(__file__).resolve().parents[3],
            resolved_configuration=self.config.to_dict(),
            copied_inputs=copied_inputs,
            lineage=self.lineage,
            providers=self._provider_settings,
            prompt_values=prompts,
            calls=calls,
            seeds={
                "split": self.config.split_seed,
                "rubric_sampling": {
                    "status": "not_applicable",
                    "reason": "provider_does_not_use_sampling",
                },
                "embedding_sampling": {
                    "status": "not_applicable",
                    "reason": "provider_does_not_use_sampling",
                },
            },
            algorithms=_build_algorithms(self.config, bool(self.lineage)),
            lineage_files=lineage_files,
            created_at=utc_now(),
        )
        validate_build_provenance(provenance)
        self.layout._write_authority_json(
            self.layout.build_provenance_path,
            provenance,
        )
        build_provenance_sha256 = _local_authority_sha256(
            self.layout,
            self.layout.build_provenance_path,
        )
        if build_provenance_sha256 != persisted_json_sha256(provenance):
            raise ValueError("persisted build provenance authority is inconsistent")
        split_paths = {
            split: self.layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
            for split in PUBLISHED_DATASET_SPLITS
        }
        generation = install_generation(
            self.layout.published_datasets,
            tenant_id=self.layout.tenant_id,
            asset_id=self.layout.asset_id,
            split_paths=split_paths,
            build_fingerprint=provenance["identity_sha256"],
            fault_hook=_publication_fault_point,
            trusted_root=self.layout.tenant_root,
        )
        self._pending_generation = generation
        generation_manifest = resolve_local_authority_file(
            generation.generation_dir / "generation_manifest.json",
            self.layout.tenants_root,
            access="read",
        )
        if generation_manifest.data is None:
            raise ValueError("generation manifest authority bytes are missing")
        workspace_generation_manifest = self.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        )
        expected_workspace_manifest = resolve_local_authority_file(
            workspace_generation_manifest,
            self.layout.tenants_root,
            access="read_optional",
        )
        resolve_local_authority_file(
            workspace_generation_manifest,
            self.layout.tenants_root,
            access="write",
            write_data=generation_manifest.data,
            expected_write_data=expected_workspace_manifest.data,
            check_expected_write_data=True,
        )
        manifest = dict(self._stage_eight_manifest)
        generation_directory = self.layout.repository_relative_path(generation.generation_dir)
        manifest["published_datasets"] = {
            "directory": self.layout.published_datasets.relative_to(self.layout.tenant_root).as_posix(),
            "release_pointer": self.layout.release_pointer_path.relative_to(
                self.layout.tenant_root
            ).as_posix(),
            "generation_id": generation.generation_id,
            "generation_manifest_sha256": generation.generation_manifest_sha256,
            "build_provenance_sha256": build_provenance_sha256,
            "build_fingerprint": provenance["identity_sha256"],
            "files": {split: f"{generation_directory}/{split}.jsonl" for split in PUBLISHED_DATASET_SPLITS},
        }
        self.layout._write_authority_json(
            self.layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "dataset_manifest.json",
            ),
            manifest,
        )
        self.layout._write_authority_json(self.layout.manifest_path, manifest)
        _publication_fault_point("after_stage_8_outputs_validated")

    def _validate_raw_inputs(self) -> Dict[str, int]:
        if self.config is None:
            self.config = self.layout.load_config()
        feedback, feedback_row_numbers = _load_jsonl_with_line_numbers(self.layout.feedback_path)
        unlabeled, unlabeled_row_numbers = _load_jsonl_with_line_numbers(self.layout.unlabeled_path)
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
        self.layout._write_authority_json(
            self.layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json"),
            manifest,
        )
        return {"feedback_records": len(feedback), "unlabeled_records": len(unlabeled)}

    def _prepare_inputs(self) -> Dict[str, int]:
        feedback_rows, feedback_row_numbers = _load_jsonl_with_line_numbers(self.layout.feedback_path)
        unlabeled_rows, unlabeled_row_numbers = _load_jsonl_with_line_numbers(self.layout.unlabeled_path)
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
        parent_assignments = {}
        parent_plan_path = self.layout.parent_snapshot / "parent_trusted_split_plan.jsonl"
        if self.lineage and parent_plan_path.is_file():
            parent_assignments = parent_assignments_by_group_id(_load_jsonl(parent_plan_path))
        split_plan = build_trusted_split_plan(
            normalized,
            split_seed=self.config.split_seed,
            parent_assignments=parent_assignments,
        )
        expanded_assignments = {
            assignment.record_id: assignment for assignment in expand_trusted_split_plan(split_plan)
        }
        eligibility = assess_correctness_eligibility_records(normalized)
        eligibility_by_id = eligibility_by_record_id(eligibility)
        for row in normalized:
            record_id = str(row["record_id"])
            assignment = expanded_assignments[record_id]
            decision = eligibility_by_id[record_id]
            row["split_group_id"] = assignment.split_group_id
            row["trusted_split"] = assignment.split
            row["evidence_eligible"] = decision.eligible
            if decision.hold_reason is not None:
                row["hold_reason"] = decision.hold_reason
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
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "trusted_split_plan.jsonl",
            ),
            [entry.to_dict() for entry in split_plan],
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "feedback_eligibility.jsonl",
            ),
            [
                {
                    **entry.to_dict(),
                    "split_group_id": expanded_assignments[entry.record_id].split_group_id,
                    "split": expanded_assignments[entry.record_id].split,
                }
                for entry in eligibility
            ],
        )
        return {"prepared_feedback": len(normalized), "prepared_intents": len(intents)}

    def _create_evaluation_guidelines(self) -> Dict[str, int]:
        normalized = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "normalized_feedback.jsonl",
            )
        )
        normalized_by_id = _unique_rows_by_key(
            normalized,
            key="record_id",
            source="normalized feedback",
        )
        eligible_training = [
            row
            for row in normalized
            if row.get("evidence_eligible") is True and row.get("trusted_split") == "train"
        ]
        eligible_training_ids = {str(row["record_id"]) for row in eligible_training}
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
        existing_evidence = (
            _load_jsonl(evidence_path) if (bool(self.lineage) and evidence_path.is_file()) else []
        )
        existing_evidence_by_id = _unique_rows_by_key(
            existing_evidence,
            key="record_id",
            source="seeded training feedback evidence",
        )
        unexpected_seeded_ids = sorted(set(existing_evidence_by_id) - eligible_training_ids)
        if unexpected_seeded_ids:
            raise ValueError(
                "seeded Stage 3 evidence is not eligible training evidence: "
                + ", ".join(unexpected_seeded_ids)
            )
        pending_training = [
            row for row in eligible_training if str(row["record_id"]) not in existing_evidence_by_id
        ]
        new_evidence = self._extract_feedback_evidence(pending_training)
        evidence = sorted(
            _replace_by_key(existing_evidence, new_evidence, key="record_id"),
            key=lambda item: str(item["record_id"]),
        )
        if {str(row["record_id"]) for row in evidence} != eligible_training_ids:
            raise ValueError("training feedback evidence coverage is incomplete")
        candidates, guidelines = self._synthesize_guidelines(
            evidence,
            normalized_by_id,
        )
        guideline_by_record = _guidelines_by_source_record(guidelines)
        trusted_intents = [
            _trusted_intent_from_guideline(guideline, normalized_by_id) for guideline in guidelines
        ]
        trusted_cases = [
            _trusted_case_with_split_metadata(
                row,
                _rubric_from_guidelines(
                    str(row["record_id"]),
                    guideline_by_record[str(row["record_id"])],
                    self._provider_identities["rubric"]["provider"],
                    self._provider_identities["rubric"]["model"],
                ),
                self.config.asset_id,
                correctness_visibility="reusable_training",
            )
            for row in eligible_training
        ]
        protected_evidence: List[Dict[str, Any]] = []
        protected_candidates: List[Dict[str, Any]] = []
        protected_guidelines: List[Dict[str, Any]] = []
        protected_cases: List[Dict[str, Any]] = []
        protected_units: Dict[tuple[str, str, str, str], List[Dict[str, Any]]] = {}
        for row in normalized:
            split = row.get("trusted_split")
            if row.get("evidence_eligible") is not True or split == "train":
                continue
            if split not in {"validation", "test", "regression"}:
                raise ValueError("eligible feedback has an unsupported trusted split")
            unit = (
                str(split),
                str(row["split_group_id"]),
                str(row["group_id"]),
                str(row["route"]),
            )
            protected_units.setdefault(unit, []).append(row)

        for unit in sorted(protected_units):
            split, split_group_id, group_id, route = unit
            unit_rows = sorted(protected_units[unit], key=lambda item: str(item["record_id"]))
            unit_evidence = self._extract_feedback_evidence(unit_rows)
            unit_candidates, unit_guidelines = self._synthesize_guidelines(
                unit_evidence,
                normalized_by_id,
            )
            scope = {
                "protected_split": split,
                "split_group_id": split_group_id,
                "source_group_id": group_id,
                "visibility": "protected_held_out",
            }
            protected_evidence.extend({**row, **scope} for row in unit_evidence)
            protected_candidates.extend({**row, **scope} for row in unit_candidates)
            protected_guidelines.extend({**row, **scope} for row in unit_guidelines)
            protected_by_record = _guidelines_by_source_record(unit_guidelines)
            protected_cases.extend(
                _trusted_case_with_split_metadata(
                    row,
                    _rubric_from_guidelines(
                        str(row["record_id"]),
                        protected_by_record[str(row["record_id"])],
                        self._provider_identities["rubric"]["provider"],
                        self._provider_identities["rubric"]["model"],
                    ),
                    self.config.asset_id,
                    correctness_visibility="protected_held_out",
                )
                for row in unit_rows
            )

        protected_evidence.sort(key=lambda item: str(item["record_id"]))
        protected_candidates.sort(
            key=lambda item: (
                str(item["protected_split"]),
                str(item["split_group_id"]),
                str(item["source_group_id"]),
                str(item["route"]),
                json.dumps(item, sort_keys=True),
            )
        )
        protected_guidelines.sort(key=lambda item: str(item["guideline_id"]))
        protected_cases.sort(key=lambda item: str(item["case_id"]))
        _validate_stage_three_identities(
            candidates=[*candidates, *protected_candidates],
            guidelines=[*guidelines, *protected_guidelines],
            trusted_intents=trusted_intents,
            trusted_cases=[*trusted_cases, *protected_cases],
        )
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
        for name, rows in (
            ("protected_feedback_evidence.jsonl", protected_evidence),
            ("protected_candidate_guidelines.jsonl", protected_candidates),
            ("protected_evaluation_guidelines.jsonl", protected_guidelines),
            ("protected_trusted_cases.jsonl", protected_cases),
        ):
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    name,
                ),
                rows,
            )
        return {
            "feedback_evidence": len(evidence),
            "candidate_guidelines": len(candidates),
            "evaluation_guidelines": len(guidelines),
            "trusted_cases": len(trusted_cases),
        }

    def _extract_feedback_evidence(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract evidence from only the caller-provided visibility unit."""
        evidence: List[Dict[str, Any]] = []
        for batch in _batches(rows, self.config.batch_size):
            evidence.extend(
                self._call_rubric_provider(
                    PipelineStage.RUBRIC_EXTRACTION,
                    EVIDENCE_EXTRACTION_PROMPT,
                    {
                        "records": [
                            _feedback_provider_record(row)
                            for row in batch
                        ]
                    },
                    partial(
                        _normalize_feedback_evidence_response,
                        batch=batch,
                        rubric_provider=self._provider_identities["rubric"]["provider"],
                        rubric_model=self._provider_identities["rubric"]["model"],
                    ),
                )
            )
        return sorted(evidence, key=lambda item: str(item["record_id"]))

    def _synthesize_guidelines(
        self,
        evidence: Sequence[Mapping[str, Any]],
        normalized_by_id: Mapping[str, Mapping[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Synthesize guidelines without crossing the supplied evidence boundary."""
        evidence_by_route: Dict[str, List[Dict[str, Any]]] = {}
        for item in evidence:
            evidence_by_route.setdefault(str(item["route"]), []).append(dict(item))
        candidates: List[Dict[str, Any]] = []
        guidelines: List[Dict[str, Any]] = []
        for route in sorted(evidence_by_route):
            route_evidence = sorted(evidence_by_route[route], key=lambda item: str(item["record_id"]))
            source_records = [normalized_by_id[str(item["record_id"])] for item in route_evidence]
            source_alias_by_id = {
                str(item["record_id"]): f"source-{index:03d}"
                for index, item in enumerate(route_evidence, start=1)
            }
            source_id_by_alias = {
                alias: record_id for record_id, alias in source_alias_by_id.items()
            }
            route_candidates, route_guidelines = self._call_rubric_provider(
                PipelineStage.RUBRIC_EXTRACTION,
                GUIDELINE_SYNTHESIS_PROMPT,
                {
                    "route": route,
                    "evidence": [
                        {
                            **item,
                            "record_id": source_alias_by_id[str(item["record_id"])],
                        }
                        for item in route_evidence
                    ],
                    "examples": [
                        {
                            **_guideline_provider_example(row),
                            "record_id": source_alias_by_id[str(row["record_id"])],
                        }
                        for row in source_records
                    ],
                },
                partial(
                    _normalize_aliased_guideline_response,
                    source_id_by_alias=source_id_by_alias,
                    route=route,
                    evidence=route_evidence,
                    rubric_provider=self._provider_identities["rubric"]["provider"],
                    rubric_model=self._provider_identities["rubric"]["model"],
                    identity_profile="current_v2",
                ),
            )
            candidates.extend(route_candidates)
            guidelines.extend(route_guidelines)
        candidates.sort(
            key=lambda item: (
                str(item["route"]),
                str(item["intent_label"]),
                json.dumps(item, sort_keys=True),
            )
        )
        guidelines.sort(key=lambda item: str(item["guideline_id"]))
        return candidates, guidelines

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
            snapshot_authority = resolve_local_authority_file(
                snapshot,
                self.layout.tenants_root,
                access="read",
            )
            if snapshot_authority.data is None:
                raise ValueError("parent snapshot authority bytes are missing")
            expected_inventory = resolve_local_authority_file(
                inventory_path,
                self.layout.tenants_root,
                access="read_optional",
            )
            resolve_local_authority_file(
                inventory_path,
                self.layout.tenants_root,
                access="write",
                write_data=snapshot_authority.data,
                expected_write_data=expected_inventory.data,
                check_expected_write_data=True,
            )
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
        parent_rows = _load_jsonl(self.layout.parent_snapshot / "parent_intent_inventory.jsonl")
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
        snapshot = self.layout.parent_snapshot / "parent_intent_matches.jsonl"
        if not snapshot.is_file():
            return {match.cluster_id for match in matches}
        previous = {
            match.cluster_id: match for match in (_intent_match(row) for row in _load_jsonl(snapshot))
        }
        return {
            match.cluster_id
            for match in matches
            if match.cluster_id not in previous
            or previous[match.cluster_id].status != match.status
            or previous[match.cluster_id].matched_intent_id != match.matched_intent_id
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
        match_texts = build_episode_guideline_candidate_texts(
            clusters,
            records,
            trusted,
        )
        vectors = None
        if self.embedding_provider is not None:
            embedding_keys = list(match_texts)
            embeddings = validate_embedding_vectors(
                self._call_embedding_provider(
                    PipelineStage.COVERAGE_DECISIONS, [match_texts[key] for key in embedding_keys]
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
        episode_candidates = build_episode_guideline_candidate_rows(
            clusters,
            records,
            trusted,
            vectors=vectors,
            cluster_top_k=GUIDELINE_CANDIDATE_CLUSTER_TOP_K,
            episode_top_k=GUIDELINE_CANDIDATE_EPISODE_TOP_K,
            max_candidates=GUIDELINE_CANDIDATE_MAX_PER_EPISODE,
            exhaustive_route_limit=GUIDELINE_CANDIDATE_EXHAUSTIVE_ROUTE_LIMIT,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "intent_matches.jsonl",
            ),
            [match_to_dict(match) for match in matches],
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "episode_guideline_candidates.jsonl",
            ),
            episode_candidates,
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
        self.layout._write_authority_jsonl(
            self.layout.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "review_queue/labeling_queue.jsonl",
            ),
            labeling_queue,
        )
        statuses = Counter(match.status for match in matches)
        return {
            "matched_clusters": statuses["matched_trusted_intent"],
            "needs_more_feedback_clusters": statuses["needs_more_trusted_examples"],
            "missing_label_clusters": statuses["missing_or_weak_labels"],
            "labeling_queue_clusters": len({row["cluster_id"] for row in labeling_queue}),
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
        guideline_by_id = {row["guideline_id"]: row for row in evaluation_guidelines}
        match_by_cluster = {match.cluster_id: match for match in matches}
        if bool(
            getattr(
                self.rubric_provider,
                "supports_episode_guideline_applicability",
                False,
            )
        ):
            return self._infer_episode_labels(
                intent_rows=intent_rows,
                normalized=normalized,
                raw_rows=raw_rows,
                evaluation_guidelines=evaluation_guidelines,
                clusters=clusters,
                matches=matches,
            )
        matched = [
            cluster
            for cluster in clusters
            if match_by_cluster[cluster.cluster_id].status == "matched_trusted_intent"
        ]
        dependency_by_cluster = {
            cluster.cluster_id: _stage_six_dependency(
                cluster=cluster,
                match=match_by_cluster[cluster.cluster_id],
                guideline=guideline_by_id[str(match_by_cluster[cluster.cluster_id].matched_intent_id)],
                intent_rows=row_by_id,
                trusted_rows=normalized_by_id,
                provider=self._provider_settings["rubric"],
            )
            for cluster in matched
        }
        dependency_rows = [
            {
                "cluster_id": cluster_id,
                "dependency": dependency_by_cluster[cluster_id],
            }
            for cluster_id in sorted(dependency_by_cluster)
        ]
        cluster_rubrics: List[Dict[str, Any]] = []
        held_outputs: List[Dict[str, Any]] = []
        if (
            self.lineage.get("clustering_mode") == "keep"
            and (self.layout.parent_snapshot / "parent_inferred_cluster_rubrics.jsonl").is_file()
            and (self.layout.parent_snapshot / "parent_inference_dependencies.jsonl").is_file()
        ):
            parent_rubrics = _unique_rows_by_key(
                _load_jsonl(self.layout.parent_snapshot / "parent_inferred_cluster_rubrics.jsonl"),
                key="cluster_id",
                source="parent inferred rubrics",
            )
            parent_dependencies = _unique_rows_by_key(
                _load_jsonl(self.layout.parent_snapshot / "parent_inference_dependencies.jsonl"),
                key="cluster_id",
                source="parent inference dependencies",
            )
            for cluster in matched:
                cluster_id = cluster.cluster_id
                rubric = parent_rubrics.get(cluster_id)
                prior = parent_dependencies.get(cluster_id)
                if (
                    rubric is None
                    or prior is None
                    or not isinstance(prior.get("dependency"), Mapping)
                    or not dependency_matches(
                        prior["dependency"],
                        dependency_by_cluster[cluster_id],
                    )
                    or rubric.get("dependency_sha256")
                    != dependency_by_cluster[cluster_id]["dependency_sha256"]
                    or not has_scoreable_rubric(rubric)
                ):
                    continue
                cluster_rubrics.append(dict(rubric))
        reused_cluster_ids = {str(rubric["cluster_id"]) for rubric in cluster_rubrics}
        changed_matched = [cluster for cluster in matched if cluster.cluster_id not in reused_cluster_ids]
        for batch in _batches(changed_matched, self.config.batch_size):
            generated_rubrics = self._call_rubric_provider(
                PipelineStage.LABEL_INFERENCE,
                INFERENCE_PROMPT,
                {
                    "mode": "legacy_cluster_rubric",
                    "clusters": [
                        {
                            "cluster_id": cluster.cluster_id,
                            "route": cluster.route,
                            "representative_requests": [
                                row_by_id[record_id]["canonical_intent_text"]
                                for record_id in cluster.representative_ids
                            ],
                            "trusted_requests": [
                                _canonical_intent_text(
                                    normalized_by_id[record_id]
                                )
                                for record_id in guideline_by_id[
                                    str(match_by_cluster[cluster.cluster_id].matched_intent_id)
                                ]["source_record_ids"]
                            ],
                            "trusted_evaluation_guideline": guideline_by_id[
                                str(match_by_cluster[cluster.cluster_id].matched_intent_id)
                            ],
                            "match_score": match_by_cluster[cluster.cluster_id].score,
                        }
                        for cluster in batch
                    ]
                },
                partial(
                    _normalize_inferred_rubric_response,
                    batch=batch,
                    rubric_provider=self._provider_identities["rubric"]["provider"],
                    rubric_model=self._provider_identities["rubric"]["model"],
                ),
            )
            for rubric in generated_rubrics:
                cluster_id = str(rubric["cluster_id"])
                rubric["dependency_sha256"] = dependency_by_cluster[cluster_id]["dependency_sha256"]
                if has_scoreable_rubric(rubric):
                    cluster_rubrics.append(rubric)
                else:
                    held_outputs.append(
                        {
                            "cluster_id": cluster_id,
                            "hold_reason": "unscoreable_rubric",
                            "dependency_sha256": dependency_by_cluster[cluster_id]["dependency_sha256"],
                            "rubric": rubric,
                        }
                    )

        labels, inferred_cases = _inferred_cases(
            clusters,
            matches,
            intent_rows,
            raw_rows,
            cluster_rubrics,
            self.config,
        )
        trusted_record_ids = {str(row["record_id"]) for row in normalized}
        labels = [row for row in labels if str(row["record_id"]) not in trusted_record_ids]
        inferred_cases = [
            row
            for row in inferred_cases
            if str(row["case_id"]).removeprefix("inferred-") not in trusted_record_ids
        ]
        missing = _missing_clusters(clusters, matches, row_by_id)
        cluster_by_id = {cluster.cluster_id: cluster for cluster in clusters}
        for held in held_outputs:
            cluster = cluster_by_id[str(held["cluster_id"])]
            missing.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "route": cluster.route,
                    "size": cluster.size,
                    "status": "held_unscoreable_rubric",
                    "reason": "inferred rubric contains no scoreable rule",
                    "best_candidate_intent_id": match_by_cluster[cluster.cluster_id].matched_intent_id,
                    "match_score": match_by_cluster[cluster.cluster_id].score,
                    "representative_examples": [
                        {
                            "record_id": record_id,
                            "user_input": row_by_id[record_id]["user_input"],
                        }
                        for record_id in cluster.representative_ids
                    ],
                }
            )
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
                "inference_dependencies.jsonl",
            ),
            dependency_rows,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "held_inference_outputs.jsonl",
            ),
            held_outputs,
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

    def _infer_episode_labels(
        self,
        *,
        intent_rows: Sequence[Mapping[str, Any]],
        normalized: Sequence[Mapping[str, Any]],
        raw_rows: Sequence[Mapping[str, Any]],
        evaluation_guidelines: Sequence[Mapping[str, Any]],
        clusters: Sequence[IntentCluster],
        matches: Sequence[IntentMatch],
    ) -> Dict[str, int]:
        """Attach zero, one, or many trusted guidelines to each episode."""
        evaluation_guidelines = _attach_applicability_contracts(
            evaluation_guidelines,
            self._injected_applicability_contracts,
        )
        row_by_id = {str(row["record_id"]): row for row in intent_rows}
        raw_by_id = {str(row["record_id"]): row for row in raw_rows}
        normalized_by_id = {str(row["record_id"]): row for row in normalized}
        guideline_by_id = {
            str(row["guideline_id"]): row for row in evaluation_guidelines
        }
        guideline_id_by_intent_label = {
            str(row["intent_label"]): str(row["guideline_id"])
            for row in evaluation_guidelines
        }
        missing_review_labels = sorted(
            self._applicability_semantic_review_intent_labels
            - set(guideline_id_by_intent_label)
        )
        if missing_review_labels:
            raise ValueError(
                "Semantic-review intent labels are absent from the guideline "
                f"library: {missing_review_labels}"
            )
        semantic_review_guideline_ids = {
            guideline_id_by_intent_label[intent_label]
            for intent_label in self._applicability_semantic_review_intent_labels
        }
        match_by_cluster = {match.cluster_id: match for match in matches}
        trusted_record_ids = set(normalized_by_id)
        eligible_record_ids = _eligible_episode_record_ids(
            clusters,
            trusted_record_ids,
        )

        candidate_path = self.layout.artifact_path(
            PipelineStage.COVERAGE_DECISIONS,
            "episode_guideline_candidates.jsonl",
        )
        if candidate_path.is_file():
            candidate_rows = _load_jsonl(candidate_path)
        else:
            candidate_rows = _legacy_episode_candidate_rows(
                clusters,
                matches,
                evaluation_guidelines,
            )
        candidate_by_record = _unique_rows_by_key(
            [
                row
                for row in candidate_rows
                if str(row.get("record_id")) in eligible_record_ids
            ],
            key="record_id",
            source="episode guideline candidates",
        )
        missing_candidates = sorted(eligible_record_ids - set(candidate_by_record))
        if missing_candidates:
            raise ValueError(
                "Episode guideline candidates omitted record(s): "
                + ", ".join(missing_candidates)
            )

        groups, group_by_record, deterministic_rows = _build_applicability_groups(
            eligible_record_ids=eligible_record_ids,
            candidate_by_record=candidate_by_record,
            raw_by_id=raw_by_id,
            guideline_by_id=guideline_by_id,
            unknown_policy=self._applicability_unknown_policy,
            semantic_review_guideline_ids=semantic_review_guideline_ids,
            use_applicability_contracts=(
                self._injected_applicability_contracts is not None
            ),
            use_deterministic_candidate_filters=False,
        )
        decisions_by_id: Dict[str, Dict[str, Any]] = {
            str(row["decision_id"]): row for row in deterministic_rows
        }
        for batch in _applicability_batches(groups):
            generated = self._call_rubric_provider(
                PipelineStage.LABEL_INFERENCE,
                INFERENCE_PROMPT,
                _applicability_provider_payload(batch, guideline_by_id),
                partial(
                    _normalize_applicability_response,
                    decision_groups=batch,
                ),
            )
            group_by_decision_id = {
                str(group["decision_id"]): group for group in batch
            }
            for decision in generated:
                decision_id = str(decision["decision_id"])
                decisions_by_id[decision_id] = _merge_applicability_decision(
                    group_by_decision_id[decision_id],
                    decision,
                )

        applicability_rows: List[Dict[str, Any]] = []
        episode_rubrics: List[Dict[str, Any]] = []
        held_outputs: List[Dict[str, Any]] = []
        selected_ids_by_record: Dict[str, tuple[str, ...]] = {}
        decision_by_record: Dict[str, Dict[str, Any]] = {}
        for record_id in sorted(eligible_record_ids):
            group = group_by_record[record_id]
            decision = dict(decisions_by_id[str(group["decision_id"])])
            selected_ids = tuple(
                str(item) for item in decision["applicable_guideline_ids"]
            )
            selected_ids_by_record[record_id] = selected_ids
            decision_by_record[record_id] = decision
            applicability_rows.append(
                _record_applicability_row(
                    record_id=record_id,
                    group=group,
                    decision=decision,
                )
            )
            if not selected_ids:
                held_outputs.append(
                    {
                        "record_id": record_id,
                        "cluster_id": str(group["cluster_id_by_record"][record_id]),
                        "hold_reason": "no_applicable_guideline",
                        "decision_id": decision["decision_id"],
                        "reason": decision["reason"],
                    }
                )
                continue
            selected_guidelines = [guideline_by_id[item] for item in selected_ids]
            rubric = _rubric_from_guidelines(
                record_id,
                selected_guidelines,
                self._provider_identities["rubric"]["provider"],
                self._provider_identities["rubric"]["model"],
            )
            rubric["label_source"] = INFERRED_FROM_TRUSTED_FEEDBACK
            rubric["review_status"] = "review_required"
            rubric["confidence"] = round(
                min(float(rubric["confidence"]), float(decision["confidence"])),
                4,
            )
            rubric["cluster_id"] = str(group["cluster_id_by_record"][record_id])
            rubric["applicability_decision_id"] = decision["decision_id"]
            if has_scoreable_rubric(rubric):
                episode_rubrics.append(rubric)
            else:
                held_outputs.append(
                    {
                        "record_id": record_id,
                        "cluster_id": rubric["cluster_id"],
                        "hold_reason": "unscoreable_episode_rubric",
                        "decision_id": decision["decision_id"],
                        "rubric": rubric,
                    }
                )

        rubric_by_record = {
            str(row["record_id"]): row for row in episode_rubrics
        }
        labels, inferred_cases = _inferred_episode_cases(
            clusters=clusters,
            matches=matches,
            intent_rows=intent_rows,
            raw_rows=raw_rows,
            rubric_by_record=rubric_by_record,
            decision_by_record=decision_by_record,
            config=self.config,
        )

        cluster_rubrics: List[Dict[str, Any]] = []
        dependency_rows: List[Dict[str, Any]] = []
        cluster_support, missing = _episode_cluster_support(
            clusters=clusters,
            matches=matches,
            row_by_id=row_by_id,
            eligible_record_ids=eligible_record_ids,
            selected_ids_by_record=selected_ids_by_record,
            rubric_by_record=rubric_by_record,
        )
        for cluster in clusters:
            match = match_by_cluster[cluster.cluster_id]
            record_ids = [
                record_id
                for record_id in cluster.record_ids
                if record_id in eligible_record_ids
            ]
            if not record_ids:
                continue
            selected_sets = {
                selected_ids_by_record[record_id] for record_id in record_ids
            }
            homogeneous = (
                bool(record_ids)
                and len(selected_sets) == 1
                and next(iter(selected_sets))
                and all(record_id in rubric_by_record for record_id in record_ids)
            )
            if not homogeneous:
                held_outputs.append(
                    _episode_gate_cluster_hold(
                        cluster,
                        record_ids,
                        selected_ids_by_record,
                        rubric_by_record,
                    )
                )
                continue
            selected_ids = next(iter(selected_sets))
            selected_guidelines = [guideline_by_id[item] for item in selected_ids]
            cluster_rubric = _rubric_from_guidelines(
                cluster.cluster_id,
                selected_guidelines,
                self._provider_identities["rubric"]["provider"],
                self._provider_identities["rubric"]["model"],
            )
            cluster_rubric["cluster_id"] = cluster_rubric.pop("record_id")
            cluster_rubric["label_source"] = INFERRED_FROM_TRUSTED_FEEDBACK
            cluster_rubric["review_status"] = "review_required"
            cluster_rubric["confidence"] = round(
                min(
                    float(cluster_rubric["confidence"]),
                    *(float(decision_by_record[item]["confidence"]) for item in record_ids),
                ),
                4,
            )
            guideline_bundle = _guideline_dependency_bundle(selected_guidelines)
            dependency = _stage_six_dependency(
                cluster=cluster,
                match=match,
                guideline=guideline_bundle,
                intent_rows=row_by_id,
                trusted_rows=normalized_by_id,
                provider=self._provider_settings["rubric"],
            )
            cluster_rubric["dependency_sha256"] = dependency["dependency_sha256"]
            cluster_rubrics.append(cluster_rubric)
            dependency_rows.append(
                {"cluster_id": cluster.cluster_id, "dependency": dependency}
            )

        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "episode_guideline_applicability.jsonl",
            ),
            applicability_rows,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_unlabeled_episode_rubrics.jsonl",
            ),
            episode_rubrics,
        )
        for name, rows in (
            ("cluster_feedback_support.jsonl", cluster_support),
            ("inferred_unlabeled_cluster_rubrics.jsonl", cluster_rubrics),
            ("inference_dependencies.jsonl", dependency_rows),
            ("held_inference_outputs.jsonl", held_outputs),
            ("inferred_unlabeled_labels.jsonl", labels),
            ("missing_labeled_feedback_clusters.jsonl", missing),
            ("inferred_cases.jsonl", inferred_cases),
        ):
            write_jsonl(
                self.layout.artifact_path(PipelineStage.LABEL_INFERENCE, name),
                rows,
            )
        _write_missing_report(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "missing_labeled_feedback_report.md",
            ),
            missing,
        )
        return {
            "inferred_cases": len(inferred_cases),
            "review_clusters": len(missing),
        }

    def _build_splits(self) -> Dict[str, int]:
        state = self.layout.load_state()
        authority = self._current_review_authority(
            state,
            compare_current_dependencies=True,
        )
        finalization = self._current_review_finalization(authority)
        if finalization is None:
            raise ReviewIntegrityError("Stage 8 requires an explicit current review finalization")
        trusted = [
            *_load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "trusted_cases.jsonl",
                )
            ),
            *_load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "protected_trusted_cases.jsonl",
                )
            ),
        ]
        review_items = {str(item["case_id"]): item for item in authority["review_items"]}
        approved_decisions = {
            str(item["case_id"]): str(item["decision_id"])
            for item in finalization["items"]
            if item["status"] == "approved"
        }
        approved = [
            _approved_case_for_release(
                review_items[case_id]["case"],
                asset_id=self.config.asset_id,
                decision_id=decision_id,
            )
            for case_id, decision_id in sorted(approved_decisions.items())
        ]
        families = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "duplicate_families.jsonl",
            )
        )
        payloads = _review_split_payloads(
            trusted=trusted,
            approved=approved,
            held=authority["held_cases"],
            families=families,
            asset_id=self.config.asset_id,
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
        self.layout._write_authority_json(
            self.layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "review_snapshot.json",
            ),
            finalization,
        )
        input_manifest = _local_authority_json(
            self.layout,
            self.layout.artifact_path(
                PipelineStage.RAW_INPUTS,
                "input_manifest.json",
            ),
        )
        guideline_path = self.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
        guideline_count = len(_load_jsonl(guideline_path)) if guideline_path.is_file() else 0
        held_case_ids = {str(row["case_id"]) for row in finalization["held"]}
        review_fingerprints = {
            "trusted": sorted(
                (
                    {
                        "case_id": str(case["case_id"]),
                        "fingerprint": case_content_fingerprint(case),
                    }
                    for case in trusted
                    if str(case["case_id"]) not in held_case_ids
                ),
                key=lambda row: (row["case_id"], row["fingerprint"]),
            ),
            **{
                status: [
                    {
                        "case_id": str(item["case_id"]),
                        "fingerprint": str(item["fingerprint"]),
                    }
                    for item in finalization["items"]
                    if item["status"] == status
                ]
                for status in ("approved", "pending", "rejected")
            },
            "held": [dict(item) for item in finalization["held"]],
        }
        if {
            status: len(rows) for status, rows in review_fingerprints.items()
        } != finalization["counts"]:
            raise ReviewIntegrityError(
                "review fingerprint inventory differs from finalization counts"
            )
        manifest = {
            "asset_id": self.config.asset_id,
            "tenant_id": self.config.tenant_id,
            "providers": {
                "rubric_provider": self._provider_identities["rubric"]["provider"],
                "rubric_model": self._provider_identities["rubric"]["model"],
                "embedding_provider": self._provider_identities["embedding"]["provider"],
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
                    "active_from_trusted_evidence" if guideline_path.is_file() else "legacy_compatibility"
                ),
                "calibration_status": ("uncalibrated" if guideline_path.is_file() else "unavailable"),
            },
            "clustering": {
                "algorithm": "deterministic_cosine_fixed_count_v1",
                "requested_clusters": self.config.cluster_count,
            },
            "coverage": {
                "match_threshold": self.config.match_threshold,
                "min_trusted_examples": self.config.min_trusted_examples,
                "min_trusted_groups": self.config.min_trusted_groups,
                "max_unlabeled_to_trusted_ratio": (self.config.max_unlabeled_to_trusted_ratio),
                "labeling_queue": {
                    "statuses": [
                        "needs_more_trusted_examples",
                        "missing_or_weak_labels",
                    ],
                    "sample_ratio": LABELING_QUEUE_SAMPLE_RATIO,
                    "minimum_per_cluster": 1,
                    "maximum_per_cluster": LABELING_QUEUE_MAX_PER_CLUSTER,
                    "selection": "deterministic_centroid_nearest",
                    "acquisition": dict(LABELING_QUEUE_ACQUISITION),
                },
            },
            "synthetic_coverage": {
                "enabled": self.config.synthetic_coverage_enabled,
                "cases_per_cluster": self.config.synthetic_cases_per_cluster,
            },
            "regression_gate": {
                "source": "trusted_feedback",
                "fraction": DEFAULT_REGRESSION_FRACTION,
                "selection": "deterministic_early_connected_group_hash",
                "seed": self.config.split_seed,
            },
            "source_hashes": {name: details["sha256"] for name, details in input_manifest["inputs"].items()},
            "published_datasets": {
                "directory": self.layout.published_datasets.relative_to(self.layout.tenant_root).as_posix(),
                "files": {},
            },
            "split_counts": {name: len(rows) for name, rows in payloads.items()},
            "review_policy": {
                "evaluation_guidelines": "active_from_trusted_evidence",
                "guideline_calibration": "uncalibrated",
                "derived_cases": "approved_only",
                "coverage_labeling_queue": "human_label_required",
                "trusted_split_assignment": "before_guideline_authoring",
                "exact_duplicate_conflicts": "triage_hold",
            },
            "review": {
                "review_set_fingerprint": finalization["review_set_fingerprint"],
                "finalization_id": finalization["finalization_id"],
                "stage7_receipt_sha256": finalization["stage7_receipt_sha256"],
                "counts": dict(finalization["counts"]),
                "fingerprints": review_fingerprints,
            },
        }
        if self.lineage:
            manifest["lineage"] = dict(self.lineage)
        self._stage_eight_manifest = manifest
        return {
            "dataset_cases": sum(
                len(payloads[name])
                for name in (
                    "train",
                    "validation",
                    "test",
                    "regression_trusted",
                )
            ),
            "train_cases": len(payloads["train"]),
            "validation_cases": len(payloads["validation"]),
            "test_cases": len(payloads["test"]),
            "regression_trusted_cases": len(payloads["regression_trusted"]),
            "triage_hold_cases": len(payloads["triage_hold"]),
        }

    def _generate_synthetic_coverage(self) -> Dict[str, int]:
        if not self.config.synthetic_coverage_enabled:
            for name in (
                "synthetic_candidates.jsonl",
                "rejected_synthetic.jsonl",
                "synthetic_filter_issues.jsonl",
                "synthetic_cases.jsonl",
                "synthetic_dependencies.jsonl",
            ):
                write_jsonl(
                    self.layout.artifact_path(
                        PipelineStage.SYNTHETIC_COVERAGE,
                        name,
                    ),
                    [],
                )
            self._write_review_artifacts()
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
        matched = [cluster for cluster in clusters if cluster.cluster_id in rubric_by_cluster]
        inference_dependencies = _unique_rows_by_key(
            _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.LABEL_INFERENCE,
                    "inference_dependencies.jsonl",
                )
            ),
            key="cluster_id",
            source="inference dependencies",
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
        generation_set = {
            cluster.cluster_id: str(
                inference_dependencies[cluster.cluster_id]["dependency"]["dependency_sha256"]
            )
            for cluster in matched
        }
        parent_synthetic: List[Dict[str, Any]] = []
        parent_dependencies: Dict[str, Dict[str, Any]] = {}
        if self.lineage.get("clustering_mode") == "keep":
            parent_cases_path = self.layout.parent_snapshot / "parent_synthetic_cases.jsonl"
            parent_dependencies_path = self.layout.parent_snapshot / "parent_synthetic_dependencies.jsonl"
            if parent_cases_path.is_file() and parent_dependencies_path.is_file():
                parent_synthetic = _load_jsonl(parent_cases_path)
                parent_dependencies = _unique_rows_by_key(
                    _load_jsonl(parent_dependencies_path),
                    key="cluster_id",
                    source="parent synthetic dependencies",
                )
        preliminary_dependencies = {
            cluster.cluster_id: _stage_seven_dependency(
                cluster=cluster,
                rubric=rubric_by_cluster[cluster.cluster_id],
                stage_six_dependency=inference_dependencies[cluster.cluster_id]["dependency"],
                comparison_cases=[
                    *trusted,
                    *inferred,
                    *[
                        case
                        for case in parent_synthetic
                        if str((case.get("metadata") or {}).get("source_cluster")) != cluster.cluster_id
                    ],
                ],
                provider=self._provider_settings["rubric"],
                config=self.config,
                generation_set=generation_set,
            )
            for cluster in matched
        }
        parent_cases_by_cluster: Dict[str, List[Dict[str, Any]]] = {}
        reused_cluster_ids: set[str] = set()
        for cluster in matched:
            prior = parent_dependencies.get(cluster.cluster_id)
            if (
                prior is None
                or not isinstance(prior.get("dependency"), Mapping)
                or not dependency_matches(
                    prior["dependency"],
                    preliminary_dependencies[cluster.cluster_id],
                )
            ):
                continue
            cluster_cases = [
                _case_for_asset(case, self.config.asset_id)
                for case in parent_synthetic
                if str((case.get("metadata") or {}).get("source_cluster")) == cluster.cluster_id
            ]
            if not cluster_cases:
                continue
            parent_cases_by_cluster[cluster.cluster_id] = cluster_cases
            reused_cluster_ids.add(cluster.cluster_id)
        generated_by_cluster: Dict[str, List[Dict[str, Any]]] = {}
        pending_generation = [
            cluster for cluster in matched if cluster.cluster_id not in reused_cluster_ids
        ]
        while True:
            for batch in _batches(pending_generation, self.config.batch_size):
                generated = self._call_rubric_provider(
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
                                "case_count": self.config.synthetic_cases_per_cluster,
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
                for case in generated:
                    cluster_id = str((case.get("metadata") or {}).get("source_cluster"))
                    generated_by_cluster.setdefault(cluster_id, []).append(case)

            candidates = [
                case
                for cluster in matched
                if cluster.cluster_id not in reused_cluster_ids
                for case in generated_by_cluster[cluster.cluster_id]
            ]
            ordered_synthetic = [
                case
                for cluster in matched
                for case in (
                    parent_cases_by_cluster[cluster.cluster_id]
                    if cluster.cluster_id in reused_cluster_ids
                    else generated_by_cluster[cluster.cluster_id]
                )
            ]
            filtered = filter_synthetic_cases(
                ordered_synthetic,
                existing_cases=trusted + inferred,
            )
            synthetic_cases = filtered.accepted
            final_dependencies = {
                cluster.cluster_id: _stage_seven_dependency(
                    cluster=cluster,
                    rubric=rubric_by_cluster[cluster.cluster_id],
                    stage_six_dependency=(
                        inference_dependencies[cluster.cluster_id]["dependency"]
                    ),
                    comparison_cases=[
                        *trusted,
                        *inferred,
                        *[
                            case
                            for case in synthetic_cases
                            if str(
                                (case.get("metadata") or {}).get("source_cluster")
                            )
                            != cluster.cluster_id
                        ],
                    ],
                    provider=self._provider_settings["rubric"],
                    config=self.config,
                    generation_set=generation_set,
                )
                for cluster in [
                    item for item in clusters if item.cluster_id in rubric_by_cluster
                ]
            }
            accepted_identities = {
                (
                    str((case.get("metadata") or {}).get("source_cluster")),
                    str(case.get("case_id")),
                )
                for case in synthetic_cases
            }
            invalidated = []
            for cluster in matched:
                if cluster.cluster_id not in reused_cluster_ids:
                    continue
                prior_cases_survived = all(
                    (cluster.cluster_id, str(case.get("case_id")))
                    in accepted_identities
                    for case in parent_cases_by_cluster[cluster.cluster_id]
                )
                prior_dependency = parent_dependencies[cluster.cluster_id][
                    "dependency"
                ]
                if not prior_cases_survived or not dependency_matches(
                    prior_dependency,
                    final_dependencies[cluster.cluster_id],
                ):
                    invalidated.append(cluster)
            if not invalidated:
                break
            reused_cluster_ids.difference_update(
                cluster.cluster_id for cluster in invalidated
            )
            pending_generation = invalidated
        for case in synthetic_cases:
            metadata = dict(case.get("metadata") or {})
            cluster_id = str(metadata.get("source_cluster"))
            metadata["dependency_sha256"] = final_dependencies[cluster_id]["dependency_sha256"]
            case["metadata"] = metadata
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
            synthetic_cases,
        )
        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_dependencies.jsonl",
            ),
            [
                {
                    "cluster_id": cluster_id,
                    "dependency": final_dependencies[cluster_id],
                }
                for cluster_id in sorted(final_dependencies)
            ],
        )
        self._write_review_artifacts()
        return {
            "synthetic_cases": len(synthetic_cases),
            "rejected_synthetic_cases": len(filtered.rejected),
        }

    def _write_review_artifacts(self) -> None:
        """Build the exact Stage 7 queue, duplicate families, and triage holds."""
        stage = PipelineStage.SYNTHETIC_COVERAGE
        trusted_cases = [
            *_load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "trusted_cases.jsonl",
                )
            ),
            *_load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "protected_trusted_cases.jsonl",
                )
            ),
        ]
        inferred_cases = _load_jsonl(
            self.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_cases.jsonl",
            )
        )
        synthetic_cases = _load_jsonl(self.layout.artifact_path(stage, "synthetic_cases.jsonl"))
        episode_applicability_path = self.layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "episode_guideline_applicability.jsonl",
        )
        if episode_applicability_path.is_file():
            inference_dependencies_by_case = _dependency_rows_by_case(
                self._write_inferred_review_dependencies(inferred_cases),
                source="inferred review dependencies",
            )
            inference_dependencies_by_cluster: Dict[str, Dict[str, Any]] = {}
        else:
            write_jsonl(
                self.layout.artifact_path(
                    PipelineStage.SYNTHETIC_COVERAGE,
                    "inferred_review_dependencies.jsonl",
                ),
                [],
            )
            inference_dependencies_by_case = {}
            inference_dependencies_by_cluster = _dependency_rows_by_cluster(
                _load_jsonl(
                    self.layout.artifact_path(
                        PipelineStage.LABEL_INFERENCE,
                        "inference_dependencies.jsonl",
                    )
                ),
                source="inference dependencies",
            )
        synthetic_dependencies = _dependency_rows_by_cluster(
            _load_jsonl(self.layout.artifact_path(stage, "synthetic_dependencies.jsonl")),
            source="synthetic dependencies",
        )
        timestamp = utc_now()
        derived: List[Dict[str, Any]] = []
        review_items_by_case: Dict[str, Dict[str, Any]] = {}
        scoreable_by_case: Dict[str, bool] = {}
        for case in [*inferred_cases, *synthetic_cases]:
            review_case = _case_for_review(case)
            metadata = dict(review_case["metadata"])
            cluster_id = str(metadata.get("source_cluster") or "")
            trust_tier = str(metadata.get("trust_tier") or "")
            if trust_tier == INFERRED_FROM_TRUSTED_FEEDBACK:
                dependency = inference_dependencies_by_case.get(
                    str(review_case["case_id"])
                ) or inference_dependencies_by_cluster.get(cluster_id)
            elif trust_tier == SYNTHETIC_FROM_TRUSTED_RUBRIC:
                dependency = synthetic_dependencies.get(cluster_id)
            else:
                dependency = None
            if dependency is None:
                raise ReviewIntegrityError(
                    f"derived case {review_case['case_id']} lacks dependency authority"
                )
            item = build_review_item(
                case=review_case,
                dependency=dependency,
                source_provenance=_review_source_provenance(
                    review_case,
                    dependency,
                ),
                reviewer="fapo_pipeline",
                timestamp=timestamp,
            )
            case_id = str(review_case["case_id"])
            if case_id in review_items_by_case:
                raise ValueError(f"duplicate derived review case_id {case_id!r}")
            derived.append(review_case)
            review_items_by_case[case_id] = item
            scoreable_by_case[case_id] = _has_scoreable_expected(review_case["expected"])

        families = build_duplicate_families([*trusted_cases, *derived])
        held: Dict[str, Dict[str, Any]] = {}
        cases_by_id = {str(case["case_id"]): case for case in [*trusted_cases, *derived]}
        if len(cases_by_id) != len(trusted_cases) + len(derived):
            raise ValueError("review family case_ids must be globally unique")

        def hold(case_id: str, reason: str, family_id: str | None) -> None:
            case = cases_by_id[case_id]
            review_item = review_items_by_case.get(case_id)
            fingerprint = (
                str(review_item["fingerprint"]) if review_item is not None else case_content_fingerprint(case)
            )
            row = {
                "case_id": case_id,
                "fingerprint": fingerprint,
                "case_content_sha256": case_content_fingerprint(case),
                "trust_tier": str(case["metadata"]["trust_tier"]),
                "status": "held",
                "reason": reason,
                "hold_reason": reason,
                "family_id": family_id,
                "case": case,
            }
            previous = held.get(case_id)
            if previous is not None and previous["reason"] != reason:
                reasons = sorted({str(previous["reason"]), reason})
                row["reason"] = "+".join(reasons)
                row["hold_reason"] = row["reason"]
            held[case_id] = row

        for family in families:
            family_id = str(family["family_id"])
            members = list(family["members"])
            if family["hold_reasons"]:
                reason = "+".join(str(item) for item in family["hold_reasons"])
                for member in members:
                    hold(str(member["case_id"]), reason, family_id)
                continue
            regression_member = any(
                member["trust_tier"] == TRUSTED_FEEDBACK and member["early_split"] == "regression"
                for member in members
            )
            if regression_member:
                for member in members:
                    if member["trust_tier"] != TRUSTED_FEEDBACK:
                        hold(
                            str(member["case_id"]),
                            "derived_attached_to_regression",
                            family_id,
                        )
        for case_id, scoreable in scoreable_by_case.items():
            if not scoreable:
                family_id = next(
                    (
                        str(family["family_id"])
                        for family in families
                        if any(str(member["case_id"]) == case_id for member in family["members"])
                    ),
                    None,
                )
                hold(case_id, "unscoreable_expected", family_id)

        queue = sorted(
            (item for case_id, item in review_items_by_case.items() if case_id not in held),
            key=lambda item: (str(item["case_id"]), str(item["fingerprint"])),
        )
        held_rows = sorted(
            held.values(),
            key=lambda row: (str(row["case_id"]), str(row["fingerprint"])),
        )
        write_jsonl(
            self.layout.artifact_path(stage, "derived_review_items.jsonl"),
            queue,
        )
        write_jsonl(
            self.layout.artifact_path(stage, "duplicate_families.jsonl"),
            families,
        )
        write_jsonl(
            self.layout.artifact_path(stage, "held_derived_cases.jsonl"),
            held_rows,
        )
        self._inherit_parent_review_decisions(queue, timestamp=timestamp)
        self._auto_approve_derived_review_items(queue, timestamp=timestamp)

    def _write_inferred_review_dependencies(
        self,
        inferred_cases: Sequence[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Bind each inferred case to its exact episode applicability decision."""
        stage = PipelineStage.LABEL_INFERENCE
        clusters = {
            cluster.cluster_id: cluster
            for cluster in (
                _intent_cluster(row)
                for row in _load_jsonl(
                    self.layout.artifact_path(
                        PipelineStage.INTENT_CLUSTERING,
                        "intent_inventory.jsonl",
                    )
                )
            )
        }
        matches = {
            match.cluster_id: match
            for match in (
                _intent_match(row)
                for row in _load_jsonl(
                    self.layout.artifact_path(
                        PipelineStage.COVERAGE_DECISIONS,
                        "intent_matches.jsonl",
                    )
                )
            )
        }
        guidelines = _unique_rows_by_key(
            _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "evaluation_guidelines.jsonl",
                )
            ),
            key="guideline_id",
            source="evaluation guidelines",
        )
        applicability = _unique_rows_by_key(
            _load_jsonl(
                self.layout.artifact_path(
                    stage,
                    "episode_guideline_applicability.jsonl",
                )
            ),
            key="record_id",
            source="episode guideline applicability",
        )
        intent_rows = _unique_rows_by_key(
            _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.PREPARED_INPUTS,
                    "intent_records.jsonl",
                )
            ),
            key="record_id",
            source="intent records",
        )
        trusted_rows = _unique_rows_by_key(
            _load_jsonl(
                self.layout.artifact_path(
                    PipelineStage.PREPARED_INPUTS,
                    "normalized_feedback.jsonl",
                )
            ),
            key="record_id",
            source="normalized feedback",
        )

        rows: List[Dict[str, Any]] = []
        seen_case_ids: set[str] = set()
        for case in inferred_cases:
            case_id = str(case.get("case_id") or "")
            metadata = case.get("metadata")
            if (
                not case_id.startswith("inferred-")
                or case_id in seen_case_ids
                or not isinstance(metadata, Mapping)
            ):
                raise ReviewIntegrityError(
                    "inferred case identity is invalid for review dependency creation"
                )
            seen_case_ids.add(case_id)
            record_id = case_id.removeprefix("inferred-")
            cluster_id = str(metadata.get("source_cluster") or "")
            cluster = clusters.get(cluster_id)
            match = matches.get(cluster_id)
            decision = applicability.get(record_id)
            if cluster is None or match is None or decision is None:
                raise ReviewIntegrityError(
                    f"inferred case {case_id} lacks episode applicability inputs"
                )
            selected_ids = decision.get("applicable_guideline_ids")
            if not isinstance(selected_ids, list) or not selected_ids:
                raise ReviewIntegrityError(
                    f"inferred case {case_id} lacks applicable guidelines"
                )
            try:
                selected_guidelines = [guidelines[str(item)] for item in selected_ids]
            except KeyError as exc:
                raise ReviewIntegrityError(
                    f"inferred case {case_id} references an unknown guideline"
                ) from exc
            guideline_bundle = _guideline_dependency_bundle(selected_guidelines)
            guideline_bundle["episode_record_id"] = record_id
            guideline_bundle["episode_applicability"] = dict(decision)
            dependency = _stage_six_dependency(
                cluster=cluster,
                match=match,
                guideline=guideline_bundle,
                intent_rows=intent_rows,
                trusted_rows=trusted_rows,
                provider=self._provider_settings["rubric"],
            )
            rows.append({"case_id": case_id, "dependency": dependency})

        write_jsonl(
            self.layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "inferred_review_dependencies.jsonl",
            ),
            rows,
        )
        return rows

    def _auto_approve_derived_review_items(
        self,
        review_items: Sequence[Mapping[str, Any]],
        *,
        timestamp: str,
    ) -> None:
        """Approve scoreable inferred and synthetic cases for publication.

        Inferred cases and opt-in synthetic cases enter this queue only after
        their respective pipeline checks. Held or unscoreable cases are absent
        and remain excluded from publication.
        """
        decisions = self.layout._read_control_log(self.layout.review_decisions_path)
        for item in review_items:
            decision, append = record_review_decision(
                item,
                decisions,
                status="approved",
                reviewer="fapo_pipeline",
                timestamp=timestamp,
                note="Automatically approved by the evaluation-asset pipeline.",
            )
            if append:
                self.layout._append_jsonl_once(
                    self.layout.review_decisions_path,
                    decision,
                    identity_fields=("decision_id",),
                )
                decisions = [*decisions, decision]

    def _inherit_parent_review_decisions(
        self,
        review_items: Sequence[Mapping[str, Any]],
        *,
        timestamp: str,
    ) -> None:
        """Inherit only byte-identical parent review identities."""
        if not self.lineage:
            return
        parent_items_path = self.layout.parent_snapshot / "parent_derived_review_items.jsonl"
        parent_decisions_path = self.layout.parent_snapshot / "parent_review_decisions.jsonl"
        if not parent_items_path.is_file() or not parent_decisions_path.is_file():
            return
        parent_items = _unique_rows_by_key(
            _load_jsonl(parent_items_path),
            key="case_id",
            source="parent review items",
        )
        parent_decisions = _load_jsonl(parent_decisions_path)
        parent_asset_id = str(self.lineage.get("parent_asset_id") or "")
        for item in review_items:
            parent_item = parent_items.get(str(item["case_id"]))
            if parent_item is None:
                continue
            inherited = inherit_review_decision(
                parent_item=parent_item,
                child_item=item,
                parent_decisions=parent_decisions,
                parent_asset_id=parent_asset_id,
                reviewer="fapo_pipeline",
                timestamp=timestamp,
            )
            if inherited is not None:
                self.layout._append_jsonl_once(
                    self.layout.review_decisions_path,
                    inherited,
                    identity_fields=("decision_id",),
                )


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
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
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
    rows = [dict(row) for row in existing if str(row[key]) not in added_keys]
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


def _case_for_review(case: Mapping[str, Any]) -> Dict[str, Any]:
    """Remove release-local fields before fingerprint-bound human review."""
    copied = dict(case)
    metadata = dict(copied.get("metadata") or {})
    for field in (
        "dataset_version",
        "decision_id",
        "generation_id",
        "release_generation_id",
        "review_decision_id",
        "review_status",
        "split",
        "split_group_id",
    ):
        metadata.pop(field, None)
    copied["metadata"] = metadata
    validate_fapo_case(copied)
    return copied


def _dependency_rows_by_cluster(
    rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> Dict[str, Dict[str, Any]]:
    """Index authentic dependency descriptors by their persisted cluster key."""
    indexed = _unique_rows_by_key(rows, key="cluster_id", source=source)
    dependencies: Dict[str, Dict[str, Any]] = {}
    for cluster_id, row in indexed.items():
        dependency = row.get("dependency")
        if not isinstance(dependency, Mapping) or not dependency_matches(
            dependency,
            dependency,
        ):
            raise ReviewIntegrityError(f"{source} has unauthentic dependency for {cluster_id!r}")
        dependencies[cluster_id] = dict(dependency)
    return dependencies


def _dependency_rows_by_case(
    rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> Dict[str, Dict[str, Any]]:
    """Index authentic dependency descriptors by their persisted case key."""
    indexed = _unique_rows_by_key(rows, key="case_id", source=source)
    dependencies: Dict[str, Dict[str, Any]] = {}
    for case_id, row in indexed.items():
        dependency = row.get("dependency")
        if not isinstance(dependency, Mapping) or not dependency_matches(
            dependency,
            dependency,
        ):
            raise ReviewIntegrityError(
                f"{source} has unauthentic dependency for {case_id!r}"
            )
        dependencies[case_id] = dict(dependency)
    return dependencies


def _review_dependencies_by_case(
    layout: EvaluationAssetLayout,
    review_items: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Resolve every queued case to its complete current Stage 6/7 dependency."""
    inference_by_cluster = _dependency_rows_by_cluster(
        _load_jsonl(
            layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inference_dependencies.jsonl",
            )
        ),
        source="inference dependencies",
    )
    inference_path = layout.artifact_path(
        PipelineStage.SYNTHETIC_COVERAGE,
        "inferred_review_dependencies.jsonl",
    )
    inference_by_case = (
        _dependency_rows_by_case(
            _load_jsonl(inference_path),
            source="inferred review dependencies",
        )
        if inference_path.is_file()
        else {}
    )
    synthetic = _dependency_rows_by_cluster(
        _load_jsonl(
            layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_dependencies.jsonl",
            )
        ),
        source="synthetic dependencies",
    )
    resolved: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        case_id = str(item.get("case_id") or "")
        case = item.get("case")
        metadata = case.get("metadata") if isinstance(case, Mapping) else None
        if not case_id or not isinstance(metadata, Mapping):
            raise ReviewIntegrityError("review item case authority is malformed")
        cluster_id = str(metadata.get("source_cluster") or "")
        trust_tier = str(metadata.get("trust_tier") or "")
        if trust_tier == INFERRED_FROM_TRUSTED_FEEDBACK:
            dependency = inference_by_case.get(case_id) or inference_by_cluster.get(
                cluster_id
            )
        elif trust_tier == SYNTHETIC_FROM_TRUSTED_RUBRIC:
            dependency = synthetic.get(cluster_id)
        else:
            dependency = None
        if dependency is None or case_id in resolved:
            raise ReviewIntegrityError(f"review item {case_id!r} has no unique current dependency")
        resolved[case_id] = dependency
    return resolved


def _review_source_provenance(
    case: Mapping[str, Any],
    dependency: Mapping[str, Any],
) -> Dict[str, Any]:
    """Project exact source member identities from one authentic dependency."""
    descriptor = dependency.get("descriptor")
    metadata = case.get("metadata")
    if not isinstance(descriptor, Mapping) or not isinstance(metadata, Mapping):
        raise ReviewIntegrityError("review source dependency is malformed")
    schema_version = dependency.get("schema_version")
    if schema_version == "fapo-stage-six-dependency-v1":
        record_ids = [str(case["case_id"]).removeprefix("inferred-")]
        members = descriptor.get("source_members")
        match = descriptor.get("match")
    elif schema_version == "fapo-stage-seven-dependency-v1":
        cluster = descriptor.get("cluster")
        nested = descriptor.get("stage_six_dependency")
        nested_descriptor = nested.get("descriptor") if isinstance(nested, Mapping) else None
        if not isinstance(cluster, Mapping) or not isinstance(
            nested_descriptor,
            Mapping,
        ):
            raise ReviewIntegrityError("synthetic review dependency is malformed")
        record_ids = [str(value) for value in cluster.get("representative_ids", [])]
        members = nested_descriptor.get("source_members")
        match = nested_descriptor.get("match")
    else:
        raise ReviewIntegrityError("review dependency schema is unsupported")
    if (
        not record_ids
        or not isinstance(members, list)
        or not isinstance(
            match,
            Mapping,
        )
    ):
        raise ReviewIntegrityError("review source provenance is incomplete")
    hashes_by_id: Dict[str, str] = {}
    for member in members:
        if not isinstance(member, Mapping):
            raise ReviewIntegrityError("review source member is malformed")
        identity = str(member.get("identity") or "")
        digest = str(member.get("content_sha256") or "")
        if identity.startswith("unlabeled:"):
            hashes_by_id[identity.removeprefix("unlabeled:")] = digest
    try:
        source_hashes = ["sha256:" + hashes_by_id[record_id] for record_id in record_ids]
    except KeyError as exc:
        raise ReviewIntegrityError("review source record is absent from dependency authority") from exc
    matched_intent_id = str(metadata.get("matched_intent_id") or match.get("matched_intent_id") or "")
    source_cluster = str(metadata.get("source_cluster") or "")
    if not matched_intent_id or not source_cluster:
        raise ReviewIntegrityError("review source identity is incomplete")
    return {
        "source_record_ids": record_ids,
        "source_record_sha256s": source_hashes,
        "source_cluster": source_cluster,
        "matched_intent_id": matched_intent_id,
    }


def _has_scoreable_expected(expected: Mapping[str, Any]) -> bool:
    """Recognize nested rubrics plus top-level deterministic scoring oracles."""
    rubric = expected.get("rubric")
    return (isinstance(rubric, Mapping) and has_scoreable_rubric(rubric)) or has_scoreable_rubric(expected)


def _trusted_case_with_split_metadata(
    row: Mapping[str, Any],
    rubric: Mapping[str, Any],
    asset_id: str,
    *,
    correctness_visibility: str,
) -> Dict[str, Any]:
    """Build a trusted case bound to its immutable early split decision."""
    split = row.get("trusted_split")
    split_group_id = row.get("split_group_id")
    if split not in {"train", "validation", "test", "regression"}:
        raise ValueError("trusted feedback is missing its early split assignment")
    if not isinstance(split_group_id, str) or not split_group_id:
        raise ValueError("trusted feedback is missing its split_group_id")
    if row.get("evidence_eligible") is not True:
        raise ValueError("ineligible feedback cannot become a trusted case")
    case = _trusted_case(row, rubric, asset_id)
    metadata = dict(case["metadata"])
    metadata.update(
        {
            "split_group_id": split_group_id,
            "trusted_split": split,
            "evidence_eligible": True,
            "correctness_visibility": correctness_visibility,
        }
    )
    case["metadata"] = metadata
    validate_fapo_case(case)
    return case


def _cluster_lineage(
    previous: Sequence[IntentCluster],
    current: Sequence[IntentCluster],
) -> List[Dict[str, Any]]:
    """Describe cluster continuity using deterministic member overlap."""
    previous_members = {cluster.cluster_id: set(cluster.record_ids) for cluster in previous}
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
    represented = {str(row["previous_cluster_id"]) for row in provisional if row["previous_cluster_id"]}
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


def _feedback_provider_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose complete redacted episode context to evidence extraction."""
    record = {
        "record_id": row["record_id"],
        "task_type": row["task_type"],
        "user_input": row["user_input"],
        "conversation_context": row["conversation_context"],
        "assistant_output": row["assistant_output"],
        "tool_calls": row["tool_calls"],
        "feedback": row["feedback"],
    }
    if "episode" in row:
        record["episode"] = row["episode"]
    return record


def _guideline_provider_example(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose compact observed tool context to guideline synthesis."""
    observed_tool_calls = []
    for position, raw_call in enumerate(row["tool_calls"], start=1):
        call = dict(raw_call)
        if "error" in call and call["error"] is not None:
            outcome_status = "error_returned"
        elif "result" in call:
            outcome_status = "result_returned"
        else:
            outcome_status = "not_recorded"
        observed = {
            "position": position,
            "name": call["name"],
            "arguments": call["arguments"],
            "outcome_status": outcome_status,
        }
        if call.get("call_id"):
            observed["call_id"] = call["call_id"]
        if outcome_status == "error_returned":
            observed["error"] = call["error"]
        observed_tool_calls.append(observed)
    return {
        "record_id": row["record_id"],
        "task_type": row["task_type"],
        "user_input": row["user_input"],
        "feedback_polarity": row["feedback"]["polarity"],
        "observed_tool_calls": observed_tool_calls,
    }


def _normalize_aliased_guideline_response(
    response: Mapping[str, Any],
    *,
    source_id_by_alias: Mapping[str, str],
    route: str,
    evidence: Sequence[Mapping[str, Any]],
    rubric_provider: str,
    rubric_model: str,
    identity_profile: str,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Restore exact source IDs before applying the strict guideline contract."""
    prepared = dict(response)
    raw_guidelines = prepared.get("guidelines")
    if isinstance(raw_guidelines, list):
        guidelines = []
        for raw_guideline in raw_guidelines:
            if not isinstance(raw_guideline, Mapping):
                guidelines.append(raw_guideline)
                continue
            guideline = dict(raw_guideline)
            guideline["source_record_ids"] = _restore_source_ids(
                guideline.get("source_record_ids"),
                source_id_by_alias,
            )
            raw_criteria = guideline.get("criteria")
            if isinstance(raw_criteria, list):
                criteria = []
                for raw_criterion in raw_criteria:
                    if not isinstance(raw_criterion, Mapping):
                        criteria.append(raw_criterion)
                        continue
                    criterion = dict(raw_criterion)
                    criterion.pop("source_record_ids", None)
                    criteria.append(criterion)
                guideline["criteria"] = criteria
            guidelines.append(guideline)
        prepared["guidelines"] = guidelines
    return _normalize_guideline_response(
        prepared,
        route=route,
        evidence=evidence,
        rubric_provider=rubric_provider,
        rubric_model=rubric_model,
        identity_profile=identity_profile,
    )


def _restore_source_ids(value: Any, source_id_by_alias: Mapping[str, str]) -> Any:
    """Restore known aliases and leave unknown values for strict rejection."""
    if not isinstance(value, list):
        return value
    return [source_id_by_alias.get(item, item) if isinstance(item, str) else item for item in value]


def _normalize_intent(row: Mapping[str, Any]) -> Dict[str, Any]:
    prepared = _redact_record(row)
    canonical, tool_names = _intent_text_and_tools(prepared)
    if "request_id" not in prepared:
        prepared["request_id"] = prepared["record_id"]
    prepared["route"] = effective_route(prepared)
    prepared["canonical_intent_text"] = canonical
    prepared["tool_names"] = tool_names
    return prepared


def _canonical_intent_text(row: Mapping[str, Any]) -> str:
    """Build intent text for an already-redacted canonical record."""
    return _intent_text_and_tools(row)[0]


def _intent_text_and_tools(row: Mapping[str, Any]) -> tuple[str, List[str]]:
    tool_calls = row["tool_calls"]
    tool_names = sorted(
        set(_tool_names(tool_calls))
        | set(episode_tool_names(row.get("episode")))
    )
    return canonical_user_intent_text(row), tool_names


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
    for logical_index, (normalized, source) in enumerate(zip(normalized_rows, source_rows)):
        row_number = row_numbers[logical_index] if row_numbers is not None else logical_index + 1
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
        raise ValueError("cluster_count cannot exceed the number of unlabeled records " f"({record_count})")
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
                "evidence_type": _string(item.get("evidence_type")) or "explicit_feedback",
                "evidence_pointer": _string(item.get("evidence_pointer")) or "feedback.rationale",
                "polarity": _string(item.get("polarity")) or _string(source["feedback"].get("polarity")),
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
            digest = hashlib.sha256(f"legacy:{record_id}:{kind}:{statement}".encode("utf-8")).hexdigest()[:10]
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
        "tool_expectations": _normalize_tool_expectations(rubric.get("tool_expectations")),
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
        "tool_expectations": _normalize_tool_expectations(raw.get("tool_expectations")),
        "reference_output": (
            _string(raw.get("reference_output")) if raw.get("reference_output") is not None else None
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
            raise ValueError(f"Inferred rubric response omitted {cluster.cluster_id}")
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
    digest = hashlib.sha256(f"{cluster.cluster_id}:{candidate_index}".encode("utf-8")).hexdigest()[:10]
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


def _legacy_episode_candidate_rows(
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
    guidelines: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Reconstruct the old one-candidate behavior for resumable old Stage 5s."""
    guideline_ids = {str(row["guideline_id"]) for row in guidelines}
    match_by_cluster = {match.cluster_id: match for match in matches}
    rows: List[Dict[str, Any]] = []
    for cluster in clusters:
        match = match_by_cluster[cluster.cluster_id]
        matched_id = str(match.matched_intent_id or "")
        candidates = []
        if matched_id in guideline_ids:
            candidates.append(
                {
                    "guideline_id": matched_id,
                    "intent_label": match.matched_label,
                    "cluster_score": match.score,
                    "episode_score": match.score,
                    "retrieval_score": match.score,
                    "retrieval_sources": ["legacy_cluster_match"],
                }
            )
        for record_id in cluster.record_ids:
            rows.append(
                {
                    "record_id": record_id,
                    "cluster_id": cluster.cluster_id,
                    "route": cluster.route,
                    "candidates": candidates,
                }
            )
    return rows


def _attach_applicability_contracts(
    guidelines: Sequence[Mapping[str, Any]],
    contracts_by_intent_label: Optional[
        Mapping[str, Mapping[str, Any]]
    ],
) -> List[Dict[str, Any]]:
    """Attach one reviewed contract to every guideline in a frozen library."""
    if contracts_by_intent_label is None:
        return [dict(guideline) for guideline in guidelines]
    intent_labels = [
        str(guideline.get("intent_label") or "")
        for guideline in guidelines
    ]
    if not all(intent_labels) or len(set(intent_labels)) != len(intent_labels):
        raise ValueError(
            "Applicability contracts require unique nonempty guideline intent labels"
        )
    if set(contracts_by_intent_label) != set(intent_labels):
        missing = sorted(set(intent_labels) - set(contracts_by_intent_label))
        extra = sorted(set(contracts_by_intent_label) - set(intent_labels))
        raise ValueError(
            "Applicability contract inventory differs from the guideline library: "
            f"missing={missing}, extra={extra}"
        )
    return [
        {
            **dict(guideline),
            "applicability_contract": dict(
                contracts_by_intent_label[str(guideline["intent_label"])]
            ),
        }
        for guideline in guidelines
    ]


def _build_applicability_groups(
    *,
    eligible_record_ids: set[str],
    candidate_by_record: Mapping[str, Mapping[str, Any]],
    raw_by_id: Mapping[str, Mapping[str, Any]],
    guideline_by_id: Mapping[str, Mapping[str, Any]],
    unknown_policy: str = "llm_fallback",
    semantic_review_guideline_ids: Collection[str] = (),
    use_applicability_contracts: bool = True,
    use_deterministic_candidate_filters: bool = True,
) -> tuple[
    List[Dict[str, Any]],
    Dict[str, Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """Build deduplicated episode decisions for direct or hybrid applicability.

    The production episode path uses retrieval followed by direct semantic
    review of every candidate.  Deterministic filters and applicability
    contracts remain opt-in for controlled comparisons and reviewed policies.
    """
    if unknown_policy not in {"llm_fallback", "not_supported"}:
        raise ValueError(
            "unknown_policy must be 'llm_fallback' or 'not_supported'"
        )
    review_guideline_ids = {str(item) for item in semantic_review_guideline_ids}
    unknown_review_guideline_ids = sorted(
        review_guideline_ids - set(guideline_by_id)
    )
    if unknown_review_guideline_ids:
        raise ValueError(
            "Semantic-review guideline IDs are absent from the guideline library: "
            f"{unknown_review_guideline_ids}"
        )
    groups_by_signature: Dict[str, Dict[str, Any]] = {}
    for record_id in sorted(eligible_record_ids):
        if record_id not in raw_by_id:
            raise ValueError(f"Missing raw episode {record_id}")
        candidate_row = candidate_by_record[record_id]
        raw_candidates = candidate_row.get("candidates")
        if not isinstance(raw_candidates, list):
            raise ValueError(f"Episode candidates are invalid for {record_id}")
        observable = _episode_observables(raw_by_id[record_id])
        episode_facts = extract_episode_facts(observable)
        active_candidates: List[Dict[str, Any]] = []
        hard_rejections: List[Dict[str, Any]] = []
        hard_acceptances: List[Dict[str, Any]] = []
        semantic_review_acceptances: List[Dict[str, Any]] = []
        unsupported_unknowns: List[Dict[str, Any]] = []
        contract_sha256_by_guideline: Dict[str, str] = {}
        seen: set[str] = set()
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, Mapping):
                raise ValueError(f"Episode candidate is invalid for {record_id}")
            guideline_id = str(raw_candidate.get("guideline_id") or "")
            if not guideline_id or guideline_id in seen:
                raise ValueError(f"Episode candidate identity is invalid for {record_id}")
            seen.add(guideline_id)
            guideline = guideline_by_id.get(guideline_id)
            if guideline is None:
                raise ValueError(
                    f"Episode candidate {guideline_id} has no evaluation guideline"
                )
            if str(guideline.get("route") or "") != str(
                candidate_row.get("route") or ""
            ):
                hard_rejections.append(
                    {
                        "guideline_id": guideline_id,
                        "reason": "candidate route differs from the episode route",
                        "evidence_pointers": [],
                        "decision_source": "deterministic_route_filter",
                    }
                )
                continue
            rejection = (
                _deterministic_candidate_rejection(observable, guideline)
                if use_deterministic_candidate_filters
                else None
            )
            if rejection:
                hard_rejections.append(
                    {
                        "guideline_id": guideline_id,
                        "reason": rejection,
                        "evidence_pointers": [],
                        "decision_source": "deterministic_contradiction_filter",
                    }
                )
                continue
            contract = (
                compile_applicability_contract(guideline)
                if use_applicability_contracts
                else None
            )
            if contract is not None:
                contract_sha256_by_guideline[guideline_id] = hashlib.sha256(
                    json.dumps(
                        contract,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()
                contract_decision = evaluate_applicability_contract(
                    episode_facts,
                    contract,
                )
                deterministic_item = {
                    "guideline_id": guideline_id,
                    "reason": contract_decision.reason,
                    "evidence_pointers": list(
                        contract_decision.evidence_pointers
                    ),
                    "decision_source": "deterministic_applicability_contract",
                }
                if contract_decision.status == "not_applicable":
                    hard_rejections.append(deterministic_item)
                    continue
                if contract_decision.status == "applicable":
                    if guideline_id in review_guideline_ids:
                        active_candidates.append(dict(raw_candidate))
                        semantic_review_acceptances.append(
                            {
                                **deterministic_item,
                                "decision_source": (
                                    "deterministic_applicability_contract_"
                                    "pending_semantic_review"
                                ),
                            }
                        )
                        continue
                    hard_acceptances.append(deterministic_item)
                    continue
                if unknown_policy == "not_supported":
                    unsupported_unknowns.append(
                        {
                            **deterministic_item,
                            "decision_source": (
                                "deterministic_unknown_not_supported_policy"
                            ),
                        }
                    )
                    continue
            active_candidates.append(dict(raw_candidate))

        signature_payload = {
            "observable_episode": observable,
            "candidate_guideline_ids": [
                str(item["guideline_id"]) for item in active_candidates
            ],
            "hard_rejections": hard_rejections,
            "hard_acceptances": hard_acceptances,
            "semantic_review_acceptances": semantic_review_acceptances,
            "unsupported_unknowns": unsupported_unknowns,
            "unknown_policy": unknown_policy,
            "applicability_contract_sha256_by_guideline": (
                contract_sha256_by_guideline
            ),
        }
        signature = hashlib.sha256(
            json.dumps(
                signature_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        group = groups_by_signature.get(signature)
        if group is None:
            group = {
                "decision_id": f"applicability-{signature[:24]}",
                "observable_signature_sha256": signature,
                "observable_episode": observable,
                "structured_episode_facts": episode_facts.to_dict(),
                "candidate_guideline_ids": [
                    str(item["guideline_id"]) for item in active_candidates
                ],
                "retrieved_candidates": [dict(item) for item in raw_candidates],
                "hard_rejections": hard_rejections,
                "hard_acceptances": hard_acceptances,
                "semantic_review_acceptances": semantic_review_acceptances,
                "unsupported_unknowns": unsupported_unknowns,
                "unknown_policy": unknown_policy,
                "applicability_contract_sha256_by_guideline": (
                    contract_sha256_by_guideline
                ),
                "record_ids": [],
                "cluster_id_by_record": {},
            }
            groups_by_signature[signature] = group
        group["record_ids"].append(record_id)
        group["cluster_id_by_record"][record_id] = str(
            candidate_row["cluster_id"]
        )

    groups = sorted(groups_by_signature.values(), key=lambda row: row["decision_id"])
    group_by_record = {
        record_id: group
        for group in groups
        for record_id in group["record_ids"]
    }
    deterministic_rows = [
        {
            "decision_id": group["decision_id"],
            "applicable_guideline_ids": [
                str(item["guideline_id"])
                for item in group["hard_acceptances"]
            ],
            "confidence": 1.0,
            "reason": (
                "All retrieved candidates were resolved by deterministic "
                "applicability contracts, contradiction checks, or the "
                "configured unknown-evidence policy."
            ),
            "evidence_pointers": list(
                dict.fromkeys(
                    pointer
                    for item in (
                        group["hard_acceptances"]
                        + group["hard_rejections"]
                        + group["semantic_review_acceptances"]
                        + group["unsupported_unknowns"]
                    )
                    for pointer in item["evidence_pointers"]
                )
            ),
            "candidate_decisions": [],
            "decision_source": "deterministic_applicability_contract",
        }
        for group in groups
        if not group["candidate_guideline_ids"]
    ]
    llm_groups = [group for group in groups if group["candidate_guideline_ids"]]
    return llm_groups, group_by_record, deterministic_rows


def _episode_observables(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Return compact, redacted request and tool-state evidence for gating."""
    prepared = _redact_record(row)
    user_messages = record_user_messages(prepared)
    tool_observations: List[Dict[str, Any]] = []
    episode = prepared.get("episode")
    if isinstance(episode, Mapping) and isinstance(episode.get("events"), list):
        calls_by_id: Dict[str, Dict[str, Any]] = {}
        for event_index, raw_event in enumerate(episode["events"]):
            if not isinstance(raw_event, Mapping):
                continue
            event_type = raw_event.get("type")
            if event_type == "tool_call":
                call_id = str(raw_event.get("call_id") or "")
                observation = {
                    "pointer": f"episode.events[{event_index}]",
                    "name": str(raw_event.get("name") or ""),
                    "arguments": _compact_tool_value(raw_event.get("arguments")),
                    "outcome_status": "not_recorded",
                }
                calls_by_id[call_id] = observation
                tool_observations.append(observation)
            elif event_type == "tool_result":
                call_id = str(raw_event.get("call_id") or "")
                observation = calls_by_id.get(call_id)
                if observation is None:
                    continue
                if raw_event.get("error") is not None:
                    observation["outcome_status"] = "error_returned"
                    observation["error"] = _compact_tool_value(raw_event["error"])
                else:
                    observation["outcome_status"] = "result_returned"
                    observation["result_state"] = _compact_tool_result(
                        raw_event.get("result")
                    )
    else:
        for index, raw_call in enumerate(prepared.get("tool_calls") or []):
            if not isinstance(raw_call, Mapping):
                continue
            observation = {
                "pointer": f"tool_calls[{index}]",
                "name": str(raw_call.get("name") or ""),
                "arguments": _compact_tool_value(raw_call.get("arguments")),
                "outcome_status": "not_recorded",
            }
            if raw_call.get("error") is not None:
                observation["outcome_status"] = "error_returned"
                observation["error"] = _compact_tool_value(raw_call["error"])
            elif "result" in raw_call:
                observation["outcome_status"] = "result_returned"
                observation["result_state"] = _compact_tool_result(
                    raw_call.get("result")
                )
            tool_observations.append(observation)
    return {
        "user_messages": user_messages,
        "tool_observations": tool_observations,
    }


def _compact_tool_value(value: Any, *, depth: int = 0) -> Any:
    """Bound arbitrary tool data while retaining useful arguments."""
    if depth > 4:
        return "<nested>"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return _compact_tool_value(json.loads(stripped), depth=depth + 1)
            except (json.JSONDecodeError, TypeError):
                pass
        return stripped if len(stripped) <= 500 else stripped[:497] + "..."
    if isinstance(value, Mapping):
        return {
            str(key): _compact_tool_value(nested, depth=depth + 1)
            for key, nested in list(value.items())[:30]
        }
    if isinstance(value, list):
        return [
            _compact_tool_value(item, depth=depth + 1) for item in value[:20]
        ]
    return value


_RESULT_STATE_KEY_RE = re.compile(
    r"(?:status|state|reason|error|address|payment|refund|balance|price|"
    r"difference|tracking|cancel|return|exchange|available|order_id|item_id|"
    r"resource_id|"
    r"method|amount)",
    re.I,
)
_RESULT_BULK_KEYS = {"variants", "products"}
_RESULT_ITEM_IDENTITY_KEYS = {"item_id", "name", "product_id", "resource_id"}


def _compact_tool_result(value: Any, *, depth: int = 0) -> Any:
    """Extract bounded state-bearing fields from potentially large results."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                return stripped if len(stripped) <= 300 else stripped[:297] + "..."
        else:
            return stripped if len(stripped) <= 300 else stripped[:297] + "..."
    if depth > 4:
        return "<nested>"
    if isinstance(value, Mapping):
        output: Dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if key_text.lower() == "items":
                item_summaries = _compact_result_item_identities(nested)
                if item_summaries:
                    output[key_text] = item_summaries
                continue
            if key_text.lower() in _RESULT_BULK_KEYS:
                continue
            if _RESULT_STATE_KEY_RE.search(key_text):
                output[key_text] = _compact_tool_value(nested, depth=depth + 1)
            elif isinstance(nested, (Mapping, list)):
                compact = _compact_tool_result(nested, depth=depth + 1)
                if compact not in ({}, [], None):
                    output[key_text] = compact
            if len(output) >= 24:
                break
        return output
    if isinstance(value, list):
        compacted = [
            _compact_tool_result(item, depth=depth + 1) for item in value[:10]
        ]
        return [item for item in compacted if item not in ({}, [], None)]
    return value


def _compact_result_item_identities(value: Any) -> List[Dict[str, Any]]:
    """Retain bounded entity identity so state can be tied to requested items."""
    raw_items: Sequence[Any]
    if isinstance(value, list):
        raw_items = value[:20]
    elif isinstance(value, Mapping):
        raw_items = list(value.values())[:20]
    else:
        return []
    output: List[Dict[str, Any]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            continue
        identity = {
            str(key): _compact_tool_value(item)
            for key, item in raw_item.items()
            if str(key).lower() in _RESULT_ITEM_IDENTITY_KEYS
        }
        if identity:
            output.append(identity)
    return output


def _deterministic_candidate_rejection(
    observable: Mapping[str, Any],
    guideline: Mapping[str, Any],
) -> Optional[str]:
    """Reject only high-precision action, scope, or state contradictions."""
    user_text = " ".join(
        str(item).lower() for item in observable.get("user_messages") or []
    )
    activation_text = _guideline_activation_text(guideline)
    intent_label = str(guideline.get("intent_label") or "").lower()

    undo_cancel = bool(
        re.search(
            r"\b(?:undo|reverse|revert|reinstate|restore)\b.{0,40}\b(?:cancel|cancellation)\b",
            user_text,
        )
        or re.search(
            r"\b(?:cancel|cancellation)\b.{0,40}\b(?:undo|reverse|revert|reinstate|restore)\b",
            user_text,
        )
    )
    if (
        undo_cancel
        and re.search(r"\bcancel(?:lation|led|ing)?\b", activation_text)
        and not re.search(r"\b(?:undo|reverse|revert|reinstate|restore)\b", activation_text)
    ):
        return "episode asks to reverse a cancellation, not perform one"

    order_address = bool(
        re.search(r"\b(?:shipping|delivery|order[- ]level) address\b", user_text)
    )
    default_address = bool(
        re.search(r"\b(?:default|account|profile|future) address\b", user_text)
    )
    guideline_order_address = "address" in intent_label and bool(
        re.search(r"\b(?:shipping|delivery|order[-_ ]level)\b", intent_label)
    )
    guideline_default_address = "address" in intent_label and bool(
        re.search(r"\b(?:default|account|profile|future)\b", intent_label)
    )
    if default_address and not order_address and guideline_order_address:
        return "episode requests an account/default address change, not an order address change"
    if order_address and not default_address and guideline_default_address:
        return "episode requests an order address change, not an account/default address change"

    states = _observable_order_states(observable)
    if states == {"delivered"} and re.search(r"\bpending\b", intent_label):
        return "observed order state is delivered, while the guideline requires pending state"
    if states == {"pending"} and re.search(r"\bdelivered\b", intent_label):
        return "observed order state is pending, while the guideline requires delivered state"
    return None


def _guideline_activation_text(guideline: Mapping[str, Any]) -> str:
    criteria = guideline.get("criteria")
    applicability = []
    if isinstance(criteria, list):
        applicability = [
            json.dumps(item.get("applicability"), sort_keys=True)
            for item in criteria
            if isinstance(item, Mapping)
        ]
    return " ".join(
        [
            str(guideline.get("intent_label") or ""),
            str(guideline.get("description") or ""),
            *applicability,
        ]
    ).lower()


def _observable_order_states(observable: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, Mapping):
            for nested_key, nested in value.items():
                visit(nested, str(nested_key))
        elif isinstance(value, list):
            for nested in value:
                visit(nested, key)
        elif key.lower() in {"status", "state"}:
            text = str(value).lower()
            for status in ("pending", "delivered", "processed", "cancelled"):
                if status in text:
                    values.add(status)

    visit(observable.get("tool_observations"))
    return values


def _applicability_batches(
    groups: Sequence[Mapping[str, Any]],
) -> Iterable[List[Mapping[str, Any]]]:
    """Batch by both decision count and candidate-pair payload cost."""
    batch: List[Mapping[str, Any]] = []
    pair_count = 0
    for group in groups:
        group_pairs = len(group["candidate_guideline_ids"])
        if batch and (
            len(batch) >= GUIDELINE_APPLICABILITY_MAX_GROUPS_PER_CALL
            or pair_count + group_pairs
            > GUIDELINE_APPLICABILITY_MAX_CANDIDATE_PAIRS_PER_CALL
        ):
            yield batch
            batch = []
            pair_count = 0
        batch.append(group)
        pair_count += group_pairs
    if batch:
        yield batch


def _applicability_provider_payload(
    groups: Sequence[Mapping[str, Any]],
    guideline_by_id: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    guideline_ids = sorted(
        {
            str(guideline_id)
            for group in groups
            for guideline_id in group["candidate_guideline_ids"]
        }
    )
    return {
        "mode": "episode_guideline_applicability",
        "guidelines": [
            _applicability_guideline_card(guideline_by_id[item])
            for item in guideline_ids
        ],
        "decision_groups": [
            {
                "decision_id": group["decision_id"],
                "observable_episode": group["observable_episode"],
                "structured_episode_facts": group["structured_episode_facts"],
                "candidate_guideline_ids": group["candidate_guideline_ids"],
            }
            for group in groups
        ],
    }


def _applicability_guideline_card(guideline: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "guideline_id": guideline["guideline_id"],
        "intent_label": guideline["intent_label"],
        "description": guideline["description"],
        "criteria": [
            {
                "criterion_id": item["criterion_id"],
                "kind": item["kind"],
                "statement": item["statement"],
                "applicability": item["applicability"],
                "severity": item["severity"],
            }
            for item in guideline["criteria"]
        ],
        "tool_expectations": guideline["tool_expectations"],
    }


def _normalize_applicability_response(
    response: Mapping[str, Any],
    *,
    decision_groups: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    items = response.get("decisions")
    if not isinstance(items, list):
        raise ValueError("Applicability response missing decisions array")
    returned: Dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("Applicability response contains an invalid decision")
        decision_id = str(item.get("decision_id") or "")
        if not decision_id or decision_id in returned:
            raise ValueError("Applicability decision identity is invalid")
        returned[decision_id] = item
    expected_ids = {str(group["decision_id"]) for group in decision_groups}
    if set(returned) != expected_ids:
        raise ValueError("Applicability response omitted or invented a decision_id")

    normalized: List[Dict[str, Any]] = []
    for group in decision_groups:
        decision_id = str(group["decision_id"])
        raw = returned[decision_id]
        candidate_ids = [str(item) for item in group["candidate_guideline_ids"]]
        selected = raw.get("applicable_guideline_ids")
        if (
            not isinstance(selected, list)
            or not all(isinstance(item, str) for item in selected)
        ):
            raise ValueError(f"Applicability selection is invalid for {decision_id}")
        retrieved_ids = {
            str(item["guideline_id"])
            for item in group.get("retrieved_candidates") or []
            if isinstance(item, Mapping) and item.get("guideline_id")
        }
        if not set(selected).issubset(retrieved_ids or set(candidate_ids)):
            raise ValueError(f"Applicability selection is invalid for {decision_id}")
        selected_ids = set(selected) & set(candidate_ids)
        confidence = raw.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(float(confidence))
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise ValueError(f"Applicability confidence is invalid for {decision_id}")
        reason = str(raw.get("reason") or "").strip()
        pointers = raw.get("evidence_pointers")
        if (
            not reason
            or not isinstance(pointers, list)
            or not all(isinstance(item, str) for item in pointers)
        ):
            raise ValueError(f"Applicability rationale is invalid for {decision_id}")
        candidate_reason_by_id: Dict[str, str] = {}
        raw_candidate_decisions = raw.get("candidate_decisions")
        if isinstance(raw_candidate_decisions, list):
            for candidate in raw_candidate_decisions:
                if not isinstance(candidate, Mapping):
                    continue
                guideline_id = str(candidate.get("guideline_id") or "")
                candidate_reason = str(candidate.get("reason") or "").strip()
                if guideline_id in candidate_ids and candidate_reason:
                    candidate_reason_by_id.setdefault(
                        guideline_id,
                        candidate_reason,
                    )
        candidate_decisions = [
            {
                "guideline_id": guideline_id,
                "status": (
                    "applicable"
                    if guideline_id in selected_ids
                    else "not_applicable"
                ),
                "reason": candidate_reason_by_id.get(guideline_id, reason),
            }
            for guideline_id in candidate_ids
        ]
        normalized.append(
            {
                "decision_id": decision_id,
                "applicable_guideline_ids": [
                    guideline_id
                    for guideline_id in candidate_ids
                    if guideline_id in selected_ids
                ],
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "evidence_pointers": list(pointers),
                "candidate_decisions": candidate_decisions,
                "decision_source": "llm_episode_applicability",
            }
        )
    return normalized


def _merge_applicability_decision(
    group: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> Dict[str, Any]:
    """Merge deterministic contract results with an LLM fallback decision."""
    hard_acceptances = list(group.get("hard_acceptances") or [])
    hard_rejections = list(group.get("hard_rejections") or [])
    semantic_review_acceptances = list(
        group.get("semantic_review_acceptances") or []
    )
    unsupported_unknowns = list(group.get("unsupported_unknowns") or [])
    if (
        not hard_acceptances
        and not hard_rejections
        and not semantic_review_acceptances
        and not unsupported_unknowns
    ):
        return dict(decision)

    selected = {
        str(item) for item in decision["applicable_guideline_ids"]
    } | {
        str(item["guideline_id"]) for item in hard_acceptances
    }
    ordered_selected = [
        str(item["guideline_id"])
        for item in group["retrieved_candidates"]
        if str(item["guideline_id"]) in selected
    ]
    deterministic_pointers = [
        str(pointer)
        for item in (
            hard_acceptances
            + hard_rejections
            + semantic_review_acceptances
            + unsupported_unknowns
        )
        for pointer in item.get("evidence_pointers") or []
    ]
    pointers = list(
        dict.fromkeys(
            deterministic_pointers
            + [str(item) for item in decision["evidence_pointers"]]
        )
    )
    return {
        **dict(decision),
        "applicable_guideline_ids": ordered_selected,
        "reason": (
            f"Deterministic contracts resolved {len(hard_acceptances)} applicable "
            f"and {len(hard_rejections)} not-applicable candidate(s), while "
            f"{len(semantic_review_acceptances)} proposed acceptance(s) received "
            "semantic review and "
            f"{len(unsupported_unknowns)} unresolved candidate(s) were not "
            "automatically supported; "
            + str(decision["reason"])
        ),
        "evidence_pointers": pointers,
        "decision_source": "hybrid_episode_applicability",
    }


def _record_applicability_row(
    *,
    record_id: str,
    group: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> Dict[str, Any]:
    hard_by_id = {
        str(item["guideline_id"]): {
            "guideline_id": str(item["guideline_id"]),
            "status": "not_applicable",
            "reason": str(item["reason"]),
            "evidence_pointers": list(item.get("evidence_pointers") or []),
            "decision_source": str(item["decision_source"]),
        }
        for item in group["hard_rejections"]
    }
    accepted_by_id = {
        str(item["guideline_id"]): {
            "guideline_id": str(item["guideline_id"]),
            "status": "applicable",
            "reason": str(item["reason"]),
            "evidence_pointers": list(item.get("evidence_pointers") or []),
            "decision_source": str(item["decision_source"]),
        }
        for item in group.get("hard_acceptances") or []
    }
    unsupported_by_id = {
        str(item["guideline_id"]): {
            "guideline_id": str(item["guideline_id"]),
            "status": "not_automatically_supported",
            "reason": str(item["reason"]),
            "evidence_pointers": list(item.get("evidence_pointers") or []),
            "decision_source": str(item["decision_source"]),
        }
        for item in group.get("unsupported_unknowns") or []
    }
    semantic_review_ids = {
        str(item["guideline_id"])
        for item in group.get("semantic_review_acceptances") or []
    }
    llm_by_id = {
        str(item["guideline_id"]): {
            **dict(item),
            "decision_source": (
                "llm_semantic_review_of_deterministic_acceptance"
                if str(item["guideline_id"]) in semantic_review_ids
                else decision["decision_source"]
            ),
        }
        for item in decision["candidate_decisions"]
    }
    candidate_decisions = []
    for candidate in group["retrieved_candidates"]:
        guideline_id = str(candidate["guideline_id"])
        candidate_decisions.append(
            {
                **dict(candidate),
                **(
                    hard_by_id.get(guideline_id)
                    or accepted_by_id.get(guideline_id)
                    or unsupported_by_id.get(guideline_id)
                    or llm_by_id[guideline_id]
                ),
            }
        )
    return {
        "record_id": record_id,
        "cluster_id": str(group["cluster_id_by_record"][record_id]),
        "decision_id": decision["decision_id"],
        "observable_signature_sha256": group["observable_signature_sha256"],
        "deduplicated_record_count": len(group["record_ids"]),
        "structured_episode_facts": dict(group["structured_episode_facts"]),
        "applicability_contract_sha256_by_guideline": dict(
            group.get("applicability_contract_sha256_by_guideline") or {}
        ),
        "unknown_policy": str(group.get("unknown_policy") or "llm_fallback"),
        "not_automatically_supported_guideline_ids": [
            str(item["guideline_id"])
            for item in group.get("unsupported_unknowns") or []
        ],
        "semantically_reviewed_guideline_ids": sorted(semantic_review_ids),
        "semantic_review_proposals": [
            dict(item)
            for item in group.get("semantic_review_acceptances") or []
        ],
        "applicable_guideline_ids": list(decision["applicable_guideline_ids"]),
        "confidence": decision["confidence"],
        "reason": decision["reason"],
        "evidence_pointers": list(decision["evidence_pointers"]),
        "decision_source": decision["decision_source"],
        "candidate_decisions": candidate_decisions,
    }


def _guideline_dependency_bundle(
    guidelines: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    guideline_ids = [str(row["guideline_id"]) for row in guidelines]
    source_ids = sorted(
        {
            str(record_id)
            for guideline in guidelines
            for record_id in guideline["source_record_ids"]
        }
    )
    return {
        "bundle_id": "guideline-bundle-"
        + hashlib.sha256("\n".join(guideline_ids).encode("utf-8")).hexdigest()[:24],
        "guideline_ids": guideline_ids,
        "source_record_ids": source_ids,
        "guidelines": [dict(row) for row in guidelines],
    }


def _episode_gate_cluster_hold(
    cluster: IntentCluster,
    record_ids: Sequence[str],
    selected_ids_by_record: Mapping[str, tuple[str, ...]],
    rubric_by_record: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Explain why one cluster cannot support one synthetic-generation rubric."""
    selected_sets = sorted(
        {selected_ids_by_record.get(record_id, ()) for record_id in record_ids}
    )
    if not record_ids:
        hold_reason = "no_unlabeled_episode_members"
        reason = "No unlabeled episode remains after trusted-record exclusion."
    elif any(
        not selected_ids_by_record.get(record_id)
        or record_id not in rubric_by_record
        for record_id in record_ids
    ):
        hold_reason = "episode_guideline_coverage_gap"
        reason = "At least one episode lacks a supported, scoreable guideline set."
    else:
        hold_reason = "heterogeneous_episode_guideline_sets"
        reason = (
            "Real episodes were labeled individually, but the cluster has no "
            "single rubric suitable for cluster-level synthetic generation."
        )
    return {
        "cluster_id": cluster.cluster_id,
        "hold_reason": hold_reason,
        "reason": reason,
        "record_ids": list(record_ids),
        "selected_guideline_sets": [list(item) for item in selected_sets],
    }


def _eligible_episode_record_ids(
    clusters: Sequence[IntentCluster],
    trusted_record_ids: Collection[str],
) -> set[str]:
    """Return all non-trusted episodes without applying a cluster support gate."""
    trusted = set(trusted_record_ids)
    return {
        record_id
        for cluster in clusters
        for record_id in cluster.record_ids
        if record_id not in trusted
    }


def _episode_cluster_support(
    *,
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
    row_by_id: Mapping[str, Mapping[str, Any]],
    eligible_record_ids: Collection[str],
    selected_ids_by_record: Mapping[str, tuple[str, ...]],
    rubric_by_record: Mapping[str, Mapping[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Aggregate post-gate episode support without using cluster similarity as proof.

    Cluster similarity is a retrieval signal only.  A cluster is supported when
    every unlabeled episode in it received a nonempty, scoreable guideline set
    from the episode applicability gate.  Mixed clusters remain useful for
    episode-level cases but are reported as only partially supported.
    """
    eligible = set(eligible_record_ids)
    match_by_cluster = {match.cluster_id: match for match in matches}
    support_rows: List[Dict[str, Any]] = []
    missing_rows: List[Dict[str, Any]] = []
    for cluster in clusters:
        match = match_by_cluster[cluster.cluster_id]
        record_ids = [
            record_id for record_id in cluster.record_ids if record_id in eligible
        ]
        supported_ids = [
            record_id
            for record_id in record_ids
            if selected_ids_by_record.get(record_id)
            and record_id in rubric_by_record
        ]
        unsupported_ids = [
            record_id for record_id in record_ids if record_id not in supported_ids
        ]
        selected_guideline_ids = sorted(
            {
                guideline_id
                for record_id in supported_ids
                for guideline_id in selected_ids_by_record[record_id]
            }
        )
        if not record_ids:
            status = "no_unlabeled_episode_members"
            reason = "No unlabeled episode remains after trusted-record exclusion."
        elif not unsupported_ids:
            status = "supported"
            reason = (
                "Every unlabeled episode received a supported, scoreable "
                "guideline set from the episode applicability gate."
            )
        elif supported_ids:
            status = "partially_supported"
            reason = (
                "Only some unlabeled episodes received a supported, scoreable "
                "guideline set from the episode applicability gate."
            )
        else:
            status = "unsupported"
            reason = (
                "No unlabeled episode received a supported, scoreable guideline "
                "set from the episode applicability gate."
            )
        unsupported_reasons = {
            record_id: (
                "no_applicable_guideline"
                if not selected_ids_by_record.get(record_id)
                else "unscoreable_episode_rubric"
            )
            for record_id in unsupported_ids
        }
        support_row = {
            "cluster_id": cluster.cluster_id,
            "route": cluster.route,
            "status": status,
            "reason": reason,
            "unlabeled_episode_count": len(record_ids),
            "supported_episode_count": len(supported_ids),
            "unsupported_episode_count": len(unsupported_ids),
            "support_rate": (
                round(len(supported_ids) / len(record_ids), 4)
                if record_ids
                else None
            ),
            "supported_record_ids": supported_ids,
            "unsupported_records": [
                {
                    "record_id": record_id,
                    "reason": unsupported_reasons[record_id],
                }
                for record_id in unsupported_ids
            ],
            "selected_guideline_ids": selected_guideline_ids,
            "retrieval_cluster_status": match.status,
            "retrieval_best_candidate_guideline_id": match.matched_intent_id,
            "retrieval_cluster_score": match.score,
        }
        support_rows.append(support_row)
        if status not in {"partially_supported", "unsupported"}:
            continue
        missing_rows.append(
            {
                "cluster_id": cluster.cluster_id,
                "route": cluster.route,
                "size": cluster.size,
                "status": (
                    "partially_supported_after_episode_gate"
                    if status == "partially_supported"
                    else "unsupported_after_episode_gate"
                ),
                "reason": reason,
                "best_candidate_intent_id": match.matched_intent_id,
                "match_score": match.score,
                "supported_episode_count": len(supported_ids),
                "unsupported_episode_count": len(unsupported_ids),
                "unsupported_records": support_row["unsupported_records"],
                "representative_examples": [
                    {
                        "record_id": record_id,
                        "user_input": row_by_id[record_id]["user_input"],
                    }
                    for record_id in cluster.representative_ids
                ],
            }
        )
    return support_rows, missing_rows


def _inferred_episode_cases(
    *,
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
    intent_rows: Sequence[Mapping[str, Any]],
    raw_rows: Sequence[Mapping[str, Any]],
    rubric_by_record: Mapping[str, Mapping[str, Any]],
    decision_by_record: Mapping[str, Mapping[str, Any]],
    config: EvaluationAssetConfig,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    match_by_cluster = {match.cluster_id: match for match in matches}
    intent_by_id = {str(row["record_id"]): row for row in intent_rows}
    raw_by_id = {str(row["record_id"]): row for row in raw_rows}
    labels: List[Dict[str, Any]] = []
    cases: List[Dict[str, Any]] = []
    for cluster in clusters:
        match = match_by_cluster[cluster.cluster_id]
        for record_id in cluster.record_ids:
            rubric = rubric_by_record.get(record_id)
            if rubric is None:
                continue
            decision = decision_by_record[record_id]
            intent = intent_by_id[record_id]
            raw = raw_by_id[record_id]
            expected = _expected(rubric)
            applicable_ids = list(rubric["evaluation_guideline_ids"])
            labels.append(
                {
                    "record_id": record_id,
                    "cluster_id": cluster.cluster_id,
                    "matched_intent_id": match.matched_intent_id,
                    "match_score": match.score,
                    "applicable_guideline_ids": applicable_ids,
                    "applicability_decision_id": decision["decision_id"],
                    "applicability_confidence": decision["confidence"],
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
                    "applicable_guideline_ids": applicable_ids,
                    "applicability_decision_id": decision["decision_id"],
                    "applicability_confidence": decision["confidence"],
                    "dataset_version": config.asset_id,
                    "group_id": intent["group_id"],
                    "request_id": intent["request_id"],
                    "trust_tier": INFERRED_FROM_TRUSTED_FEEDBACK,
                    "review_status": "review_required",
                },
            }
            validate_fapo_case(case)
            cases.append(case)
    return labels, cases


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
        rubric = rubric_by_cluster.get(cluster.cluster_id)
        if rubric is None:
            continue
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
                raise ValueError(f"Cluster {cluster.cluster_id} references unknown record {record_id}")
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
                    "acquisition": dict(LABELING_QUEUE_ACQUISITION),
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


def _discard_provider_metadata(provider: Any) -> None:
    """Discard stale optional metadata without expanding the provider contract."""
    drain = getattr(provider, "drain_call_metadata", None)
    if callable(drain):
        try:
            drain()
        except Exception:  # noqa: BLE001
            pass


def _drain_provider_metadata(provider: Any) -> Any:
    """Return sanitized optional metadata or one explicit unavailable marker."""
    drain = getattr(provider, "drain_call_metadata", None)
    if not callable(drain):
        return None
    try:
        return sanitize_call_metadata(drain())
    except Exception:  # noqa: BLE001
        return unavailable("metadata_failed_validation")


def _stage_seeds(
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    *,
    call_count: int = 0,
) -> dict[str, Any]:
    if stage == PipelineStage.PREPARED_INPUTS:
        return {"split": config.split_seed}
    if STAGE_SPECIFICATIONS[stage].provider_roles:
        reason = "provider_does_not_use_sampling" if call_count else "stage_made_no_provider_calls"
        return {"sampling": not_applicable(reason)}
    return {"sampling": not_applicable("stage_has_no_provider_role")}


def _stage_algorithms(
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    *,
    extension: bool = False,
) -> dict[str, Any]:
    algorithms = _build_algorithms(config, extension)
    return {"stage": stage.value, "revision": algorithms[stage.value]}


def _build_algorithms(
    config: EvaluationAssetConfig,
    extension: bool,
) -> dict[str, Any]:
    return build_algorithm_inventory(config.to_dict(), extension=extension)


def _publication_fault_point(name: str) -> None:
    workspace_module._fault_point(name)


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
        matched_intent_id=(str(row["matched_intent_id"]) if row.get("matched_intent_id") else None),
        matched_label=(str(row["matched_label"]) if row.get("matched_label") else None),
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


def _stage_six_dependency(
    *,
    cluster: IntentCluster,
    match: IntentMatch,
    guideline: Mapping[str, Any],
    intent_rows: Mapping[str, Mapping[str, Any]],
    trusted_rows: Mapping[str, Mapping[str, Any]],
    provider: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the complete, content-bound identity for one inferred rubric."""
    members: list[dict[str, Any]] = []
    for record_id in sorted(cluster.record_ids):
        source = dict(intent_rows[record_id])
        source["dependency_identity"] = f"unlabeled:{record_id}"
        members.append(source)
    for record_id in sorted(str(item) for item in guideline["source_record_ids"]):
        source = dict(trusted_rows[record_id])
        source["dependency_identity"] = f"trusted:{record_id}"
        members.append(source)
    return build_stage_six_dependency(
        cluster=cluster_to_dict(cluster),
        match=match_to_dict(match),
        guideline=guideline,
        source_members=fingerprinted_members(
            members,
            identity_key="dependency_identity",
        ),
        provider=provider,
        prompt={
            "revision": PROMPT_REVISIONS["label_inference"],
            "sha256": hashlib.sha256(INFERENCE_PROMPT.encode("utf-8")).hexdigest(),
        },
        algorithm_revision="stage-six-dependency-v1",
    )


def _stage_seven_dependency(
    *,
    cluster: IntentCluster,
    rubric: Mapping[str, Any],
    stage_six_dependency: Mapping[str, Any],
    comparison_cases: Sequence[Mapping[str, Any]],
    provider: Mapping[str, Any],
    config: EvaluationAssetConfig,
    generation_set: Mapping[str, str],
) -> dict[str, Any]:
    """Build the exact reuse identity for one synthetic generation unit."""
    members = []
    for case in comparison_cases:
        dependency_case = {
            "dependency_identity": str(case["case_id"]),
            "case_id": case["case_id"],
            "task_type": case["task_type"],
            "context": case["context"],
            "expected": case["expected"],
            "metadata": {
                key: value
                for key, value in dict(case.get("metadata") or {}).items()
                if key
                in {
                    "source",
                    "source_cluster",
                    "matched_intent_id",
                    "group_id",
                    "split_group_id",
                    "trust_tier",
                }
            },
        }
        members.append(dependency_case)
    return build_stage_seven_dependency(
        cluster=cluster_to_dict(cluster),
        rubric=rubric,
        stage_six_dependency=stage_six_dependency,
        comparison_members=fingerprinted_members(
            members,
            identity_key="dependency_identity",
        ),
        provider=provider,
        prompt={
            "revision": PROMPT_REVISIONS["synthetic_coverage"],
            "sha256": hashlib.sha256(SYNTHETIC_PROMPT.encode("utf-8")).hexdigest(),
        },
        settings={
            "candidate_count": config.synthetic_cases_per_cluster,
            "literal_leakage_min_length": 24,
            "token_overlap_threshold": 0.95,
            "generation_set": dict(sorted(generation_set.items())),
        },
        algorithm_revision="stage-seven-dependency-v1",
    )


def _context(user_input: Any, prior: Any, tools: Any, runtime: Any) -> Dict[str, str]:
    return model_visible_context(
        {
            "user_input": _redact_text(_string(user_input)),
            "conversation_context": list(_redact_messages(prior) or []),
            "tool_calls": _redact_tool_calls(tools),
            "runtime": _redact_named_content(runtime),
        }
    )


def _case_group_id(case: Mapping[str, Any]) -> str:
    metadata = case.get("metadata")
    if isinstance(metadata, Mapping):
        group_id = _string(metadata.get("group_id"))
        if group_id:
            return group_id
    return _string(case.get("case_id"))


def _approved_case_for_release(
    case: Mapping[str, Any],
    *,
    asset_id: str,
    decision_id: str,
) -> Dict[str, Any]:
    """Attach release-local metadata to one explicitly approved derived case."""
    copied = dict(case)
    metadata = dict(copied.get("metadata") or {})
    metadata.update(
        {
            "dataset_version": asset_id,
            "review_status": "approved",
            "decision_id": decision_id,
        }
    )
    copied["metadata"] = metadata
    validate_fapo_case(copied)
    return copied


def _review_split_payloads(
    *,
    trusted: Sequence[Mapping[str, Any]],
    approved: Sequence[Mapping[str, Any]],
    held: Sequence[Mapping[str, Any]],
    families: Sequence[Mapping[str, Any]],
    asset_id: str,
    seed: int,
) -> Dict[str, List[Dict[str, Any]]]:
    """Publish trusted plus approved cases without crossing exact families."""
    validated_families = [validate_duplicate_family(row) for row in families]
    family_by_case: Dict[str, Dict[str, Any]] = {}
    for family in validated_families:
        for member in family["members"]:
            case_id = str(member["case_id"])
            if case_id in family_by_case:
                raise ReviewIntegrityError(f"case {case_id!r} appears in multiple duplicate families")
            family_by_case[case_id] = family
    all_cases = [*trusted, *approved]
    all_ids = [str(case["case_id"]) for case in all_cases]
    if len(set(all_ids)) != len(all_ids):
        raise ReviewIntegrityError("publication case_ids are not unique")
    if set(all_ids) - set(family_by_case):
        raise ReviewIntegrityError("publication case is absent from duplicate-family authority")
    held_ids = {str(row.get("case_id") or "") for row in held}
    standard: Dict[str, List[Dict[str, Any]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    regression: List[Dict[str, Any]] = []
    published_family_splits: Dict[str, str] = {}

    def publish(case: Mapping[str, Any], split: str) -> Dict[str, Any]:
        copied = dict(case)
        metadata = dict(copied.get("metadata") or {})
        family = family_by_case[str(copied["case_id"])]
        family_id = str(family["family_id"])
        previous = published_family_splits.setdefault(family_id, split)
        if previous != split:
            raise ReviewIntegrityError(f"duplicate family {family_id!r} crosses dataset splits")
        metadata.update(
            {
                "dataset_version": asset_id,
                "split": split,
                "split_group_id": str(family["split_group_id"]),
            }
        )
        copied["metadata"] = metadata
        validate_fapo_case(copied)
        return copied

    trusted_published: List[Dict[str, Any]] = []
    for case in trusted:
        case_id = str(case["case_id"])
        if case_id in held_ids:
            continue
        metadata = case.get("metadata")
        split = metadata.get("trusted_split") if isinstance(metadata, Mapping) else None
        if split not in {"train", "validation", "test", "regression"}:
            raise ReviewIntegrityError(f"trusted case {case_id!r} lacks an early split")
        published = publish(case, str(split))
        trusted_published.append(published)
        if split == "regression":
            regression.append(published)
        else:
            standard[str(split)].append(published)

    inferred_published: List[Dict[str, Any]] = []
    synthetic_published: List[Dict[str, Any]] = []
    for case in approved:
        case_id = str(case["case_id"])
        if case_id in held_ids:
            raise ReviewIntegrityError(f"held case {case_id!r} cannot be approved for publication")
        family = family_by_case[case_id]
        split = family["assigned_early_split"]
        if split == "regression":
            raise ReviewIntegrityError("a derived case attached to regression authority was not held")
        if split is None:
            value = _stable_fraction(str(family["split_group_id"]), seed)
            split = "train" if value < 0.6 else "validation" if value < 0.8 else "test"
        if split not in standard:
            raise ReviewIntegrityError("derived duplicate family split is invalid")
        published = publish(case, str(split))
        standard[str(split)].append(published)
        trust_tier = str(published["metadata"].get("trust_tier") or "")
        if trust_tier == INFERRED_FROM_TRUSTED_FEEDBACK:
            inferred_published.append(published)
        elif trust_tier == SYNTHETIC_FROM_TRUSTED_RUBRIC:
            synthetic_published.append(published)
        else:
            raise ReviewIntegrityError(f"approved case {case_id!r} has an unsupported trust tier")
    for rows in standard.values():
        rows.sort(key=lambda row: str(row["case_id"]))
    payloads = _provenance_split_payloads(
        standard,
        trusted_published,
        inferred_published,
        synthetic_published,
    )
    payloads["regression_trusted"] = sorted(
        regression,
        key=lambda row: str(row["case_id"]),
    )
    triage: List[Dict[str, Any]] = []
    for row in held:
        case = row.get("case")
        if not isinstance(case, Mapping):
            raise ReviewIntegrityError("held review case body is missing")
        copied = dict(case)
        metadata = dict(copied.get("metadata") or {})
        metadata["hold_reason"] = str(row.get("reason") or row.get("hold_reason") or "")
        copied["metadata"] = metadata
        validate_fapo_case(copied)
        triage.append(copied)
    payloads["triage_hold"] = sorted(
        triage,
        key=lambda row: str(row["case_id"]),
    )
    return payloads


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
    regression_groups = {_case_group_id(case) for case in regression_trusted}
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
        for case in _load_jsonl(layout.parent_snapshot / "parent_regression_trusted.jsonl")
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
    regression_groups = parent_regression | {_case_group_id(case) for case in regression_trusted}
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
            split = "train" if value < 0.6 else "validation" if value < 0.8 else "test"
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
        payloads[f"{split}_trusted"] = [row for row in rows if str(row["case_id"]) in trusted_ids]
        payloads[f"{split}_inferred"] = [row for row in rows if str(row["case_id"]) in inferred_ids]
        payloads[f"{split}_synthetic"] = [row for row in rows if str(row["case_id"]) in synthetic_ids]
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
    indexed: Dict[str, Dict[str, Any]] = {}
    positions: Dict[str, int] = {}
    for position, item in enumerate(items, start=1):
        if not isinstance(item, Mapping) or not item.get(identity_key):
            continue
        identity = str(item[identity_key])
        if identity in indexed:
            raise ValueError(
                f"Rubric response has duplicate {identity_key} {identity!r} "
                f"at item {positions[identity]} and item {position}"
            )
        indexed[identity] = dict(item)
        positions[identity] = position
    return indexed


def _unique_rows_by_key(
    rows: Sequence[Mapping[str, Any]],
    *,
    key: str,
    source: str,
) -> Dict[str, Dict[str, Any]]:
    """Index persisted rows without permitting silent identity overwrite."""
    indexed: Dict[str, Dict[str, Any]] = {}
    positions: Dict[str, int] = {}
    for position, row in enumerate(rows, start=1):
        identity = _string(row.get(key))
        if not identity:
            raise ValueError(f"{source} item {position} is missing {key}")
        if identity in indexed:
            raise ValueError(
                f"{source} has duplicate {key} {identity!r} at item "
                f"{positions[identity]} and item {position}"
            )
        indexed[identity] = dict(row)
        positions[identity] = position
    return indexed


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
        raise ValueError("rubric tool_expectations must be a JSON object, array, string, or null")
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
MESSAGE_STRUCTURE_FIELDS = frozenset({"conversation_context", "message", "messages"})
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
        prepared["conversation_context"] = _redact_messages(prepared["conversation_context"])
    if "tool_calls" in prepared:
        prepared["tool_calls"] = _redact_tool_calls(prepared["tool_calls"])
    if "episode" in prepared:
        prepared["episode"] = _redact_episode(prepared["episode"])
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
            if (key == "role" or field in PRESERVED_NAMED_FIELDS) and not _is_composite_value(nested):
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
            if (key in {"name", "tool"} or field in PRESERVED_NAMED_FIELDS) and not _is_composite_value(
                nested
            ):
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


def _redact_episode(value: Any) -> Any:
    """Redact episode content while preserving event ordering and links."""
    if not isinstance(value, Mapping):
        return _redact_value(value)
    episode = dict(value)
    events = episode.get("events")
    if not isinstance(events, list):
        return _redact_named_content(episode)
    redacted_events = []
    preserved_fields = {"sequence", "type", "role", "call_id", "name"}
    content_fields = {"content", "arguments", "result", "error"}
    for item in events:
        if not isinstance(item, Mapping):
            redacted_events.append(_redact_named_content(item))
            continue
        event = dict(item)
        for key, nested in tuple(event.items()):
            if key in preserved_fields and not _is_composite_value(nested):
                continue
            if key in content_fields:
                event[key] = _redact_value(nested)
            else:
                event[key] = _redact_named_content(nested)
        redacted_events.append(event)
    episode["events"] = redacted_events
    for key, nested in tuple(episode.items()):
        if key == "events":
            continue
        if key == "episode_id" and not _is_composite_value(nested):
            continue
        episode[key] = _redact_named_content(nested)
    return episode


def _redact_feedback(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    feedback = dict(value)
    for key, nested in tuple(feedback.items()):
        if key in {"rationale", "correction"}:
            feedback[key] = _redact_value(nested)
        elif key == "correctness_signals" and isinstance(nested, list):
            feedback[key] = redact_correctness_signals(
                nested,
                redact_content=_redact_value,
            )
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
            elif field == "name" and structural_descriptor and not _is_composite_value(item):
                redacted[key] = item
            elif field in PRESERVED_NAMED_FIELDS and not _is_composite_value(item):
                redacted[key] = item
            else:
                redacted[key] = _redact_named_content(
                    item,
                    structural_descriptor=(field in STRUCTURAL_DESCRIPTOR_FIELDS),
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
