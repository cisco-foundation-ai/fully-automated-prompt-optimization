# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for allowlisted Evaluation Asset Studio build provenance."""

from __future__ import annotations

import inspect
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.hephaestus.datasets.embedding_providers import OpenAIEmbeddingProvider
from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.evaluation_assets import control_jsonl as control_jsonl_module
from src.hephaestus.evaluation_assets import provenance as provenance_module
from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig, PipelineStage
from src.hephaestus.evaluation_assets.pipeline import _stage_algorithms, _stage_seeds
from src.hephaestus.evaluation_assets.provenance import (
    PROMPT_REVISIONS,
    SOURCE_FIXED_MEMBERS,
    build_provenance,
    build_provider_call,
    canonical_sha256,
    collect_git_evidence,
    declared_source_dependencies,
    not_applicable,
    provider_settings,
    sanitize_call_metadata,
    unavailable,
    validate_build_provenance,
    validate_provider_calls,
    working_source_identity,
)


def _source_tree(root: Path) -> None:
    for relative in SOURCE_FIXED_MEMBERS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source:{relative}\n", encoding="utf-8")


def _native_inputs(
    *,
    include_review: bool = True,
) -> dict[str, dict[str, object]]:
    inputs = {
        name: {
            "path": f"stages/01_raw_inputs/{name}.jsonl",
            "bytes": 10,
            "rows": 1,
            "sha256": digest * 64,
        }
        for name, digest in (("labeled_feedback", "a"), ("unlabeled", "b"))
    }
    if include_review:
        inputs["review_snapshot"] = {
            "path": "stages/08_dataset_splits/review_snapshot.json",
            "bytes": 10,
            "rows": 1,
            "sha256": "c" * 64,
        }
    return inputs


def _native_config() -> dict[str, object]:
    return EvaluationAssetConfig(
        tenant_id="tenant",
        asset_id="asset",
        rubric_provider="custom",
        rubric_model="rubric-model",
        embedding_provider="custom",
        embedding_model="embedding-model",
    ).to_dict()


def _native_providers() -> dict[str, dict[str, object]]:
    marker = unavailable("provider_does_not_expose_field")
    return {
        "rubric": {
            "provider": "custom",
            "model": "rubric-model",
            "source": "injected",
            "interface": "generate_json-v1",
            "settings": {
                "timeout_seconds": marker,
                "max_retries": marker,
                "retry_backoff_seconds": marker,
                "pipeline_batch_size": 3,
                "max_output_tokens": marker,
                "temperature": marker,
                "response_format": marker,
                "seed": marker,
            },
        },
        "embedding": {
            "provider": "custom",
            "model": "embedding-model",
            "source": "injected",
            "interface": "embed_texts-v1",
            "settings": {
                "timeout_seconds": marker,
                "max_retries": marker,
                "retry_backoff_seconds": marker,
                "provider_batch_size": marker,
                "response_format": marker,
                "seed": marker,
            },
        },
    }


def _default_config() -> dict[str, object]:
    return EvaluationAssetConfig(tenant_id="tenant", asset_id="asset").to_dict()


def _default_providers(config: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        "rubric": provider_settings(
            OpenAIRubricProvider(
                model=str(config["rubric_model"]),
                max_output_tokens=16384,
            ),
            role="rubric",
            identity={
                "provider": str(config["rubric_provider"]),
                "model": str(config["rubric_model"]),
                "source": "default",
            },
            pipeline_batch_size=int(config["batch_size"]),
        ),
        "embedding": provider_settings(
            OpenAIEmbeddingProvider(model=str(config["embedding_model"])),
            role="embedding",
            identity={
                "provider": str(config["embedding_provider"]),
                "model": str(config["embedding_model"]),
                "source": "default",
            },
            pipeline_batch_size=int(config["batch_size"]),
        ),
    }


def _native_prompts(suffix: str = "") -> dict[str, str]:
    return {name: f"{name} prompt {suffix}" for name in PROMPT_REVISIONS}


def _native_seeds() -> dict[str, object]:
    marker = not_applicable("provider_does_not_use_sampling")
    return {
        "split": 42,
        "rubric_sampling": marker,
        "embedding_sampling": marker,
    }


def _native_algorithms(*, extension: bool = False) -> dict[str, object]:
    return provenance_module.build_algorithm_inventory(
        {"embedding_provider": "custom"},
        extension=extension,
    )


def _historical_source(
    source: dict[str, object],
    *,
    members: tuple[str, ...],
) -> dict[str, object]:
    """Project a current source identity onto one frozen historical inventory."""
    historical = json.loads(json.dumps(source))
    historical["members"] = [
        row for row in historical["members"] if row["path"] in members
    ]
    historical["fingerprint"] = canonical_sha256(historical["members"])
    return historical


def _parent_release() -> dict[str, str]:
    return {
        "stage_8_receipt_sha256": "1" * 64,
        "released_state_sha256": "2" * 64,
        "source_lineage_sha256": "3" * 64,
        "release_pointer_sha256": "4" * 64,
        "generation_id": f"sha256-{'5' * 64}",
        "generation_manifest_sha256": "6" * 64,
        "build_provenance_sha256": "7" * 64,
        "build_fingerprint": "8" * 64,
    }


def test_working_source_fingerprint_changes_for_every_declared_member(
    tmp_path: Path,
) -> None:
    """Changing any declared dependency changes its source fingerprint."""
    _source_tree(tmp_path)
    members = declared_source_dependencies(tmp_path)
    baseline = working_source_identity(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in members] == sorted(
        {
            *(str(path) for path in SOURCE_FIXED_MEMBERS),
        }
    )
    for path in members:
        previous = path.read_bytes()
        path.write_bytes(previous + b"changed\n")
        assert (
            working_source_identity(tmp_path)["fingerprint"]
            != baseline["fingerprint"]
        )
        path.write_bytes(previous)


@pytest.mark.parametrize("kind", ["missing", "symlink", "directory"])
def test_declared_source_inventory_fails_closed_for_unsafe_members(
    tmp_path: Path,
    kind: str,
) -> None:
    """Missing, symlinked, and non-file fixed dependencies are rejected."""
    _source_tree(tmp_path)
    target = tmp_path / SOURCE_FIXED_MEMBERS[0]
    target.unlink()
    if kind == "symlink":
        outside = tmp_path / "outside.py"
        outside.write_text("outside\n", encoding="utf-8")
        target.symlink_to(outside)
    elif kind == "directory":
        target.mkdir()

    with pytest.raises(ValueError, match="declared source dependency"):
        declared_source_dependencies(tmp_path)


def test_git_evidence_distinguishes_clean_dependency_and_unrelated_dirt(
    tmp_path: Path,
) -> None:
    """Git audit reports repository and dependency dirt independently."""
    if shutil.which("git") is None:
        pytest.skip("git is unavailable")
    _source_tree(tmp_path)
    unrelated = tmp_path / "README.md"
    unrelated.write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "test",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    clean = collect_git_evidence(tmp_path)
    assert clean["repository_dirty"] is False
    assert clean["dependency_set_dirty"] is False
    assert len(clean["commit"]) == 40
    assert len(clean["committed_tree"]) == 40

    unrelated.write_text("dirty\n", encoding="utf-8")
    unrelated_dirty = collect_git_evidence(tmp_path)
    assert unrelated_dirty["repository_dirty"] is True
    assert unrelated_dirty["dependency_set_dirty"] is False

    member = declared_source_dependencies(tmp_path)[0]
    member.write_text("dependency dirty\n", encoding="utf-8")
    dependency_dirty = collect_git_evidence(tmp_path)
    assert dependency_dirty["repository_dirty"] is True
    assert dependency_dirty["dependency_set_dirty"] is True


def test_non_git_evidence_uses_explicit_unavailable_markers(tmp_path: Path) -> None:
    """Non-Git source retains fingerprint authority with explicit audit gaps."""
    _source_tree(tmp_path)

    evidence = collect_git_evidence(tmp_path)

    marker = unavailable("not_a_git_worktree")
    assert evidence == {
        "commit": marker,
        "committed_tree": marker,
        "repository_dirty": marker,
        "dependency_set_dirty": marker,
    }
    assert working_source_identity(tmp_path)["fingerprint"]


def test_git_runner_is_bounded_and_never_invokes_a_shell() -> None:
    """Git audit collection uses an explicit bounded-output no-shell runner."""
    source = inspect.getsource(provenance_module._run_git)

    assert "subprocess.Popen" in source
    assert "shell=False" in source
    assert "max_output_bytes" in source


def test_metadata_sanitizer_keeps_only_allowlisted_scalar_transport_facts() -> None:
    """Arbitrary provider payloads, headers, and secrets never enter call metadata."""
    secret = "sk-secret-canary"
    sanitized = sanitize_call_metadata(
        [
            {
                "transport_ordinal": 1,
                "response_id": "response-1",
                "request_id": "request-1",
                "model": "model-revision",
                "system_fingerprint": "fingerprint-1",
                "usage": {
                    "input_tokens": 3,
                    "output_tokens": 4,
                    "total_tokens": 7,
                    "secret": secret,
                },
                "retry_count": 2,
                "headers": {"authorization": secret},
                "response": {"body": secret},
            }
        ]
    )

    assert sanitized == [
        {
            "transport_ordinal": 1,
            "response_id": "response-1",
            "request_id": "request-1",
            "model": "model-revision",
            "system_fingerprint": "fingerprint-1",
            "usage": {
                "input_tokens": 3,
                "output_tokens": 4,
                "total_tokens": 7,
            },
            "retry_count": 2,
        }
    ]
    assert secret not in repr(sanitized)
    assert not_applicable("stage_made_no_provider_calls") == {
        "status": "not_applicable",
        "reason": "stage_made_no_provider_calls",
    }


def test_build_provenance_has_exact_schema_and_body_free_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit-only facts cannot perturb identity and protected bodies never persist."""
    _source_tree(tmp_path)
    secret = "sk-build-provenance-canary"
    call = build_provider_call(
        stage="rubric_extraction",
        ordinal=1,
        provider_role="rubric",
        provider="custom",
        model="rubric-model",
        request={
            "protected_prompt": secret,
            "settings": _native_providers()["rubric"]["settings"],
        },
        response={"protected_response": secret},
        metadata=None,
    )
    arguments = {
        "repository_root": tmp_path,
        "resolved_configuration": _native_config(),
        "copied_inputs": _native_inputs(),
        "lineage": None,
        "providers": _native_providers(),
        "prompt_values": _native_prompts(secret),
        "calls": [call],
        "seeds": _native_seeds(),
        "algorithms": _native_algorithms(),
        "lineage_files": None,
    }
    monkeypatch.setattr(
        provenance_module,
        "collect_git_evidence",
        lambda root: {
            "commit": "1" * 40,
            "committed_tree": "2" * 40,
            "repository_dirty": False,
            "dependency_set_dirty": False,
        },
    )
    first = build_provenance(**arguments, created_at="2026-08-20T00:00:00+00:00")
    validate_build_provenance(first)

    assert set(first) == {
        "schema_version",
        "identity",
        "identity_sha256",
        "audit",
        "created_at",
    }
    assert set(first["identity"]) == {
        "schema_version",
        "hash_algorithm",
        "resolved_configuration",
        "source",
        "runtime_dependencies",
        "inputs",
        "lineage",
        "providers",
        "prompts",
        "calls",
        "seeds",
        "algorithms",
    }
    assert first["identity_sha256"] == canonical_sha256(first["identity"])
    assert secret not in repr(first)

    monkeypatch.setattr(
        provenance_module,
        "collect_git_evidence",
        lambda root: {
            "commit": "3" * 40,
            "committed_tree": "4" * 40,
            "repository_dirty": True,
            "dependency_set_dirty": False,
        },
    )
    audit_changed = build_provenance(
        **arguments,
        created_at="2026-08-20T00:00:01+00:00",
    )
    assert audit_changed["identity"] == first["identity"]
    assert audit_changed["identity_sha256"] == first["identity_sha256"]
    assert audit_changed != first

    dependency = declared_source_dependencies(tmp_path)[0]
    dependency.write_bytes(dependency.read_bytes() + b"mutation\n")
    source_changed = build_provenance(
        **arguments,
        created_at="2026-08-20T00:00:02+00:00",
    )
    assert source_changed["identity_sha256"] != first["identity_sha256"]

    review_changed_arguments = dict(arguments)
    review_changed_inputs = json.loads(json.dumps(arguments["copied_inputs"]))
    review_changed_inputs["review_snapshot"]["sha256"] = "d" * 64
    review_changed_arguments["copied_inputs"] = review_changed_inputs
    review_changed = build_provenance(
        **review_changed_arguments,
        created_at="2026-08-20T00:00:03+00:00",
    )
    assert review_changed["identity_sha256"] != source_changed["identity_sha256"]


@pytest.mark.parametrize(
    "corruption",
    [
        "outer_extra",
        "identity_extra",
        "identity_hash",
        "audit_extra",
        "timestamp",
        "config_nested",
        "source_member",
        "git_nested",
        "hybrid_profile",
    ],
)
def test_build_provenance_validator_rejects_schema_corruption(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Full provenance has an exact outer, identity, audit, and timestamp schema."""
    _source_tree(tmp_path)
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    candidate = json.loads(json.dumps(payload))
    if corruption == "outer_extra":
        candidate["extra"] = True
    elif corruption == "identity_extra":
        candidate["identity"]["extra"] = True
        candidate["identity_sha256"] = canonical_sha256(candidate["identity"])
    elif corruption == "identity_hash":
        candidate["identity_sha256"] = "0" * 64
    elif corruption == "audit_extra":
        candidate["audit"]["extra"] = True
    elif corruption == "config_nested":
        candidate["identity"]["resolved_configuration"]["sha256"] = "0" * 64
        candidate["identity_sha256"] = canonical_sha256(candidate["identity"])
    elif corruption == "source_member":
        candidate["identity"]["source"]["members"][0]["sha256"] = "0" * 64
        candidate["identity_sha256"] = canonical_sha256(candidate["identity"])
    elif corruption == "git_nested":
        candidate["audit"]["git"]["extra"] = True
    elif corruption == "hybrid_profile":
        candidate["identity"]["source"] = unavailable(
            "legacy_checkpoint_predates_provenance"
        )
        candidate["identity"]["providers"] = {}
        candidate["identity"]["prompts"] = unavailable(
            "legacy_checkpoint_predates_provenance"
        )
        candidate["identity"]["calls"] = unavailable(
            "legacy_checkpoint_predates_provenance"
        )
        candidate["identity"]["lineage"] = {"parent_asset_id": "anything"}
        candidate["identity_sha256"] = canonical_sha256(candidate["identity"])
    else:
        candidate["created_at"] = "not-a-canonical-timestamp"

    with pytest.raises(ValueError, match="provenance"):
        validate_build_provenance(candidate)


@pytest.mark.parametrize(
    "corruption",
    [
        "source_marker",
        "source_member_missing",
        "provider_markers",
        "seed_type",
        "algorithm_markers",
        "lineage_marker",
    ],
)
def test_native_build_provenance_rejects_rehashed_profile_substitutions(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Native releases cannot rehash legacy or loosely typed provenance facts."""
    _source_tree(tmp_path)
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    candidate = json.loads(json.dumps(payload))
    identity = candidate["identity"]
    if corruption == "source_marker":
        identity["source"] = unavailable("git_command_unavailable")
    elif corruption == "source_member_missing":
        identity["source"]["members"].pop()
        identity["source"]["fingerprint"] = canonical_sha256(
            identity["source"]["members"]
        )
    elif corruption == "provider_markers":
        marker = unavailable("legacy_checkpoint_predates_provenance")
        identity["providers"] = {"rubric": marker, "embedding": marker}
    elif corruption == "seed_type":
        identity["seeds"]["split"] = "42"
    elif corruption == "algorithm_markers":
        marker = unavailable("legacy_checkpoint_predates_provenance")
        identity["algorithms"] = {
            stage.value: marker for stage in PipelineStage
        }
    else:
        marker = not_applicable("provider_does_not_use_sampling")
        identity["lineage"] = marker
        candidate["audit"]["lineage_files"] = marker
    candidate["identity_sha256"] = canonical_sha256(identity)

    with pytest.raises(ValueError, match="provenance"):
        validate_build_provenance(candidate)


def test_native_extension_provenance_binds_identity_and_audit_dependencies(
    tmp_path: Path,
) -> None:
    """Extension identity must exactly bind its audit file dependencies."""
    _source_tree(tmp_path)
    lineage = {
        "parent_asset_id": "v1",
        "clustering_mode": "keep",
        "added_labeled_record_ids": [],
        "added_unlabeled_record_ids": [],
        "parent_input_counts": {"labeled": 1, "unlabeled": 1},
        "extended_input_counts": {"labeled": 1, "unlabeled": 1},
        "parent_release": _parent_release(),
    }
    lineage_files = {
        "lineage_sha256": "2" * 64,
        "reuse_manifest_sha256": "3" * 64,
        "parent_release": _parent_release(),
    }
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=lineage,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(extension=True),
        lineage_files=lineage_files,
        created_at="2026-08-20T00:00:00+00:00",
    )
    payload["audit"]["lineage_files"]["reuse_manifest_sha256"] = "4" * 64

    with pytest.raises(ValueError, match="lineage"):
        validate_build_provenance(payload)


@pytest.mark.parametrize(
    "corruption",
    [
        "empty_provider_settings",
        "default_provider_substitution",
        "injected_provider_substitution",
        "legacy_runtime_marker",
        "mixed_git_markers",
    ],
)
def test_native_provenance_rejects_rehashed_nested_profile_substitutions(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Native runtime, provider, settings, and Git profiles are exact."""
    _source_tree(tmp_path)
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    identity = payload["identity"]
    if corruption == "empty_provider_settings":
        identity["providers"]["rubric"]["settings"] = {}
    elif corruption == "default_provider_substitution":
        identity["providers"]["rubric"].update(
            {
                "provider": "substitute",
                "model": "substitute",
                "source": "default",
            }
        )
    elif corruption == "injected_provider_substitution":
        identity["providers"]["rubric"].update(
            {"provider": "substitute", "model": "substitute"}
        )
    elif corruption == "legacy_runtime_marker":
        identity["runtime_dependencies"]["python_version"] = unavailable(
            "legacy_checkpoint_predates_provenance"
        )
    else:
        payload["audit"]["git"]["commit"] = unavailable(
            "legacy_checkpoint_predates_provenance"
        )
    payload["identity_sha256"] = canonical_sha256(identity)

    with pytest.raises(ValueError, match="provenance|Git"):
        validate_build_provenance(payload)


@pytest.mark.parametrize("corruption", ["config_bool", "setting_float"])
def test_native_provenance_rejects_json_scalar_type_substitutions(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Native exact profiles distinguish JSON booleans, integers, and floats."""
    _source_tree(tmp_path)
    config = _default_config()
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=config,
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=_default_providers(config),
        prompt_values=_native_prompts(),
        calls=[],
        seeds=_native_seeds(),
        algorithms=provenance_module.build_algorithm_inventory(
            config,
            extension=False,
        ),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    identity = payload["identity"]
    if corruption == "config_bool":
        values = identity["resolved_configuration"]["values"]
        values["synthetic_coverage_enabled"] = 0
        identity["resolved_configuration"]["sha256"] = canonical_sha256(values)
    else:
        identity["providers"]["rubric"]["settings"]["max_retries"] = 3.0
    payload["identity_sha256"] = canonical_sha256(identity)

    with pytest.raises(ValueError, match="provenance"):
        validate_build_provenance(payload)


@pytest.mark.parametrize(
    "corruption",
    ["parent_release_extra", "lineage_types"],
)
def test_native_extension_rejects_rehashed_lineage_shape_substitutions(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Reduced extension lineage retains the exact live lineage contract."""
    _source_tree(tmp_path)
    parent_release = _parent_release()
    lineage = {
        "parent_asset_id": "v1",
        "clustering_mode": "keep",
        "added_labeled_record_ids": [],
        "added_unlabeled_record_ids": [],
        "parent_input_counts": {"labeled": 1, "unlabeled": 1},
        "extended_input_counts": {"labeled": 1, "unlabeled": 1},
        "parent_release": parent_release,
    }
    lineage_files = {
        "lineage_sha256": "a" * 64,
        "reuse_manifest_sha256": "b" * 64,
        "parent_release": parent_release,
    }
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=lineage,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(extension=True),
        lineage_files=lineage_files,
        created_at="2026-08-20T00:00:00+00:00",
    )
    identity = payload["identity"]
    if corruption == "parent_release_extra":
        identity["lineage"]["file_dependencies"]["parent_release"][
            "unexpected"
        ] = "accepted"
        payload["audit"]["lineage_files"]["parent_release"][
            "unexpected"
        ] = "accepted"
    else:
        identity["lineage"]["parent_asset_id"] = 7
        identity["lineage"]["clustering_mode"] = "unknown"
        identity["lineage"]["added_labeled_record_ids"] = "not-a-list"
        identity["lineage"]["parent_input_counts"] = {"labeled": -1}
    payload["identity_sha256"] = canonical_sha256(identity)

    with pytest.raises(ValueError, match="lineage"):
        validate_build_provenance(payload)


@pytest.mark.parametrize(
    "corruption",
    ["identity_extra", "usage_extra", "secret_request_id", "transport_ordinal"],
)
def test_provider_call_validator_rejects_nested_metadata_corruption(
    corruption: str,
) -> None:
    """Receipt-backed ledgers strictly validate all allowlisted transport fields."""
    row = build_provider_call(
        stage="intent_clustering",
        ordinal=1,
        provider_role="embedding",
        provider="provider",
        model="model",
        request={"request": "hashed only", "settings": {}},
        response=[[1.0, 0.0]],
        metadata=[
            {
                "transport_ordinal": 1,
                "response_id": "response-1",
                "request_id": "request-1",
                "model": "model-revision",
                "system_fingerprint": "fingerprint",
                "usage": {"input_tokens": 2, "total_tokens": 2},
                "retry_count": 0,
            }
        ],
    )
    candidate = json.loads(json.dumps(row))
    if corruption == "identity_extra":
        candidate["transport_identity"][0]["extra"] = True
    elif corruption == "usage_extra":
        candidate["transport_audit"][0]["usage"]["extra"] = 1
    elif corruption == "secret_request_id":
        candidate["transport_audit"][0]["request_id"] = "sk-secret-canary"
    else:
        candidate["transport_audit"][0]["transport_ordinal"] = 2

    with pytest.raises(ValueError, match="transport"):
        validate_provider_calls([candidate], expected_stage="intent_clustering")


def test_provider_call_validator_rejects_role_on_disallowed_stage() -> None:
    """A fabricated call cannot attach provider authority to a non-provider stage."""
    row = build_provider_call(
        stage="raw_inputs",
        ordinal=1,
        provider_role="rubric",
        provider="provider",
        model="model",
        request={"request": "hashed only", "settings": {}},
        response={"response": "hashed only"},
        metadata=None,
    )

    with pytest.raises(ValueError, match="provider role"):
        validate_provider_calls([row], expected_stage="raw_inputs")


@pytest.mark.parametrize("field", ["provider", "model"])
def test_pr2_provider_call_validator_rejects_secret_identity_fields(
    field: str,
) -> None:
    """Logical-call identity cannot persist credential-shaped values."""
    row = build_provider_call(
        stage="intent_clustering",
        ordinal=1,
        provider_role="embedding",
        provider="provider",
        model="model",
        request={"request": "hashed only", "settings": {}},
        response=[[1.0, 0.0]],
        metadata=None,
    )
    row[field] = "sk-secret-canary"

    with pytest.raises(ValueError, match="provider.*identity"):
        validate_provider_calls([row], expected_stage="intent_clustering")


@pytest.mark.parametrize(
    "corruption",
    ["logical_bool", "identity_bool", "audit_bool", "empty_transport"],
)
def test_provider_call_validator_rejects_non_integer_or_empty_ordinals(
    corruption: str,
) -> None:
    """Boolean ordinals and claimed-but-empty transport evidence are invalid."""
    row = build_provider_call(
        stage="intent_clustering",
        ordinal=1,
        provider_role="embedding",
        provider="provider",
        model="model",
        request={"request": "hashed only", "settings": {}},
        response=[[1.0, 0.0]],
        metadata=[
            {
                "transport_ordinal": 1,
                "usage": {"input_tokens": 1, "total_tokens": 1},
                "retry_count": 0,
            }
        ],
    )
    candidate = json.loads(json.dumps(row))
    if corruption == "logical_bool":
        candidate["ordinal"] = True
    elif corruption == "identity_bool":
        candidate["transport_identity"][0]["transport_ordinal"] = True
    elif corruption == "audit_bool":
        candidate["transport_audit"][0]["transport_ordinal"] = True
    else:
        candidate["transport_identity"] = []
        candidate["transport_audit"] = []

    with pytest.raises(ValueError, match="ordinal|transport"):
        validate_provider_calls([candidate], expected_stage="intent_clustering")


@pytest.mark.parametrize("ordinal", [True, 1.0, 0, -1])
def test_provider_call_builder_rejects_non_positive_integer_ordinals(
    ordinal: object,
) -> None:
    """Logical-call identity starts at an exact non-boolean integer ordinal."""
    with pytest.raises(ValueError, match="ordinal"):
        build_provider_call(
            stage="intent_clustering",
            ordinal=ordinal,  # type: ignore[arg-type]
            provider_role="embedding",
            provider="provider",
            model="model",
            request={"settings": {}},
            response=[],
            metadata=None,
        )


@pytest.mark.parametrize("metadata", [[], [{"transport_ordinal": True}]])
def test_metadata_sanitizer_rejects_empty_or_boolean_transport_ordinals(
    metadata: list[dict[str, object]],
) -> None:
    """An implemented metadata protocol provides a nonempty exact sequence."""
    with pytest.raises(ValueError, match="metadata|ordinal"):
        sanitize_call_metadata(metadata)


def test_build_provenance_calls_must_equal_authenticated_stage_ledgers(
    tmp_path: Path,
) -> None:
    """Rehashed call projections cannot differ from the stage-local ledgers."""
    _source_tree(tmp_path)
    call = build_provider_call(
        stage="rubric_extraction",
        ordinal=1,
        provider_role="rubric",
        provider="custom",
        model="rubric-model",
        request={
            "request": "hashed only",
            "settings": _native_providers()["rubric"]["settings"],
        },
        response={"response": "hashed only"},
        metadata=None,
    )
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[call],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    ledgers = {
        "rubric_extraction": [call],
        "intent_clustering": [],
        "coverage_decisions": [],
        "label_inference": [],
        "synthetic_coverage": [],
    }
    candidate = json.loads(json.dumps(payload))
    candidate["identity"]["calls"][0]["request_sha256"] = "f" * 64
    candidate["identity_sha256"] = canonical_sha256(candidate["identity"])

    provenance_module.validate_build_provenance_call_ledgers(payload, ledgers)
    with pytest.raises(ValueError, match="call ledger"):
        provenance_module.validate_build_provenance_call_ledgers(candidate, ledgers)


def test_historical_build_provenance_binds_v1_provider_settings_profile(
    tmp_path: Path,
) -> None:
    """Rehashing provider settings cannot contradict authenticated v1 calls."""
    _source_tree(tmp_path)
    call = build_provider_call(
        stage="rubric_extraction",
        ordinal=1,
        provider_role="rubric",
        provider="custom",
        model="rubric-model",
        request={"settings": _native_providers()["rubric"]["settings"]},
        response={},
        metadata=None,
    )
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=_native_providers(),
        prompt_values=_native_prompts(),
        calls=[call],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    ledgers = {
        "rubric_extraction": [call],
        "intent_clustering": [],
        "coverage_decisions": [],
        "label_inference": [],
        "synthetic_coverage": [],
    }
    profile = provenance_module.historical_build_provenance_profile(payload)
    provenance_module.validate_build_provenance_call_ledgers(
        payload,
        ledgers,
        profile=profile,
    )
    candidate = json.loads(json.dumps(payload))
    candidate["identity"]["providers"]["rubric"]["settings"][
        "timeout_seconds"
    ] = 123.0
    candidate["identity_sha256"] = canonical_sha256(candidate["identity"])

    with pytest.raises(ValueError, match="provider settings"):
        provenance_module.validate_build_provenance_call_ledgers(
            candidate,
            ledgers,
            profile=profile,
        )


def test_provider_settings_project_actual_builtin_and_unavailable_custom_fields() -> None:
    """Provenance states wire settings only when the provider exposes them."""
    builtin = OpenAIRubricProvider(model="gpt-4.1")
    identity = {"provider": "openai", "model": "gpt-4.1", "source": "default"}

    settings = provider_settings(
        builtin,
        role="rubric",
        identity=identity,
        pipeline_batch_size=16,
    )["settings"]

    assert settings["temperature"] == 0.0
    assert settings["response_format"] == "json_object"
    assert settings["seed"] == not_applicable("provider_does_not_use_sampling")

    class CustomProvider:
        model = "custom-model"

    custom = provider_settings(
        CustomProvider(),
        role="rubric",
        identity={
            "provider": "custom",
            "model": "custom-model",
            "source": "injected",
        },
        pipeline_batch_size=16,
    )["settings"]
    marker = unavailable("provider_does_not_expose_field")
    assert custom["temperature"] == marker
    assert custom["response_format"] == marker
    assert custom["seed"] == marker


def test_call_backed_injected_settings_survive_current_and_historical_validation(
    tmp_path: Path,
) -> None:
    """Actual injected settings are captured and bound to their call ledger."""
    _source_tree(tmp_path)

    class CustomRubricProvider:
        timeout_seconds = 300
        max_retries = 3
        retry_backoff_seconds = 2
        max_output_tokens = 16384
        temperature = 0.0
        response_format = "json_object"
        seed = 7

    identity = {
        "provider": "custom",
        "model": "rubric-model",
        "source": "injected",
    }
    rubric = provider_settings(
        CustomRubricProvider(),
        role="rubric",
        identity=identity,
        pipeline_batch_size=3,
    )
    providers = _native_providers()
    providers["rubric"] = rubric
    call = build_provider_call(
        stage="rubric_extraction",
        ordinal=1,
        provider_role="rubric",
        provider="custom",
        model="rubric-model",
        request={"settings": rubric["settings"]},
        response={},
        metadata=None,
    )
    payload = build_provenance(
        repository_root=tmp_path,
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(),
        lineage=None,
        providers=providers,
        prompt_values=_native_prompts(),
        calls=[call],
        seeds=_native_seeds(),
        algorithms=_native_algorithms(),
        lineage_files=None,
        created_at="2026-08-20T00:00:00+00:00",
    )
    ledgers = {
        "rubric_extraction": [call],
        "intent_clustering": [],
        "coverage_decisions": [],
        "label_inference": [],
        "synthetic_coverage": [],
    }

    provenance_module.validate_build_provenance_call_ledgers(payload, ledgers)
    provenance_module.validate_build_provenance_call_ledgers(
        payload,
        ledgers,
        profile=provenance_module.historical_build_provenance_profile(payload),
    )

    v2_payload = json.loads(json.dumps(payload))
    v2_payload["schema_version"] = "fapo-evaluation-build-provenance-v2"
    v2_payload["identity"]["schema_version"] = (
        "fapo-evaluation-build-identity-v2"
    )
    v2_payload["identity"]["source"] = _historical_source(
        v2_payload["identity"]["source"],
        members=provenance_module._HISTORICAL_SOURCE_FIXED_MEMBERS_V2,
    )
    v2_payload["identity"]["algorithms"] = (
        provenance_module.historical_algorithm_inventory_v2(
            v2_payload["identity"]["resolved_configuration"]["values"],
            extension=False,
        )
    )
    del v2_payload["identity"]["inputs"]["review_snapshot"]
    v2_payload["identity_sha256"] = canonical_sha256(v2_payload["identity"])
    provenance_module.validate_build_provenance_call_ledgers(
        v2_payload,
        ledgers,
        profile=provenance_module.HISTORICAL_PROVENANCE_PROFILE_V2,
    )

    v1_payload = json.loads(json.dumps(payload))
    v1_call = json.loads(json.dumps(call))
    v1_call["schema_version"] = "fapo-provider-call-v1"
    del v1_call["settings_sha256"]
    v1_payload["schema_version"] = "fapo-evaluation-build-provenance-v1"
    v1_payload["identity"]["schema_version"] = (
        "fapo-evaluation-build-identity-v1"
    )
    v1_payload["identity"]["source"] = _historical_source(
        v1_payload["identity"]["source"],
        members=provenance_module._HISTORICAL_SOURCE_FIXED_MEMBERS_V1,
    )
    v1_payload["identity"]["algorithms"] = (
        provenance_module.historical_algorithm_inventory_v1(
            v1_payload["identity"]["resolved_configuration"]["values"],
            extension=False,
        )
    )
    del v1_payload["identity"]["inputs"]["review_snapshot"]
    del v1_payload["identity"]["calls"][0]["settings_sha256"]
    v1_payload["identity_sha256"] = canonical_sha256(v1_payload["identity"])
    v1_ledgers = dict(ledgers)
    v1_ledgers["rubric_extraction"] = [v1_call]

    assert provenance_module.historical_build_provenance_profile(v1_payload) == (
        provenance_module.HISTORICAL_PROVENANCE_PROFILE_V1
    )
    provenance_module.validate_build_provenance_call_ledgers(
        v1_payload,
        v1_ledgers,
        profile=provenance_module.HISTORICAL_PROVENANCE_PROFILE_V1,
    )


def test_legacy_split_seed_is_bound_to_resolved_configuration() -> None:
    """Historical-unavailable provenance cannot invent a different split seed."""
    payload = provenance_module.build_legacy_provenance(
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(include_review=False),
        lineage=None,
        split_seed=int(_native_config()["split_seed"]),
        created_at="2026-08-20T00:00:00+00:00",
    )
    payload["identity"]["seeds"]["split"] += 1
    payload["identity_sha256"] = canonical_sha256(payload["identity"])

    with pytest.raises(ValueError, match="seed"):
        validate_build_provenance(
            payload,
            profile=provenance_module.historical_build_provenance_profile(payload),
        )


@pytest.mark.parametrize(
    "corruption",
    ["native-marker", "count-type", "count-equation", "generation-id"],
)
def test_legacy_lineage_profile_is_exact_and_type_sensitive(
    corruption: str,
) -> None:
    """Legacy native and extension lineage retain one closed v2 profile."""
    lineage = None
    if corruption != "native-marker":
        lineage = {
            "parent_asset_id": "v1",
            "clustering_mode": "keep",
            "added_labeled_record_ids": ["feedback-2"],
            "added_unlabeled_record_ids": [],
            "parent_input_counts": {"labeled": 1, "unlabeled": 1},
            "extended_input_counts": {"labeled": 2, "unlabeled": 1},
            "parent_release": _parent_release(),
        }
    payload = provenance_module.build_legacy_provenance(
        resolved_configuration=_native_config(),
        copied_inputs=_native_inputs(include_review=False),
        lineage=lineage,
        split_seed=int(_native_config()["split_seed"]),
        created_at="2026-08-20T00:00:00+00:00",
    )
    identity_lineage = payload["identity"]["lineage"]
    if corruption == "native-marker":
        identity_lineage["reason"] = "provider_does_not_expose_field"
    elif corruption == "count-type":
        identity_lineage["parent_input_counts"]["labeled"] = True
    elif corruption == "count-equation":
        identity_lineage["extended_input_counts"]["labeled"] = 99
    else:
        identity_lineage["parent_generation_id"] = "not-a-generation"
    payload["identity_sha256"] = canonical_sha256(payload["identity"])

    with pytest.raises(ValueError, match="legacy.*lineage"):
        validate_build_provenance(
            payload,
            profile=provenance_module.historical_build_provenance_profile(payload),
        )


def test_extension_file_dependencies_change_deterministic_build_identity(
    tmp_path: Path,
) -> None:
    """Parent snapshot and reuse hashes are generation-addressing dependencies."""
    _source_tree(tmp_path)
    base = {
        "repository_root": tmp_path,
        "resolved_configuration": _native_config(),
        "copied_inputs": _native_inputs(),
        "lineage": {
            "parent_asset_id": "v1",
            "clustering_mode": "keep",
            "added_labeled_record_ids": [],
            "added_unlabeled_record_ids": [],
            "parent_input_counts": {"labeled": 1, "unlabeled": 1},
            "extended_input_counts": {"labeled": 1, "unlabeled": 1},
            "parent_release": _parent_release(),
        },
        "providers": _native_providers(),
        "prompt_values": _native_prompts(),
        "calls": [],
        "seeds": _native_seeds(),
        "algorithms": _native_algorithms(),
        "created_at": "2026-08-20T00:00:00+00:00",
    }
    first = build_provenance(
        **base,
        lineage_files={
            "lineage_sha256": "2" * 64,
            "reuse_manifest_sha256": "3" * 64,
            "parent_release": _parent_release(),
        },
    )
    changed = build_provenance(
        **base,
        lineage_files={
            "lineage_sha256": "2" * 64,
            "reuse_manifest_sha256": "4" * 64,
            "parent_release": _parent_release(),
        },
    )

    assert changed["identity_sha256"] != first["identity_sha256"]


def test_stage_provenance_distinguishes_calls_and_extension_algorithm() -> None:
    """Stage-local facts cannot claim no calls or the native split algorithm."""
    config = EvaluationAssetConfig(tenant_id="tenant", asset_id="asset")

    assert _stage_seeds(
        PipelineStage.RUBRIC_EXTRACTION,
        config,
        call_count=1,
    ) == {"sampling": not_applicable("provider_does_not_use_sampling")}
    assert _stage_algorithms(
        PipelineStage.DATASET_SPLITS,
        config,
        extension=True,
    )["revision"] == {
        "algorithm": (
            "approved-exact-family-early-split-stable-extension-v1"
        ),
        "trusted_split_assignment": "connected-model-context-stable-hash-v1",
        "regression_selection": "deterministic-early-connected-group-hash-v1",
        "derived_inclusion": "approved-exact-fingerprint-only-v1",
        "hold_policy": "exclude-held-cases-and-families-v1",
        "regression_fraction": 0.2,
    }


def _native_stage_provenance_case(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    repository = tmp_path / "repository"
    _source_tree(repository)
    stage = PipelineStage.RUBRIC_EXTRACTION
    prompts = {
        "evidence_extraction": "exact evidence prompt",
        "guideline_synthesis": "exact guideline prompt",
    }
    provider_identity = {
        "rubric": _native_providers()["rubric"]
    }
    calls = [
        build_provider_call(
            stage=stage.value,
            ordinal=1,
            provider_role="rubric",
            provider="custom",
            model="rubric-model",
            request={
                "prompt_sha256": "1" * 64,
                "settings": provider_identity["rubric"]["settings"],
            },
            response={"result_sha256": "2" * 64},
            metadata=None,
        )
    ]
    source = working_source_identity(repository)
    seeds = {"sampling": not_applicable("provider_does_not_use_sampling")}
    algorithms = {"stage": stage.value, "revision": "stage-revision-v1"}
    payload = provenance_module.build_stage_provenance(
        stage=stage.value,
        provider_identity=provider_identity,
        prompt_values=prompts,
        calls=calls,
        code=source,
        seeds=seeds,
        algorithms=algorithms,
    )
    expected = {
        "expected_stage": stage.value,
        "profile": "native",
        "expected_provider_identity": provider_identity,
        "expected_prompt_set_sha256": canonical_sha256(
            {row["name"]: row["sha256"] for row in payload["prompts"]}
        ),
        "expected_prompts": payload["prompts"],
        "expected_calls": calls,
        "expected_source": source,
        "expected_seeds": seeds,
        "expected_algorithms": algorithms,
    }
    return payload, expected


def test_stage_provenance_validator_accepts_exact_native_and_legacy_profiles(
    tmp_path: Path,
) -> None:
    """Only the declared native profile and exact historical marker are accepted."""
    payload, expected = _native_stage_provenance_case(tmp_path)

    assert provenance_module.validate_stage_provenance(payload, **expected) == payload
    v3_expected = dict(expected)
    v3_expected["profile"] = provenance_module.HISTORICAL_PROVENANCE_PROFILE_V3
    assert provenance_module.validate_stage_provenance(
        payload,
        **v3_expected,
    ) == payload

    v2_payload = json.loads(json.dumps(payload))
    v2_payload["schema_version"] = "fapo-stage-provenance-v2"
    v2_source = _historical_source(
        v2_payload["source"],
        members=provenance_module._HISTORICAL_SOURCE_FIXED_MEMBERS_V2,
    )
    v2_payload["source"] = v2_source
    v2_expected = dict(expected)
    v2_expected.update(
        profile=provenance_module.HISTORICAL_PROVENANCE_PROFILE_V2,
        expected_source=v2_source,
    )
    assert provenance_module.validate_stage_provenance(
        v2_payload,
        **v2_expected,
    ) == v2_payload

    v1_payload = json.loads(json.dumps(payload))
    v1_payload["schema_version"] = "fapo-stage-provenance-v1"
    v1_provider = {
        role: {
            field: identity[field]
            for field in ("provider", "model", "source")
        }
        for role, identity in v1_payload["provider_identity"].items()
    }
    v1_payload["provider_identity"] = v1_provider
    for call in v1_payload["calls"]:
        call["schema_version"] = "fapo-provider-call-v1"
        del call["settings_sha256"]
    v1_source = _historical_source(
        v1_payload["source"],
        members=provenance_module._HISTORICAL_SOURCE_FIXED_MEMBERS_V1,
    )
    v1_payload["source"] = v1_source
    v1_expected = dict(expected)
    v1_expected.update(
        profile=provenance_module.HISTORICAL_PROVENANCE_PROFILE_V1,
        expected_provider_identity=v1_provider,
        expected_calls=v1_payload["calls"],
        expected_source=v1_source,
    )
    assert provenance_module.validate_stage_provenance(
        v1_payload,
        **v1_expected,
    ) == v1_payload

    legacy = provenance_module.build_legacy_stage_provenance("raw_inputs")
    assert provenance_module.validate_stage_provenance(
        legacy,
        expected_stage="raw_inputs",
        profile="legacy",
    ) == legacy


@pytest.mark.parametrize(
    "corruption",
    [
        "outer_extra_secret",
        "wrong_stage",
        "provider_nested_extra",
        "prompt_hash",
        "call_identity",
        "source_member_extra",
        "seed_bool",
        "algorithm_extra",
    ],
)
def test_native_stage_provenance_rejects_exact_profile_and_cross_link_corruption(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Self-consistent JSON cannot substitute any stage provenance fact."""
    payload, expected = _native_stage_provenance_case(tmp_path)
    candidate = json.loads(json.dumps(payload))
    if corruption == "outer_extra_secret":
        candidate["request_body"] = "sk-stage-provenance-canary"
    elif corruption == "wrong_stage":
        candidate["stage"] = "raw_inputs"
    elif corruption == "provider_nested_extra":
        candidate["provider_identity"]["rubric"]["headers"] = {
            "authorization": "Bearer stage-provenance-canary"
        }
    elif corruption == "prompt_hash":
        candidate["prompts"][0]["sha256"] = "3" * 64
    elif corruption == "call_identity":
        candidate["calls"][0]["provider"] = "substitute"
    elif corruption == "source_member_extra":
        candidate["source"]["members"][0]["body"] = "protected request"
    elif corruption == "seed_bool":
        candidate["seeds"] = {"sampling": False}
    elif corruption == "algorithm_extra":
        candidate["algorithms"]["request"] = {"body": "protected response"}
    else:  # pragma: no cover - parameter list is exhaustive
        raise AssertionError(corruption)

    with pytest.raises(ValueError, match="provenance"):
        provenance_module.validate_stage_provenance(candidate, **expected)


@pytest.mark.parametrize(
    "field",
    ["provider_identity", "prompts", "calls", "seeds", "algorithms", "source"],
)
def test_legacy_stage_provenance_requires_exact_unavailable_marker(field: str) -> None:
    """Legacy adoption cannot substitute a generic or native-looking marker."""
    candidate = provenance_module.build_legacy_stage_provenance("raw_inputs")
    candidate[field] = unavailable("provider_does_not_expose_field")

    with pytest.raises(ValueError, match="stage provenance"):
        provenance_module.validate_stage_provenance(
            candidate,
            expected_stage="raw_inputs",
            profile="legacy",
        )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"stage":"raw_inputs","stage":"raw_inputs"}',
        b'{"stage":"raw_inputs","value":NaN}',
        b'{"stage":"raw_inputs","value":Infinity}',
    ],
)
def test_strict_json_object_rejects_duplicate_keys_and_nonstandard_numbers(
    raw: bytes,
) -> None:
    """Stage provenance parsing uses the same strict control JSON boundary."""
    with pytest.raises(ValueError, match="control JSON"):
        control_jsonl_module.parse_strict_json_object(raw)
