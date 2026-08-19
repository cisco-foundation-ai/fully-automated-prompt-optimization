# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.datasets.intent_assets import IntentCluster, IntentMatch
from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets.models import (
    STAGE_COUNT_KEYS,
    EvaluationAssetConfig,
    PipelineStage,
)
from src.hephaestus.evaluation_assets.pipeline import (
    GUIDELINE_SYNTHESIS_PROMPT,
    EvaluationAssetPipeline,
    _build_labeling_queue,
    _compile_evaluation_guidelines,
    _normalize_feedback,
    _normalize_intent,
    _normalize_rubric,
    _rubric_from_guidelines,
)
from src.hephaestus.evaluation_assets.service import EvaluationAssetRunManager
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


class FakeEmbeddingProvider:
    model = "fake-embedding"

    def __init__(self):
        self.calls = 0

    def embed_texts(self, texts):
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


class MalformedEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, malformed_call: int):
        super().__init__()
        self.malformed_call = malformed_call

    def embed_texts(self, texts):
        self.calls += 1
        if self.calls == self.malformed_call:
            return [[0.0, 0.0] for _ in texts]
        return [[1.0, 0.0] for _ in texts]


class SecretFailingEmbeddingProvider(FakeEmbeddingProvider):
    def embed_texts(self, texts):
        raise RuntimeError(
            'sk-live-secret-token raw_response={"email":"private@example.com"}'
        )


class FakeRubricProvider:
    model = "fake-rubric"

    def __init__(self):
        self.synthetic_calls = 0
        self.feedback_record_ids = []
        self.calls = 0

    def generate_json(self, system_prompt, payload):
        self.calls += 1
        if "records" in payload:
            self.feedback_record_ids.extend(
                row["record_id"] for row in payload["records"]
            )
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer the request",
                        "confidence": 0.9,
                        "observations": [
                            {
                                "claim": "Answer the user's stated request.",
                                "evidence_type": "explicit_feedback",
                                "evidence_pointer": "feedback.rationale",
                                "polarity": row["feedback"]["polarity"],
                            }
                        ],
                        "requested_corrections": [],
                        "uncertainties": [],
                    }
                    for row in payload["records"]
                ]
            }
        if "evidence" in payload:
            return {
                "guidelines": [
                    {
                        "intent_label": "answer the request",
                        "description": "Answer requests within their stated scope.",
                        "route": payload["route"],
                        "source_record_ids": [
                            row["record_id"] for row in payload["evidence"]
                        ],
                        "confidence": 0.9,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": "Answer the user's stated request.",
                                "dimension": "task_success",
                                "severity": "critical",
                                "applicability": "always",
                                "scoring": "binary",
                                "evidence_required": False,
                                "evaluator": {
                                    "type": "llm_judge",
                                    "fallback": "human_review",
                                },
                            },
                            {
                                "kind": "prohibited",
                                "statement": "Change the requested scope.",
                                "dimension": "instruction_following",
                                "severity": "major",
                                "applicability": "always",
                                "scoring": "binary",
                                "evidence_required": False,
                                "evaluator": {
                                    "type": "llm_judge",
                                    "fallback": "human_review",
                                },
                            },
                        ],
                        "tool_expectations": {},
                        "reference_output": None,
                    }
                ]
            }
        if "synthetic evaluation input" in system_prompt:
            self.synthetic_calls += 1
            return {
                "cases": [
                    {
                        "cluster_id": row["cluster_id"],
                        "task_type": row["route"],
                        "user_input": (
                            f"Variation-{case_index + 1} request for "
                            f"{row['cluster_id']}"
                        ),
                        "conversation_context": [],
                    }
                    for row in payload["clusters"]
                    for case_index in range(row["case_count"])
                ]
            }
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer the request",
                    "confidence": 0.8,
                    "must": ["Answer the user's stated request."],
                    "must_not": ["Change the requested scope."],
                    "should": ["Be concise."],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }


class SecretFailingRubricProvider(FakeRubricProvider):
    def generate_json(self, system_prompt, payload):
        raise RuntimeError(
            'sk-live-secret-token raw_response={"email":"private@example.com"}'
        )


def test_normalization_preserves_structural_fields_and_redacts_content() -> None:
    """Schema structure survives while content-bearing PII is redacted."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": " record.owner@example.com ",
        "group_id": " group.owner@example.com ",
        "request_id": " request.owner@example.com ",
        "task_type": " task.owner@example.com ",
        "route": " route.owner@example.com ",
        "intent_label": " intent.owner@example.com ",
        "user_input": "Contact user@example.com from 192.0.2.1.",
        "assistant_output": "Reached assistant@example.com at 192.0.2.2.",
        "conversation_context": [
            {
                "role": " role.owner@example.com ",
                "content": "Earlier user@example.com at 192.0.2.3.",
                "metadata": {
                    "intent_label": "context.owner@example.com",
                    "note": "Escalate to context@example.com.",
                },
            }
        ],
        "tool_calls": [
            {
                "name": " lookup.owner@example.com ",
                "arguments": {
                    "address": "argument@example.com",
                    "nested": ["192.0.2.4"],
                },
                "result": {"owner": "result@example.com"},
                "error": "Tool error for error@example.com",
            }
        ],
        "runtime": {
            "model": " model.owner@example.com ",
            "unknown_leaf": "runtime-unknown@example.com",
            "request": {
                "content": "Runtime payload runtime@example.com",
                "model": " nested-model.owner@example.com ",
                "provider": " nested-provider.owner@example.com ",
                "route": " nested-route.owner@example.com ",
            },
            "nested_structures": {
                "messages": [
                    {
                        "role": " nested-role.owner@example.com ",
                        "content": "Nested message nested-message@example.com",
                        "metadata": {
                            "unknown_leaf": "nested-message-metadata@example.com"
                        },
                    }
                ],
                "tool_calls": [
                    {
                        "id": " nested-call.owner@example.com ",
                        "type": "function",
                        "function": {
                            "name": " nested-tool.owner@example.com ",
                            "arguments": {"email": "nested-argument@example.com"},
                        },
                        "metadata": {
                            "unknown_leaf": "nested-tool-metadata@example.com"
                        },
                    }
                ],
            },
        },
        "metadata": {
            "source_system": " source.owner@example.com ",
            "source_version": " source-version.owner@example.com ",
            "intent_label": " metadata.owner@example.com ",
            "unknown_leaf": "metadata-unknown@example.com",
            "nested": {"note": "Metadata metadata@example.com"},
        },
        "feedback": {
            "polarity": "negative",
            "source": "source.owner@example.com",
            "rationale": "Wrong for rationale@example.com",
            "correction": {"text": "Use correction@example.com"},
        },
    }

    feedback = _normalize_feedback(row)
    intent = _normalize_intent({key: value for key, value in row.items() if key != "feedback"})

    for normalized in (feedback, intent):
        assert normalized["schema_version"] == row["schema_version"]
        assert normalized["record_id"] == row["record_id"]
        assert normalized["group_id"] == row["group_id"]
        assert normalized["request_id"] == row["request_id"]
        assert normalized["task_type"] == row["task_type"]
        assert normalized["route"] == row["route"]
        assert normalized["intent_label"] == row["intent_label"]
        assert normalized["conversation_context"][0]["role"] == row[
            "conversation_context"
        ][0]["role"]
        assert normalized["tool_calls"][0]["name"] == row["tool_calls"][0]["name"]
        assert normalized["runtime"]["model"] == row["runtime"]["model"]
        assert normalized["runtime"]["request"]["model"] == row["runtime"][
            "request"
        ]["model"]
        assert normalized["runtime"]["request"]["provider"] == row[
            "runtime"
        ]["request"]["provider"]
        assert normalized["runtime"]["request"]["route"] == row["runtime"][
            "request"
        ]["route"]
        assert normalized["metadata"]["source_system"] == row["metadata"][
            "source_system"
        ]
        assert normalized["metadata"]["source_version"] == row["metadata"][
            "source_version"
        ]
        assert normalized["metadata"]["intent_label"] == row["metadata"][
            "intent_label"
        ]
        assert normalized["runtime"]["nested_structures"]["messages"][0][
            "role"
        ] == row["runtime"]["nested_structures"]["messages"][0]["role"]
        assert normalized["runtime"]["nested_structures"]["tool_calls"][0][
            "id"
        ] == row["runtime"]["nested_structures"]["tool_calls"][0]["id"]
        assert normalized["runtime"]["nested_structures"]["tool_calls"][0][
            "function"
        ]["name"] == row["runtime"]["nested_structures"]["tool_calls"][0][
            "function"
        ]["name"]
        serialized = json.dumps(normalized, sort_keys=True)
        for secret in (
            "user@example.com",
            "assistant@example.com",
            "context@example.com",
            "argument@example.com",
            "result@example.com",
            "error@example.com",
            "runtime@example.com",
            "metadata@example.com",
            "runtime-unknown@example.com",
            "metadata-unknown@example.com",
            "nested-message@example.com",
            "nested-message-metadata@example.com",
            "nested-argument@example.com",
            "nested-tool-metadata@example.com",
            "192.0.2.1",
            "192.0.2.2",
            "192.0.2.3",
            "192.0.2.4",
        ):
            assert secret not in serialized
    feedback_serialized = json.dumps(feedback, sort_keys=True)
    assert "rationale@example.com" not in feedback_serialized
    assert "correction@example.com" not in feedback_serialized


def test_normalization_defaults_preserve_exact_canonical_source_strings() -> None:
    """Omitted request and route fields inherit source strings without trimming."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": " exact-record-id ",
        "group_id": " exact-group-id ",
        "task_type": " exact-task-type ",
        "intent_label": " exact-intent-label ",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    feedback = _normalize_feedback(row)
    intent = _normalize_intent({key: value for key, value in row.items() if key != "feedback"})

    for normalized in (feedback, intent):
        assert normalized["request_id"] == " exact-record-id "
        assert normalized["route"] == " exact-task-type "


def test_prepare_inputs_rejects_normalized_duplicate_with_both_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A faulty normalizer collision reports both originating rows and IDs."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_extension_feedback(feedback, [" source-one ", " source-two "])
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    original = pipeline_module._normalize_feedback

    def collide(row):
        normalized = original(row)
        normalized["record_id"] = " canonical-collision "
        return normalized

    monkeypatch.setattr(pipeline_module, "_normalize_feedback", collide)

    with pytest.raises(
        ValueError,
        match=(
            r"normalized feedback.*' canonical-collision '.*"
            r"row 1.*' source-one '.*row 2.*' source-two '"
        ),
    ):
        pipeline._prepare_inputs()


@pytest.mark.parametrize(
    ("routes", "cluster_count", "message"),
    [
        (["route_a"], 2, "cannot exceed the number of unlabeled records"),
        (
            ["route_a", "route_b"],
            1,
            "must be at least the number of distinct effective routes",
        ),
    ],
)
def test_stage_one_rejects_infeasible_clustering_before_provider_calls(
    tmp_path: Path,
    routes: list[str],
    cluster_count: int,
    message: str,
) -> None:
    """Data-dependent clustering failures stop before paid provider work."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_unlabeled_routes(unlabeled, routes)
    rubric_provider = FakeRubricProvider()
    embedding_provider = FakeEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=cluster_count,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )

    with pytest.raises(ValueError, match=message):
        pipeline.run()

    state = pipeline.layout.load_state()
    assert state.current_stage == PipelineStage.RAW_INPUTS.value
    assert rubric_provider.calls == 0
    assert embedding_provider.calls == 0


def test_stage_one_accepts_one_cluster_per_record_and_effective_route(
    tmp_path: Path,
) -> None:
    """The exact feasibility boundary remains accepted in Stage 1."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_unlabeled_routes(unlabeled, ["route_a", "route_b"])
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=2),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )

    assert pipeline._validate_raw_inputs() == {
        "feedback_records": 1,
        "unlabeled_records": 2,
    }


@pytest.mark.parametrize(
    ("copied_input", "expected_detail"),
    [
        ("feedback", "missing required field 'group_id'"),
        ("unlabeled", "'conversation_context[0].content' is required"),
    ],
)
def test_stage_one_revalidates_each_copied_input_before_provider_calls(
    tmp_path: Path,
    copied_input: str,
    expected_detail: str,
) -> None:
    """A copied v1 contract violation fails Stage 1 with its exact location."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    rubric_provider = FakeRubricProvider()
    embedding_provider = FakeEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )
    copied_path = (
        pipeline.layout.feedback_path
        if copied_input == "feedback"
        else pipeline.layout.unlabeled_path
    )
    row = _read_test_jsonl(copied_path)[0]
    if copied_input == "feedback":
        del row["group_id"]
    else:
        row["conversation_context"] = [{"role": "user"}]
    copied_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    expected_error = f"{copied_path}:1: {expected_detail}"

    with pytest.raises(ValueError) as caught:
        pipeline.run()

    assert str(caught.value) == expected_error
    state = pipeline.layout.load_state()
    raw_stage = next(
        stage for stage in state.stages if stage.stage == PipelineStage.RAW_INPUTS.value
    )
    assert state.status == "failed"
    assert state.current_stage == PipelineStage.RAW_INPUTS.value
    assert state.error == expected_error
    assert raw_stage.status == "failed"
    assert raw_stage.message == expected_error
    assert rubric_provider.calls == 0
    assert embedding_provider.calls == 0


@pytest.mark.parametrize(
    ("malformed_call", "expected_stage"),
    [
        (1, PipelineStage.INTENT_CLUSTERING),
        (2, PipelineStage.COVERAGE_DECISIONS),
    ],
)
def test_pipeline_validates_injected_embedding_batches_at_every_stage(
    tmp_path: Path,
    malformed_call: int,
    expected_stage: PipelineStage,
) -> None:
    """Custom providers cannot bypass Stage 4 or Stage 5 vector validation."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    embedding_provider = MalformedEmbeddingProvider(malformed_call)
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=embedding_provider,
    )

    with pytest.raises(ValueError, match="embedding provider.*nonzero"):
        pipeline.run()

    state = pipeline.layout.load_state()
    assert state.current_stage == expected_stage.value
    assert embedding_provider.calls == malformed_call


@pytest.mark.parametrize(
    ("failure_kind", "expected_stage"),
    [
        ("rubric", PipelineStage.RUBRIC_EXTRACTION),
        ("embedding", PipelineStage.INTENT_CLUSTERING),
    ],
)
def test_provider_failure_persists_only_sanitized_causal_summary(
    tmp_path: Path,
    failure_kind: str,
    expected_stage: PipelineStage,
) -> None:
    """Provider payloads stay in the chained cause and out of artifacts."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    rubric_provider = (
        SecretFailingRubricProvider()
        if failure_kind == "rubric"
        else FakeRubricProvider()
    )
    embedding_provider = (
        SecretFailingEmbeddingProvider()
        if failure_kind == "embedding"
        else FakeEmbeddingProvider()
    )
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            rubric_model="safe-rubric-model",
            embedding_model="safe-embedding-model",
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )

    with pytest.raises(Exception) as caught:
        pipeline.run()

    assert caught.value.__class__.__name__ == "ProviderCallError"
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert "sk-live-secret-token" in str(caught.value.__cause__)
    persisted = (
        pipeline.layout.state_path.read_text(encoding="utf-8")
        + pipeline.layout.events_path.read_text(encoding="utf-8")
    )
    assert expected_stage.value in persisted
    assert "provider=openai" in persisted
    assert "model=safe-" in persisted
    assert "cause=RuntimeError" in persisted
    assert "summary=provider operation failed" in persisted
    assert "sk-live-secret-token" not in persisted
    assert "raw_response" not in persisted
    assert "private@example.com" not in persisted


def test_provider_failure_never_persists_dynamic_exception_class_name(
    tmp_path: Path,
) -> None:
    """Only fixed exception categories cross the persistence boundary."""
    secret_class_name = "SecretCredentialClass_A1B2C3"
    secret_exception = type(secret_class_name, (Exception,), {})

    class DynamicFailureProvider(FakeRubricProvider):
        def generate_json(self, system_prompt, payload):
            raise secret_exception("raw-secret-value")

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=DynamicFailureProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )

    with pytest.raises(Exception) as caught:
        pipeline.run()

    assert caught.value.__cause__.__class__.__name__ == secret_class_name
    assert "raw-secret-value" in str(caught.value.__cause__)
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in pipeline.layout.root.rglob("*")
        if path.is_file()
    )
    assert "cause=ProviderError" in persisted
    assert secret_class_name not in persisted
    assert "raw-secret-value" not in persisted


def test_rubric_normalization_accepts_list_form_tool_expectations() -> None:
    expectation = "Use the required search tool before answering." + ("x" * 80)

    rubric = _normalize_rubric(
        {
            "intent_label": "answer the request",
            "confidence": 0.9,
            "must": ["Answer the request."],
            "must_not": [],
            "should": [],
            "deterministic_checks": [],
            "tool_expectations": [expectation],
            "reference_output": None,
        },
        "record_id",
        "feedback-1",
        "human_feedback",
        "gpt-5.5",
    )

    assert rubric["tool_expectations"] == {"requirements": [expectation]}
    assert "tool_expectations" in GUIDELINE_SYNTHESIS_PROMPT


def test_guideline_compilation_preserves_provenance_and_evaluator_plan() -> None:
    evidence = [
        {
            "record_id": "feedback-1",
            "group_id": "group-1",
            "route": "task_route",
            "requested_corrections": [],
            "uncertainties": ["The required ordering is not established."],
        }
    ]
    candidates = [
        {
            "route": "task_route",
            "intent_label": "complete the task",
            "description": "Complete the requested task safely.",
            "source_record_ids": ["feedback-1"],
            "confidence": 0.9,
            "criteria": [
                {
                    "kind": "required",
                    "statement": "The requested state change is present.",
                    "source_record_ids": ["feedback-1"],
                    "dimension": "task_success",
                    "severity": "critical",
                    "applicability": "always",
                    "scoring": "binary",
                    "evidence_required": True,
                    "evaluator": {
                        "type": "state_check",
                        "fallback": "human_review",
                    },
                }
            ],
            "tool_expectations": {},
            "reference_output": None,
            "conflicts": [],
            "uncertainties": [],
        }
    ]

    guidelines = _compile_evaluation_guidelines(
        candidates,
        evidence,
        "gpt-5.5",
    )
    rubric = _rubric_from_guidelines("feedback-1", guidelines, "gpt-5.5")

    assert guidelines[0]["criteria"][0]["source_record_ids"] == ["feedback-1"]
    assert guidelines[0]["criteria"][0]["evaluator"]["type"] == "state_check"
    assert guidelines[0]["uncertainties"] == [
        "The required ordering is not established."
    ]
    assert rubric["deterministic_checks"][0]["criterion_id"].startswith(
        "criterion-"
    )


def test_evaluation_asset_optional_settings_have_safe_defaults() -> None:
    config = EvaluationAssetConfig(tenant_id="new_tenant")

    assert config.match_threshold == 0.6
    assert config.synthetic_coverage_enabled is False
    assert config.synthetic_cases_per_cluster == 1

    loaded = EvaluationAssetConfig.from_dict({"tenant_id": "new_tenant"})
    assert loaded.match_threshold == 0.6
    assert loaded.synthetic_coverage_enabled is False
    assert loaded.synthetic_cases_per_cluster == 1


def test_config_round_trip_distinguishes_missing_ratio_from_explicit_null() -> None:
    """A missing coverage ratio defaults while explicit null stays disabled."""
    missing = EvaluationAssetConfig.from_dict({"tenant_id": "new_tenant"})
    disabled = EvaluationAssetConfig.from_dict(
        {
            "tenant_id": "new_tenant",
            "max_unlabeled_to_trusted_ratio": None,
        }
    )

    assert missing.max_unlabeled_to_trusted_ratio == 20.0
    assert EvaluationAssetConfig.from_dict(
        missing.to_dict()
    ).max_unlabeled_to_trusted_ratio == 20.0
    assert disabled.max_unlabeled_to_trusted_ratio is None
    assert EvaluationAssetConfig.from_dict(
        disabled.to_dict()
    ).max_unlabeled_to_trusted_ratio is None


def test_layout_accepts_only_selected_tenant_source_jsonl(tmp_path: Path) -> None:
    """Create accepts ordinary selected-tenant source and dataset JSONL files."""
    tenants_root = tmp_path / "tenants"
    feedback = (
        tenants_root / "tenant_a" / "source_artifacts" / "feedback.jsonl"
    )
    unlabeled = tenants_root / "tenant_a" / "datasets" / "unlabeled.jsonl"
    feedback.parent.mkdir(parents=True)
    unlabeled.parent.mkdir(parents=True)
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )

    assert layout.feedback_path.read_bytes() == feedback.read_bytes()
    assert layout.unlabeled_path.read_bytes() == unlabeled.read_bytes()


@pytest.mark.parametrize(
    "source_kind",
    [
        "workspace_external",
        "other_tenant",
        "generated_dataset",
        "directory",
        "wrong_suffix",
        "symlink_escape",
    ],
)
def test_layout_rejects_unauthorized_sources_before_initializing(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """Create rejects every source outside the selected tenant input boundary."""
    tenants_root = tmp_path / "workspace" / "tenants"
    selected_sources = tenants_root / "tenant_a" / "source_artifacts"
    selected_sources.mkdir(parents=True)
    unlabeled = selected_sources / "unlabeled.jsonl"
    _write_extension_unlabeled(unlabeled, ["u1"])
    outside = tmp_path / "outside.jsonl"
    _write_extension_feedback(outside, ["f1"])

    if source_kind == "workspace_external":
        feedback = outside
    elif source_kind == "other_tenant":
        feedback = (
            tenants_root / "tenant_b" / "source_artifacts" / "feedback.jsonl"
        )
        feedback.parent.mkdir(parents=True)
        _write_extension_feedback(feedback, ["f1"])
    elif source_kind == "generated_dataset":
        feedback = (
            tenants_root
            / "tenant_a"
            / "datasets"
            / "evaluation_assets"
            / "v0"
            / "train.jsonl"
        )
        feedback.parent.mkdir(parents=True)
        _write_extension_feedback(feedback, ["f1"])
    elif source_kind == "directory":
        feedback = selected_sources / "directory.jsonl"
        feedback.mkdir()
    elif source_kind == "wrong_suffix":
        feedback = selected_sources / "feedback.json"
        _write_extension_feedback(feedback, ["f1"])
    else:
        feedback = selected_sources / "feedback.jsonl"
        feedback.symlink_to(outside)

    layout = EvaluationAssetLayout(tenants_root, "tenant_a", source_kind)

    with pytest.raises((OSError, ValueError)):
        layout.initialize(
            EvaluationAssetConfig(
                tenant_id="tenant_a",
                asset_id=source_kind,
            ),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_initialize_reports_source_file_and_row_before_creating_asset(
    tmp_path: Path,
) -> None:
    """Contract failures identify the original source row without side effects."""
    tenants_root = tmp_path / "tenants"
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    feedback.write_text('{"record_id":"f1"}\n', encoding="utf-8")
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(
        ValueError,
        match=r"feedback\.jsonl:1: missing required field 'schema_version'",
    ):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_layout_rejects_symlinked_tenant_source_root_escape(
    tmp_path: Path,
) -> None:
    """A source_artifacts directory symlink cannot authorize external files."""
    tenants_root = tmp_path / "workspace" / "tenants"
    tenant_root = tenants_root / "tenant_a"
    external = tmp_path / "external"
    tenant_root.mkdir(parents=True)
    external.mkdir()
    (tenant_root / "source_artifacts").symlink_to(external, target_is_directory=True)
    feedback = external / "feedback.jsonl"
    unlabeled = external / "unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(ValueError, match="selected tenant"):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_initialize_reports_source_file_and_row_for_malformed_json(
    tmp_path: Path,
) -> None:
    """Malformed source JSON identifies its original file and physical row."""
    tenants_root = tmp_path / "tenants"
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    feedback.write_text('{"record_id":\n', encoding="utf-8")
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(ValueError, match=r"feedback\.jsonl:1: invalid JSON"):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_extension_rejects_unauthorized_addition_before_initializing_child(
    tmp_path: Path,
) -> None:
    """Extension applies the same tenant source boundary before child writes."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    parent = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = parent.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    state.status = "completed"
    parent.save_state(state)
    other_feedback = (
        tenants_root / "tenant_b" / "source_artifacts" / "feedback.jsonl"
    )
    other_feedback.parent.mkdir(parents=True)
    _write_extension_feedback(other_feedback, ["f2"])
    child = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")

    with pytest.raises(ValueError):
        child.initialize_extension(
            parent,
            additional_feedback=other_feedback,
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_service_create_and_extend_share_tenant_source_boundary(
    tmp_path: Path,
) -> None:
    """The service delegates create and extend authorization to core layout."""
    workspace = tmp_path / "workspace"
    tenants_root = workspace / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    other_source = (
        tenants_root / "tenant_b" / "source_artifacts" / "other.jsonl"
    )
    other_source.parent.mkdir(parents=True)
    other_source.write_text('{"record_id":"other"}\n', encoding="utf-8")
    manager = EvaluationAssetRunManager(tenants_root)

    with pytest.raises(ValueError, match="selected tenant"):
        manager.start(
            EvaluationAssetConfig(
                tenant_id="tenant_a",
                asset_id="service-create",
                embedding_provider="tfidf",
                embedding_model="tfidf",
            ),
            other_source,
            unlabeled,
        )
    assert not (
        tenants_root / "tenant_a" / "evaluation_assets" / "service-create"
    ).exists()

    parent = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = parent.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    state.status = "completed"
    parent.save_state(state)
    with pytest.raises(ValueError, match="selected tenant"):
        manager.extend(
            "tenant_a",
            "v1",
            "service-extend",
            additional_feedback=other_source,
            additional_unlabeled=None,
            clustering_mode="keep",
        )
    assert not (
        tenants_root / "tenant_a" / "evaluation_assets" / "service-extend"
    ).exists()


def test_layout_resolves_existing_legacy_artifact_paths(tmp_path: Path) -> None:
    layout = EvaluationAssetLayout(tmp_path / "tenants", "legacy_tenant", "v1")
    for name in (
        "raw_inputs",
        "prepared_inputs",
        "decision_assets",
        "review_queues",
        "dataset_splits",
    ):
        (layout.root / name).mkdir(parents=True, exist_ok=True)

    assert layout.uses_stage_layout is False
    assert layout.artifact_path(
        "rubric_extraction",
        "feedback_rubrics.jsonl",
    ) == (layout.root / "decision_assets" / "feedback_rubrics.jsonl")
    assert layout.artifact_path(
        "rubric_extraction",
        "trusted_cases.jsonl",
    ) == (layout.root / "prepared_inputs" / "trusted_cases.jsonl")
    assert layout.artifact_path(
        "coverage_decisions",
        "review_queue/labeling_queue.jsonl",
    ) == (layout.root / "review_queues" / "labeling_queue.jsonl")


def test_layout_resolves_previous_stage_three_directory(tmp_path: Path) -> None:
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    previous = layout.stages_root / "03_rubric_extraction"
    previous.mkdir(parents=True)

    assert layout.stage_directory(PipelineStage.RUBRIC_EXTRACTION) == previous
    assert layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "feedback_rubrics.jsonl",
    ) == previous / "feedback_rubrics.jsonl"


def test_revise_config_invalidates_only_dependent_stages(tmp_path: Path) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=5,
            match_threshold=0.6,
        ),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages:
        stage_state.status = "completed"
        stage_state.message = "done"
        stage_state.started_at = "start"
        stage_state.completed_at = "end"
    state.status = "failed"
    state.error = "stopped"
    state.counts = {
        key: 1 for keys in STAGE_COUNT_KEYS.values() for key in keys
    }
    layout.save_state(state)
    stage_four_artifact = layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    )
    stage_five_artifact = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    stage_four_artifact.write_text("{}\n", encoding="utf-8")
    stage_five_artifact.write_text("{}\n", encoding="utf-8")
    layout.manifest_path.write_text("{}\n", encoding="utf-8")
    published_split = layout.published_datasets / "train.jsonl"
    published_split.parent.mkdir(parents=True)
    published_split.write_text("{}\n", encoding="utf-8")

    revision = layout.revise_config({"match_threshold": 0.2})

    revised_state = layout.load_state()
    assert revision["resume_from_stage"] == "coverage_decisions"
    assert revision["invalidated_from_stage"] == "coverage_decisions"
    assert revision["changed_fields"] == {
        "match_threshold": {"previous": 0.6, "new": 0.2}
    }
    assert layout.load_config().match_threshold == 0.2
    assert stage_four_artifact.exists()
    assert not stage_five_artifact.exists()
    assert not layout.manifest_path.exists()
    assert not layout.published_datasets.exists()
    assert [
        item.status for item in revised_state.stages[:4]
    ] == ["completed"] * 4
    assert [
        item.status for item in revised_state.stages[4:]
    ] == ["pending"] * 4
    assert "intent_clusters" in revised_state.counts
    assert "matched_clusters" not in revised_state.counts
    assert revised_state.status == "queued"
    assert revised_state.current_stage == "coverage_decisions"
    history = [
        json.loads(line)
        for line in layout.config_history_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert [entry["event"] for entry in history] == [
        "configuration_created",
        "configuration_updated",
    ]


def test_revise_config_derives_embedding_provider_and_restarts_stage_four(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages[:3]:
        stage_state.status = "completed"
    layout.save_state(state)

    revision = layout.revise_config({"embedding_model": "tfidf"})

    config = layout.load_config()
    assert config.embedding_model == "tfidf"
    assert config.embedding_provider == "tfidf"
    assert revision["resume_from_stage"] == "intent_clustering"
    assert revision["invalidated_from_stage"] == "intent_clustering"


def test_revise_config_with_unchanged_values_preserves_checkpoints(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    state.stages[0].status = "completed"
    layout.save_state(state)

    revision = layout.revise_config({"match_threshold": 0.6})

    assert revision == {
        "changed_fields": {},
        "invalidated_from_stage": None,
        "resume_from_stage": None,
    }
    assert layout.load_state().stages[0].status == "completed"
    assert layout.config_revision_summary()["count"] == 1


def test_revise_config_resumes_an_earlier_incomplete_stage(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages:
        stage_state.status = "completed"
    state.stages[4].status = "failed"
    state.status = "failed"
    state.current_stage = "coverage_decisions"
    layout.save_state(state)

    revision = layout.revise_config({"synthetic_coverage_enabled": True})

    assert revision["invalidated_from_stage"] == "synthetic_coverage"
    assert revision["resume_from_stage"] == "coverage_decisions"
    assert layout.load_state().current_stage == "coverage_decisions"


def test_extend_asset_keeps_clustering_and_extracts_only_new_rubrics(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tenants_root / "tenant_a" / "source_artifacts"
    inputs.mkdir(parents=True)
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_feedback = inputs / "added-feedback.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    _write_extension_feedback(added_feedback, ["u1"])
    parent_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    parent_pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            synthetic_coverage_enabled=False,
        ),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent_pipeline.run()
    parent_inventory = parent_layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_text(encoding="utf-8")
    parent_locations = _split_case_locations(parent_layout)

    child_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
    child_layout.initialize_extension(
        parent_layout,
        additional_feedback=added_feedback,
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    parent_layout.root.rename(tmp_path / "archived-parent")
    child_provider = FakeRubricProvider()
    child_state = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=child_provider,
        embedding_provider=FakeEmbeddingProvider(),
    ).run()

    assert child_state.status == "completed"
    assert child_provider.feedback_record_ids == ["u1"]
    assert child_layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_text(encoding="utf-8") == parent_inventory
    guidelines = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
    )
    assert {
        record_id
        for row in guidelines
        for record_id in row["source_record_ids"]
    } == {"f1", "u1"}
    inferred = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "inferred_cases.jsonl",
        )
    )
    assert "inferred-u1" not in {row["case_id"] for row in inferred}
    child_locations = _split_case_locations(child_layout)
    for case_id in ("feedback-f1", "inferred-u2"):
        assert child_locations[case_id] == parent_locations[case_id]
    lineage = json.loads(child_layout.lineage_path.read_text(encoding="utf-8"))
    assert lineage["parent_asset_id"] == "v1"
    assert lineage["clustering_mode"] == "keep"


def test_extend_asset_refreshes_clustering_for_new_unlabeled_records(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tenants_root / "tenant_a" / "source_artifacts"
    inputs.mkdir(parents=True)
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_unlabeled = inputs / "added-unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    _write_extension_unlabeled(added_unlabeled, ["u3"])
    parent = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent.run()
    parent_layout = parent.layout

    child_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
    child_layout.initialize_extension(
        parent_layout,
        additional_feedback=None,
        additional_unlabeled=added_unlabeled,
        clustering_mode="refresh",
        config_updates={"cluster_count": 2},
    )
    child_provider = FakeRubricProvider()
    state = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=child_provider,
        embedding_provider=FakeEmbeddingProvider(),
    ).run()

    assert state.status == "completed"
    assert child_provider.feedback_record_ids == []
    assert state.counts["unlabeled_records"] == 3
    assert state.counts["intent_clusters"] == 2
    lineage_rows = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.INTENT_CLUSTERING,
            "cluster_lineage.jsonl",
        )
    )
    assert lineage_rows
    assert {
        row["relationship"] for row in lineage_rows
    } <= {"continued", "split", "merged", "new", "retired"}


def test_extend_asset_rejects_unlabeled_additions_when_clustering_is_kept(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tenants_root / "tenant_a" / "source_artifacts"
    inputs.mkdir(parents=True)
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_unlabeled = inputs / "added-unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    _write_extension_unlabeled(added_unlabeled, ["u2"])
    parent = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent.run()

    with pytest.raises(ValueError, match="use refresh"):
        EvaluationAssetLayout(tenants_root, "tenant_a", "v2").initialize_extension(
            parent.layout,
            additional_feedback=None,
            additional_unlabeled=added_unlabeled,
            clustering_mode="keep",
        )


def test_labeling_queue_samples_only_clusters_needing_trusted_labels() -> None:
    clusters = [
        IntentCluster(
            cluster_id="route-a-001",
            route="route_a",
            record_ids=[f"u{index}" for index in range(1, 25)],
            representative_ids=["u1", "u2", "u3"],
            top_terms=["category", "alpha"],
        ),
        IntentCluster(
            cluster_id="route-b-001",
            route="route_b",
            record_ids=["u25"],
            representative_ids=["u25"],
            top_terms=["category", "beta"],
        ),
    ]
    matches = [
        IntentMatch(
            cluster_id="route-a-001",
            status="missing_or_weak_labels",
            score=0.2,
            reason="below threshold",
        ),
        IntentMatch(
            cluster_id="route-b-001",
            status="matched_trusted_intent",
            score=0.9,
        ),
    ]
    intent_rows = [
        {
            "record_id": f"u{index}",
            "user_input": f"request {index}",
            "route": "route_a" if index < 25 else "route_b",
        }
        for index in range(1, 26)
    ]

    queue = _build_labeling_queue(
        clusters,
        matches,
        intent_rows,
        sample_ratio=0.1,
        max_per_cluster=3,
    )

    assert [row["trace"]["record_id"] for row in queue] == ["u1", "u2", "u3"]
    assert {row["cluster_id"] for row in queue} == {"route-a-001"}
    assert {row["annotation_status"] for row in queue} == {"pending"}
    assert {row["samples_from_cluster"] for row in queue} == {3}


@pytest.mark.parametrize(
    (
        "synthetic_coverage_enabled",
        "synthetic_cases_per_cluster",
        "expected_synthetic_cases",
    ),
    [(False, 1, 0), (True, 2, 2)],
)
def test_pipeline_is_self_contained_and_writes_canonical_layout(
    tmp_path: Path,
    synthetic_coverage_enabled: bool,
    synthetic_cases_per_cluster: int,
    expected_synthetic_cases: int,
) -> None:
    tenants_root = tmp_path / "tenants"
    imports = tenants_root / "new_tenant" / "source_artifacts"
    imports.mkdir(parents=True)
    feedback = imports / "feedback.jsonl"
    unlabeled = imports / "unlabeled.jsonl"
    feedback.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema_version": "fapo-evaluation-input-v1",
                    "record_id": f"f{index}",
                    "group_id": (
                        "feedback-thread"
                        if index == 1
                        else f"feedback-thread-{index}"
                    ),
                    "task_type": "answer",
                    "user_input": f"Apply requirement {index}",
                    "assistant_output": "Applied an alternative condition",
                    "conversation_context": [],
                    "tool_calls": [],
                    "runtime": {},
                    "metadata": {},
                    "feedback": {
                        "polarity": "negative",
                        "rationale": "The required condition was not satisfied",
                    },
                }
            )
            for index in range(1, 11)
        )
        + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema_version": "fapo-evaluation-input-v1",
                    "record_id": f"u{index}",
                    "group_id": (
                        "feedback-thread"
                        if index == 1
                        else f"feedback-thread-{index}"
                    ),
                    "task_type": "answer",
                    "user_input": f"Answer request {index}",
                    "conversation_context": [],
                    "tool_calls": [],
                    "runtime": {},
                    "metadata": {},
                }
            )
            for index in range(1, 4)
        )
        + "\n",
        encoding="utf-8",
    )
    config = EvaluationAssetConfig(
        tenant_id="new_tenant",
        asset_id="v1",
        cluster_count=1,
        rubric_model="fake-rubric",
        embedding_model="fake-embedding",
        synthetic_coverage_enabled=synthetic_coverage_enabled,
        synthetic_cases_per_cluster=synthetic_cases_per_cluster,
    )
    rubric_provider = FakeRubricProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        config,
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=FakeEmbeddingProvider(),
    )

    feedback.unlink()
    unlabeled.unlink()
    state = pipeline.run()
    layout = pipeline.layout

    assert state.status == "completed"
    assert all(stage.status == "completed" for stage in state.stages)
    assert layout.feedback_path.exists()
    assert layout.unlabeled_path.exists()
    assert layout.artifact_path(
        "prepared_inputs",
        "normalized_feedback.jsonl",
    ).exists()
    assert layout.artifact_path(
        "coverage_decisions",
        "intent_matches.jsonl",
    ).exists()
    assert layout.artifact_path(
        "coverage_decisions",
        "review_queue/labeling_queue.jsonl",
    ).exists()
    assert layout.artifact_path("dataset_splits", "train.jsonl").exists()
    assert layout.manifest_path.exists()
    for split_name in (
        "train",
        "validation",
        "test",
        "regression_trusted",
    ):
        stage_split = layout.artifact_path(
            "dataset_splits",
            f"{split_name}.jsonl",
        )
        published_split = layout.published_datasets / f"{split_name}.jsonl"
        assert published_split.read_bytes() == stage_split.read_bytes()
    assert (layout.root / "stages" / "01_raw_inputs").is_dir()
    assert (layout.root / "stages" / "03_evaluation_guidelines").is_dir()
    assert not (layout.root / "stages" / "03_rubric_extraction").exists()
    assert not (layout.root / "raw_inputs").exists()

    prepared_feedback = json.loads(
        layout.artifact_path(
            "prepared_inputs",
            "normalized_feedback.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    prepared_intent = json.loads(
        layout.artifact_path(
            "prepared_inputs",
            "intent_records.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    feedback_evidence = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "feedback_evidence.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    evaluation_guideline = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "evaluation_guidelines.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    trusted_case = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "trusted_cases.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    inferred_rubric = json.loads(
        layout.artifact_path(
            "label_inference",
            "inferred_unlabeled_cluster_rubrics.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    dataset_manifest = json.loads(
        layout.artifact_path(
            "dataset_splits",
            "dataset_manifest.json",
        ).read_text(encoding="utf-8")
    )

    assert prepared_feedback["record_id"] == "f1"
    assert prepared_feedback["group_id"] == "feedback-thread"
    assert prepared_feedback["schema_version"] == "fapo-evaluation-input-v1"
    assert "feedback_id" not in prepared_feedback
    assert "thread_id" not in prepared_feedback
    assert prepared_intent["record_id"] == "u1"
    assert prepared_intent["group_id"] == "feedback-thread"
    assert prepared_intent["schema_version"] == "fapo-evaluation-input-v1"
    assert "feedback_id" not in prepared_intent
    assert "thread_id" not in prepared_intent
    assert feedback_evidence["record_id"] == "f1"
    assert "feedback_id" not in feedback_evidence
    assert set(evaluation_guideline["source_record_ids"]) == {
        f"f{index}" for index in range(1, 11)
    }
    assert evaluation_guideline["calibration_status"] == "uncalibrated"
    assert evaluation_guideline["criteria"][0]["evaluator"]["type"] == "llm_judge"
    assert trusted_case["metadata"]["group_id"] == "feedback-thread"
    assert trusted_case["metadata"]["request_id"] == "f1"
    assert "review_status" not in trusted_case["metadata"]
    assert "thread_group" not in trusted_case["metadata"]
    assert "request_group" not in trusted_case["metadata"]
    assert trusted_case["expected"]["evaluation_guideline_ids"] == [
        evaluation_guideline["guideline_id"]
    ]
    assert inferred_rubric["review_status"] == "review_required"
    assert (
        dataset_manifest["review_policy"]["evaluation_guidelines"]
        == "active_from_trusted_evidence"
    )
    assert dataset_manifest["review_policy"]["guideline_calibration"] == "uncalibrated"
    assert dataset_manifest["coverage"]["match_threshold"] == 0.6
    assert dataset_manifest["evaluation_guidelines"] == {
        "schema_version": "fapo-evaluation-guideline-v1",
        "count": 1,
        "activation_status": "active_from_trusted_evidence",
        "calibration_status": "uncalibrated",
    }
    assert dataset_manifest["coverage"]["labeling_queue"] == {
        "statuses": [
            "needs_more_trusted_examples",
            "missing_or_weak_labels",
        ],
        "sample_ratio": 0.1,
        "minimum_per_cluster": 1,
        "maximum_per_cluster": 3,
        "selection": "deterministic_centroid_nearest",
    }
    assert dataset_manifest["synthetic_coverage"] == {
        "enabled": synthetic_coverage_enabled,
        "cases_per_cluster": synthetic_cases_per_cluster,
    }
    assert dataset_manifest["regression_gate"] == {
        "source": "trusted_feedback",
        "fraction": 0.2,
        "selection": "deterministic_group_safe_random",
        "seed": 42,
    }
    assert dataset_manifest["published_datasets"] == {
        "directory": "datasets/evaluation_assets/v1",
        "files": {
            "train": "datasets/evaluation_assets/v1/train.jsonl",
            "validation": "datasets/evaluation_assets/v1/validation.jsonl",
            "test": "datasets/evaluation_assets/v1/test.jsonl",
            "regression_trusted": (
                "datasets/evaluation_assets/v1/regression_trusted.jsonl"
            ),
        },
    }
    assert (
        dataset_manifest["review_policy"]["regression_gate"]
        == "automatic_trusted_feedback_holdout"
    )
    assert (
        dataset_manifest["review_policy"]["coverage_labeling_queue"]
        == "human_label_required"
    )

    synthetic_candidates = [
        json.loads(line)
        for line in layout.artifact_path(
            "synthetic_coverage",
            "synthetic_candidates.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    synthetic_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "synthetic_coverage",
            "synthetic_cases.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(synthetic_candidates) == expected_synthetic_cases
    assert len(synthetic_cases) == expected_synthetic_cases
    assert len({row["case_id"] for row in synthetic_candidates}) == len(
        synthetic_candidates
    )
    assert rubric_provider.synthetic_calls == (
        1 if synthetic_coverage_enabled else 0
    )

    regression_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "dataset_splits",
            "regression_trusted.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    standard_trusted_cases = [
        json.loads(line)
        for name in ("train_trusted", "validation_trusted", "test_trusted")
        for line in layout.artifact_path(
            "dataset_splits",
            f"{name}.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(regression_cases) == 2
    assert len(standard_trusted_cases) == 8
    assert {
        row["case_id"] for row in regression_cases
    }.isdisjoint(row["case_id"] for row in standard_trusted_cases)
    assert {
        row["metadata"]["group_id"] for row in regression_cases
    }.isdisjoint(
        row["metadata"]["group_id"] for row in standard_trusted_cases
    )
    assert state.counts["regression_trusted_cases"] == 2

    combined_splits = {
        name: [
            json.loads(line)
            for line in layout.artifact_path(
                "dataset_splits",
                f"{name}.jsonl",
            ).read_text(encoding="utf-8").splitlines()
        ]
        for name in ("train", "validation", "test")
    }
    split_groups = {
        name: {row["metadata"]["group_id"] for row in rows}
        for name, rows in combined_splits.items()
    }
    assert split_groups["train"].isdisjoint(split_groups["validation"])
    assert split_groups["train"].isdisjoint(split_groups["test"])
    assert split_groups["validation"].isdisjoint(split_groups["test"])
    regression_groups = {
        row["metadata"]["group_id"] for row in regression_cases
    }
    assert all(
        regression_groups.isdisjoint(groups)
        for groups in split_groups.values()
    )

    triage_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "dataset_splits",
            "triage_hold.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert all(
        row["metadata"]["group_id"] in regression_groups
        and row["metadata"]["hold_reason"]
        == "group_id_reserved_for_regression"
        for row in triage_cases
    )
    case_locations = {
        row["case_id"]: split
        for split, rows in {
            **combined_splits,
            "regression": regression_cases,
            "triage": triage_cases,
        }.items()
        for row in rows
    }
    for index in range(1, 4):
        trusted_location = case_locations[f"feedback-f{index}"]
        inferred_location = case_locations[f"inferred-u{index}"]
        if trusted_location == "regression":
            assert inferred_location == "triage"
        else:
            assert inferred_location == trusted_location
    assert state.counts["triage_hold_cases"] == len(triage_cases)


def test_layout_rejects_unsafe_tenant_and_asset_names(tmp_path: Path) -> None:
    for tenant_id, asset_id in (("../escape", "v1"), ("tenant", "../../asset")):
        try:
            EvaluationAssetLayout(tmp_path / "tenants", tenant_id, asset_id)
        except ValueError:
            continue
        raise AssertionError("unsafe evaluation asset path was accepted")


def _write_extension_feedback(path: Path, record_ids: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": record_id,
            "group_id": f"group-{record_id}",
            "task_type": "answer",
            "route": "route_a",
            "user_input": f"Request {record_id}",
            "assistant_output": "Previous response",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
            "feedback": {
                "polarity": "positive",
                "rationale": "The response satisfied the request.",
            },
        }
        for record_id in record_ids
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_extension_unlabeled(path: Path, record_ids: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": record_id,
            "group_id": f"group-{record_id}",
            "task_type": "answer",
            "route": "route_a",
            "user_input": f"Request {record_id}",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
        }
        for record_id in record_ids
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_unlabeled_routes(path: Path, routes: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": f"u{index}",
            "group_id": f"group-u{index}",
            "task_type": route,
            "route": route if index % 2 else None,
            "user_input": f"Request u{index}",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
        }
        for index, route in enumerate(routes, start=1)
    ]
    for row in rows:
        if row["route"] is None:
            del row["route"]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_minimal_input_pair(
    tenants_root: Path,
    tenant_id: str,
) -> tuple[Path, Path]:
    source_root = tenants_root / tenant_id / "source_artifacts"
    source_root.mkdir(parents=True, exist_ok=True)
    feedback = source_root / "feedback.jsonl"
    unlabeled = source_root / "unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    return feedback, unlabeled


def _read_test_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _split_case_locations(layout: EvaluationAssetLayout) -> dict[str, str]:
    locations = {}
    for split in ("train", "validation", "test", "regression_trusted"):
        for row in _read_test_jsonl(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
        ):
            locations[row["case_id"]] = split
    return locations
