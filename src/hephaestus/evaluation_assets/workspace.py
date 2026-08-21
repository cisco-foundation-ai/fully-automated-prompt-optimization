# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Filesystem layout and persistence for evaluation assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, Mapping, Optional, Sequence

from src.hephaestus import local_authority_io as authority_io
from src.hephaestus.artifact_io import (
    atomic_append_jsonl as atomic_append_jsonl,
)
from src.hephaestus.artifact_io import atomic_copy_file
from src.hephaestus.artifact_io import (
    atomic_write_json as atomic_write_json,
)
from src.hephaestus.artifact_io import (
    atomic_write_jsonl as atomic_write_jsonl,
)
from src.hephaestus.artifact_io import (
    atomic_write_text as atomic_write_text,
)
from src.hephaestus.evaluation_assets import models as evaluation_asset_models
from src.hephaestus.evaluation_assets.control_jsonl import (
    acquire_local_authority_lock,
    open_local_authority_directory,
    parse_strict_json_object,
    parse_strict_jsonl_objects,
    read_local_authority_file_at,
    remove_local_authority_file,
    resolve_local_authority_file,
    write_local_authority_json,
    write_local_authority_jsonl,
    write_local_authority_text,
)
from src.hephaestus.evaluation_assets.durability import (
    STAGE_SPECIFICATIONS,
    EvaluationAssetBusyError,
    EvaluationAssetImmutableError,
    EvaluationAssetIntegrityError,
    EvaluationAssetLegacyError,
    _exact_completed_state,
    _exact_pre_v2_history_from_authority,
    _exact_v2_state,
    _validate_local_authority_layout,
    _verify_prospective_legacy_adoption_candidate,
    build_stage_receipt,
    persisted_json_sha256,
    released_parent_evidence,
    validate_legacy_release_candidate,
    verify_raw_snapshot_floor,
    verify_release_candidate,
    verify_released_asset,
)
from src.hephaestus.evaluation_assets.input_contract import validate_input_records
from src.hephaestus.evaluation_assets.journal_transitions import (
    JOURNAL_SCHEMA_VERSION,
    PERSISTED_STAGE_COUNT_KEYS_V2,
    PERSISTED_STAGE_INDEX_V2,
    PERSISTED_STAGE_VALUES_V2,
    append_jsonl_bytes,
    derive_adoption_plan,
    derive_audit_transition,
    derive_rebuild_plan,
    derive_release_publication_plan,
    derive_revision_plan,
    is_exact_legacy_event_row_v1,
    normalized_legacy_completed_state_v1,
)
from src.hephaestus.evaluation_assets.journal_validation import (
    validate_recovery_journal,
)
from src.hephaestus.evaluation_assets.lineage_validation import (
    LINEAGE_SCHEMA_VERSION,
    REUSE_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
    StageState,
)
from src.hephaestus.evaluation_assets.provenance import (
    build_legacy_provenance,
    build_legacy_stage_provenance,
)
from src.hephaestus.evaluation_assets.publication import (
    GENERATION_MANIFEST_SCHEMA_VERSION,
    LOGICAL_SPLITS,
    InstalledGeneration,
    build_generation_descriptor,
    build_generation_manifest,
    build_release_pointer,
    generation_id_for_descriptor,
    install_generation,
    resolve_evaluation_asset_release,
    validate_historical_generation,
    write_release_pointer,
)

SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")
STAGE_DIRECTORIES = dict(
    zip(
        PERSISTED_STAGE_VALUES_V2,
        (
            "01_raw_inputs",
            "02_prepared_inputs",
            "03_evaluation_guidelines",
            "04_intent_clustering",
            "05_coverage_decisions",
            "06_label_inference",
            "07_synthetic_coverage",
            "08_dataset_splits",
        ),
        strict=True,
    )
)


def _persisted_stages_v2() -> tuple[str, ...]:
    """Return immutable v2 stage keys without consulting the authoring enum."""
    return PERSISTED_STAGE_VALUES_V2


def _local_authority_bytes(layout: "EvaluationAssetLayout", path: Path) -> bytes:
    """Read one exact no-follow authority file beneath the tenants root."""
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read",
    )
    if authority.data is None:
        raise ValueError("local authority read did not return bytes")
    return authority.data


def _optional_local_authority_bytes(
    layout: "EvaluationAssetLayout",
    path: Path,
) -> tuple[bool, bytes]:
    """Observe optional authority presence and bytes through one bound handle."""
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read_optional",
    )
    if not authority.exists:
        return False, b""
    if authority.data is None:
        raise ValueError("optional local authority read did not return bytes")
    return True, authority.data


def _local_authority_node_exists(
    layout: "EvaluationAssetLayout",
    path: Path,
) -> bool:
    """Treat every present or unsafe node as authority evidence."""
    try:
        return _optional_local_authority_bytes(layout, path)[0]
    except (OSError, ValueError):
        return True


def _local_authority_json(
    layout: "EvaluationAssetLayout",
    path: Path,
) -> dict[str, Any]:
    """Parse one exact local authority JSON object from its bound handle bytes."""
    return parse_strict_json_object(_local_authority_bytes(layout, path))


def _local_authority_sha256(
    layout: "EvaluationAssetLayout",
    path: Path,
) -> str:
    """Hash the same no-follow authority bytes accepted by the resolver."""
    return hashlib.sha256(_local_authority_bytes(layout, path)).hexdigest()


def _assert_legacy_authority_unchanged(
    layout: "EvaluationAssetLayout",
    artifact_snapshot: Mapping[Path, bytes],
    artifact_presence: Mapping[Path, bool],
) -> None:
    """Require the complete captured legacy inventory to remain unchanged."""
    if any(
        _local_authority_bytes(layout, path) != payload
        for path, payload in artifact_snapshot.items()
    ):
        raise ValueError("legacy authority changed after semantic validation")
    if any(
        resolve_local_authority_file(
            path,
            layout.tenants_root,
            access="write",
        ).exists
        != expected
        for path, expected in artifact_presence.items()
    ):
        raise ValueError(
            "legacy authority inventory changed after semantic validation"
        )


def _rollback_new_release_pointer(
    layout: "EvaluationAssetLayout",
    *,
    preexisting: bool,
    pointer: Mapping[str, Any],
    installed_identity: tuple[int, int, int] | None,
) -> None:
    """Quarantine only the exact pointer installed by the failed operation."""
    del pointer
    if preexisting or installed_identity is None:
        return
    try:
        remove_local_authority_file(
            layout.release_pointer_path,
            layout.tenant_root,
            expected_identity=installed_identity,
        )
    except (OSError, ValueError):
        # A raced replacement is not owned by this operation and must survive.
        return


def _handle_release_state_failure(
    layout: "EvaluationAssetLayout",
    *,
    before_state: Mapping[str, Any],
    target_state: Mapping[str, Any],
    preexisting: bool,
    pointer: Mapping[str, Any],
    installed_identity: tuple[int, int, int] | None,
) -> None:
    """Rollback a pointer only while state remains the exact WAL-before bytes."""
    try:
        present, current = _optional_local_authority_bytes(layout, layout.state_path)
    except (OSError, ValueError):
        return
    if not present or current != _persisted_json_bytes(before_state):
        # Target and foreign/unknown states retain the pointer so recovery never
        # compounds a possibly completed state installation.
        del target_state
        return
    _rollback_new_release_pointer(
        layout,
        preexisting=preexisting,
        pointer=pointer,
        installed_identity=installed_identity,
    )


def _release_pointer_write_expectation(
    layout: "EvaluationAssetLayout",
    descriptor: Mapping[str, Any],
    *,
    owned_retry: Mapping[str, Any] | None = None,
) -> tuple[bool, bytes | None]:
    """Bind a pointer write to the operation's earlier WAL observation."""
    if set(descriptor) != {"present", "bytes", "sha256"} or not isinstance(
        descriptor.get("present"),
        bool,
    ):
        raise ValueError("release pointer WAL descriptor is invalid")
    expected_present = descriptor["present"]
    present, payload = _optional_local_authority_bytes(
        layout,
        layout.release_pointer_path,
    )
    if present != expected_present:
        if not (
            not expected_present
            and present
            and owned_retry is not None
            and payload == _persisted_json_bytes(owned_retry)
        ):
            raise ValueError("release pointer presence changed after WAL observation")
        return False, payload
    if not present:
        if descriptor["bytes"] != 0 or descriptor["sha256"] is not None:
            raise ValueError("absent release pointer WAL descriptor is invalid")
        return False, None
    if (
        not isinstance(descriptor["bytes"], int)
        or isinstance(descriptor["bytes"], bool)
        or descriptor["bytes"] != len(payload)
        or not isinstance(descriptor["sha256"], str)
        or descriptor["sha256"] != hashlib.sha256(payload).hexdigest()
    ):
        raise ValueError("release pointer changed after WAL observation")
    return True, payload


def _wal_json_write_expectation(
    layout: "EvaluationAssetLayout",
    path: Path,
    before: Mapping[str, Any],
    target: Mapping[str, Any],
) -> bytes:
    """Accept only an exact WAL before/target JSON authority on recovery."""
    present, payload = _optional_local_authority_bytes(layout, path)
    allowed = {_persisted_json_bytes(before), _persisted_json_bytes(target)}
    if not present or payload not in allowed:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "control authority changed after its WAL observation",
        )
    return payload


def _wal_descriptor_write_expectation(
    layout: "EvaluationAssetLayout",
    path: Path,
    descriptor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> tuple[bool, bytes | None]:
    """Bind one generated control write to its WAL descriptor or exact retry."""
    if set(descriptor) != {"present", "bytes", "sha256"} or not isinstance(
        descriptor.get("present"),
        bool,
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "generated control WAL descriptor is invalid",
        )
    present, payload = _optional_local_authority_bytes(layout, path)
    target_bytes = _persisted_json_bytes(target)
    if present and payload == target_bytes:
        return True, payload
    if present != descriptor["present"]:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "generated control presence changed after its WAL observation",
        )
    if not present:
        if descriptor["bytes"] != 0 or descriptor["sha256"] is not None:
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "absent generated control WAL descriptor is invalid",
            )
        return False, None
    if (
        not isinstance(descriptor["bytes"], int)
        or isinstance(descriptor["bytes"], bool)
        or descriptor["bytes"] != len(payload)
        or not isinstance(descriptor["sha256"], str)
        or descriptor["sha256"] != hashlib.sha256(payload).hexdigest()
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "generated control changed after its WAL observation",
        )
    return False, payload


def _capture_legacy_generation_inventory(
    layout: "EvaluationAssetLayout",
    *,
    generation_id: str,
    descriptor: Mapping[str, Any],
    split_payloads: Mapping[str, bytes],
) -> tuple[tuple[str, int, int, tuple[tuple[str, str], ...]], ...]:
    """Capture only exact adoption-owned final/staging generation entries."""
    expected_manifest = _persisted_json_bytes(
        {
            "schema_version": GENERATION_MANIFEST_SCHEMA_VERSION,
            "tenant_id": layout.tenant_id,
            "asset_id": layout.asset_id,
            "generation_id": generation_id,
            "descriptor": dict(descriptor),
        }
    )
    expected_members = {
        **{f"{split}.jsonl": split_payloads[split] for split in LOGICAL_SPLITS},
        "generation_manifest.json": expected_manifest,
    }
    temporary_pattern = re.compile(
        rf"^\.{re.escape(generation_id)}\.[0-9a-f]{{32}}\.tmp$"
    )
    with open_local_authority_directory(
        layout.published_datasets,
        layout.tenant_root,
    ) as catalog_descriptor:
        generations_stat = authority_io.optional_stat_child(
            catalog_descriptor,
            "generations",
        )
        if generations_stat is None:
            return ()
        if generations_stat.kind != "directory":
            raise ValueError("legacy generation catalog is not an exact directory")
        generations_descriptor = authority_io.open_child_directory(
            catalog_descriptor,
            "generations",
            expected=generations_stat.identity,
        )
        try:
            captured = []
            for name in authority_io.list_children(generations_descriptor):
                child_stat = authority_io.stat_child(
                    generations_descriptor,
                    name,
                )
                if child_stat.kind != "directory":
                    raise ValueError("legacy generation entry is not a directory")
                final_generation = name == generation_id
                if not final_generation and temporary_pattern.fullmatch(name) is None:
                    raise ValueError("legacy checkpoint contains a foreign generation")
                temporary_descriptor = authority_io.open_child_directory(
                    generations_descriptor,
                    name,
                    expected=child_stat.identity,
                )
                try:
                    member_names = authority_io.list_children(temporary_descriptor)
                    if (
                        final_generation
                        and set(member_names) != set(expected_members)
                        or not final_generation
                        and any(
                            member not in expected_members for member in member_names
                        )
                    ):
                        raise ValueError(
                            "legacy generation member inventory is invalid"
                        )
                    members = tuple(
                        (
                            member,
                            hashlib.sha256(
                                read_local_authority_file_at(
                                    temporary_descriptor,
                                    member,
                                )
                            ).hexdigest(),
                        )
                        for member in member_names
                    )
                    if any(
                        digest
                        != hashlib.sha256(expected_members[member]).hexdigest()
                        for member, digest in members
                    ):
                        raise ValueError(
                            "legacy generation member content is invalid"
                        )
                    if authority_io.list_children(temporary_descriptor) != member_names:
                        raise ValueError(
                            "legacy generation member inventory changed"
                        )
                    captured.append(
                        (
                            name,
                            child_stat.identity[0],
                            child_stat.identity[1],
                            members,
                        )
                    )
                finally:
                    temporary_descriptor.close()
            if authority_io.list_children(generations_descriptor) != tuple(
                row[0] for row in captured
            ):
                raise ValueError("legacy generation inventory changed")
            return tuple(captured)
        finally:
            generations_descriptor.close()


def _capture_local_authority_tree(
    root: Path,
    trusted_root: Path,
) -> tuple[tuple[str, str, int, int, str], ...]:
    """Capture one exact no-follow directory inventory and regular-file bytes."""
    records: list[tuple[str, str, int, int, str]] = []
    def capture(
        directory_descriptor: authority_io.DirectoryLike,
        prefix: str,
    ) -> None:
        names = authority_io.list_children(directory_descriptor)
        for name in names:
            details = authority_io.stat_child(directory_descriptor, name)
            relative = f"{prefix}/{name}" if prefix else name
            if details.kind == "file":
                payload = read_local_authority_file_at(directory_descriptor, name)
                records.append(
                    (
                        relative,
                        "file",
                        details.identity[0],
                        details.identity[1],
                        hashlib.sha256(payload).hexdigest(),
                    )
                )
                continue
            if details.kind != "directory":
                raise ValueError("local authority tree contains an unsafe node")
            child_descriptor = authority_io.open_child_directory(
                directory_descriptor,
                name,
                expected=details.identity,
            )
            try:
                records.append(
                    (
                        relative,
                        "directory",
                        details.identity[0],
                        details.identity[1],
                        "",
                    )
                )
                capture(child_descriptor, relative)
            finally:
                child_descriptor.close()
        if authority_io.list_children(directory_descriptor) != names:
            raise ValueError("local authority directory inventory changed")

    with open_local_authority_directory(root, trusted_root) as root_descriptor:
        root_identity = authority_io.directory_identity(root_descriptor)
        records.append((".", "directory", root_identity[0], root_identity[1], ""))
        capture(root_descriptor, "")
    return tuple(records)


PREVIOUS_STAGE_DIRECTORIES = {
    "rubric_extraction": "03_rubric_extraction",
}
LEGACY_DIRECTORIES = (
    "raw_inputs",
    "prepared_inputs",
    "decision_assets",
    "review_queues",
    "dataset_splits",
)


def utc_now() -> str:
    """Return a stable ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _persisted_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the exact bytes emitted by ``atomic_write_json``."""
    return (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _state_authority_expectation(
    state: PipelineState,
    fallback: Mapping[str, Any],
) -> bytes:
    """Return the exact state bytes loaded before mutable normalization."""
    authority = getattr(state, "_persisted_authority_bytes", None)
    return authority if isinstance(authority, bytes) else _persisted_json_bytes(fallback)


def _fault_point(name: str) -> None:
    """Provide a deterministic test seam between durable transaction phases."""


def _released_provider_decision(
    layout: "EvaluationAssetLayout",
    stage: PipelineStage | str,
    role: str,
    *,
    receipt_payload: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Return verified producing identity or an explicit unavailable marker."""
    receipt = (
        dict(receipt_payload)
        if receipt_payload is not None
        else _local_authority_json(layout, layout.receipt_path(stage))
    )
    provider_identity = receipt.get("provider_identity")
    if not isinstance(provider_identity, Mapping):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released provider identity is inconsistent",
        )
    if provider_identity.get("status") in {
        "unavailable",
        "historically_unavailable",
    }:
        return {"status": "unavailable"}
    identity = provider_identity.get(role)
    if not isinstance(identity, Mapping):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released provider identity is inconsistent",
        )
    provider = identity.get("provider")
    model = identity.get("model")
    if (
        identity.get("status") == "unavailable"
        or not isinstance(provider, str)
        or not provider.strip()
        or not isinstance(model, str)
        or not model.strip()
    ):
        return {"status": "unavailable"}
    return {
        "status": "available",
        "provider": provider.strip(),
        "model": model.strip(),
    }


def _required_extension_provider_identity(
    *,
    role: str,
    configured_provider: str,
    configured_model: str,
    decision: Mapping[str, str],
    updates: Mapping[str, Any],
    allow_replacement: bool = False,
) -> tuple[str, str]:
    """Require an explicit child choice when parent evidence cannot be inherited."""
    provider_field = f"{role}_provider"
    model_field = f"{role}_model"
    configured = (configured_provider, configured_model)
    if decision.get("status") == "unavailable":
        explicit_provider = updates.get(provider_field)
        explicit_model = updates.get(model_field)
        if (
            not isinstance(explicit_provider, str)
            or not explicit_provider.strip()
            or not isinstance(explicit_model, str)
            or not explicit_model.strip()
        ):
            raise ValueError(
                "extension requires an explicit provider identity because "
                f"the released parent {role} identity is unavailable"
            )
        return explicit_provider.strip(), explicit_model.strip()
    producing = (str(decision["provider"]), str(decision["model"]))
    if allow_replacement and producing != configured:
        explicit_provider = updates.get(provider_field)
        explicit_model = updates.get(model_field)
        if (
            not isinstance(explicit_provider, str)
            or not explicit_provider.strip()
            or not isinstance(explicit_model, str)
            or not explicit_model.strip()
        ):
            raise ValueError(
                "extension requires an explicit provider identity because "
                f"released parent {role} evidence differs from configuration"
            )
        return explicit_provider.strip(), explicit_model.strip()
    if producing != configured and (
        updates.get(provider_field),
        updates.get(model_field),
    ) != producing:
        raise ValueError(
            "extension requires an explicit provider identity matching "
            f"released parent {role} evidence"
        )
    return producing


@contextmanager
def _ordered_asset_locks(
    layouts: Sequence["EvaluationAssetLayout"],
    timeout: float,
) -> Iterator[None]:
    """Acquire unique asset locks by sorted absolute path and release in reverse."""
    ordered = sorted(
        {str(layout.lock_path.absolute()): layout for layout in layouts}.items()
    )
    current: Optional[EvaluationAssetLayout] = None
    with ExitStack() as stack:
        for _, layout in ordered:
            try:
                authority_io.validate_existing_directory_chain(
                    layout.repository_base,
                    layout.tenants_root,
                )
                _validate_local_authority_layout(layout)
            except (OSError, ValueError) as exc:
                raise EvaluationAssetIntegrityError(
                    layout.tenant_id,
                    layout.asset_id,
                    "local authority path is unsafe",
                ) from exc
        for _, current in ordered:
            try:
                stack.enter_context(
                    acquire_local_authority_lock(
                        current.lock_path,
                        current.repository_base,
                        timeout=timeout,
                    )
                )
            except TimeoutError as exc:
                raise EvaluationAssetBusyError(
                    current.tenant_id,
                    current.asset_id,
                ) from exc
            except (OSError, ValueError) as exc:
                raise EvaluationAssetIntegrityError(
                    current.tenant_id,
                    current.asset_id,
                    "local authority lock path is unsafe",
                ) from exc
        yield


@dataclass(frozen=True)
class EvaluationAssetLayout:
    """Canonical self-contained layout for one tenant asset version."""

    tenants_root: Path
    tenant_id: str
    asset_id: str
    repository_base: Path | None = None

    def __post_init__(self) -> None:
        if not SAFE_NAME.fullmatch(self.tenant_id):
            raise ValueError("tenant_id must contain only letters, digits, '-' or '_'")
        if not SAFE_NAME.fullmatch(self.asset_id):
            raise ValueError("asset_id must contain only letters, digits, '-' or '_'")
        explicit_base = self.repository_base is not None
        base = Path(
            os.path.abspath(
                os.fspath(
                    self.repository_base
                    if explicit_base
                    else Path.cwd()
                    if not self.tenants_root.is_absolute()
                    else self.tenants_root.parent
                )
            )
        )
        tenants_root = Path(
            os.path.abspath(
                os.fspath(
                    self.tenants_root
                    if self.tenants_root.is_absolute()
                    else base / self.tenants_root
                )
            )
        )
        if explicit_base:
            try:
                tenants_root.relative_to(base)
            except ValueError as exc:
                raise ValueError(
                    "tenants root must remain within the repository base"
                ) from exc
            try:
                authority_io.validate_existing_directory_chain(
                    base,
                    tenants_root,
                )
            except (OSError, ValueError) as exc:
                raise ValueError(
                    "tenants root must remain within the exact repository base"
                ) from exc
        object.__setattr__(self, "repository_base", base)
        object.__setattr__(self, "tenants_root", tenants_root)

    def repository_relative_path(self, path: Path) -> str:
        """Return one lexical repository-relative immutable artifact path."""
        candidate = Path(os.path.abspath(os.fspath(path)))
        try:
            relative = candidate.relative_to(self.repository_base)
        except ValueError as exc:
            raise ValueError("artifact path escapes the repository base") from exc
        return relative.as_posix()

    @property
    def tenant_root(self) -> Path:
        return self.tenants_root / self.tenant_id

    @property
    def assets_root(self) -> Path:
        return self.tenant_root / "evaluation_assets"

    @property
    def root(self) -> Path:
        return self.assets_root / self.asset_id

    @property
    def lock_path(self) -> Path:
        """Return the deterministic collection-level lock for this asset."""
        return self.assets_root / ".locks" / f"{self.asset_id}.lock"

    @contextmanager
    def asset_lock(self, timeout: float = 0) -> Iterator[None]:
        """Hold the cross-process mutation lock for this asset."""
        with _ordered_asset_locks((self,), timeout):
            yield

    @property
    def stages_root(self) -> Path:
        return self.root / "stages"

    @property
    def receipts_root(self) -> Path:
        return self.root / "receipts"

    def receipt_path(self, stage: PipelineStage | str) -> Path:
        """Return the commit-marker path for one ordered stage."""
        stage_name = str(getattr(stage, "value", stage))
        try:
            index = PERSISTED_STAGE_INDEX_V2[stage_name]
        except KeyError as exc:
            raise ValueError(f"Unknown evaluation asset stage: {stage_name}") from exc
        return self.receipts_root / f"{index:02d}_{stage_name}.json"

    @property
    def uses_stage_layout(self) -> bool:
        """Return whether this asset uses the canonical stage-oriented layout."""
        if self.stages_root.is_dir():
            return True
        return not any((self.root / name).exists() for name in LEGACY_DIRECTORIES)

    def stage_directory(self, stage: PipelineStage | str) -> Path:
        """Return the canonical output directory for one pipeline stage."""
        stage_name = str(getattr(stage, "value", stage))
        try:
            directory = STAGE_DIRECTORIES[stage_name]
        except KeyError as exc:
            raise ValueError(f"Unknown evaluation asset stage: {stage_name}") from exc
        canonical = self.stages_root / directory
        previous_name = PREVIOUS_STAGE_DIRECTORIES.get(stage_name)
        previous = self.stages_root / previous_name if previous_name else None
        if previous is not None and previous.is_dir() and not canonical.exists():
            return previous
        return canonical

    def artifact_path(
        self,
        stage: PipelineStage | str,
        relative_name: str,
    ) -> Path:
        """Resolve a stage artifact in either the canonical or legacy layout."""
        stage_name = str(getattr(stage, "value", stage))
        if self.uses_stage_layout:
            return self.stage_directory(stage_name) / relative_name
        return self.root / _legacy_artifact_path(stage_name, relative_name)

    def stage_provenance_path(self, stage: PipelineStage | str) -> Path:
        """Return a unique stage record path for canonical or historical layouts."""
        stage_name = str(getattr(stage, "value", stage))
        try:
            index = PERSISTED_STAGE_INDEX_V2[stage_name]
        except KeyError as exc:
            raise ValueError(f"Unknown evaluation asset stage: {stage_name}") from exc
        if self.uses_stage_layout:
            return self.artifact_path(stage_name, "provenance.json")
        return self.root / "stage_provenance" / f"{index:02d}_{stage_name}.json"

    @property
    def raw_inputs(self) -> Path:
        """Compatibility alias for Stage 1 or the legacy raw-input directory."""
        if self.uses_stage_layout:
            return self.stage_directory(evaluation_asset_models.PipelineStage.RAW_INPUTS)
        return self.root / "raw_inputs"

    @property
    def prepared_inputs(self) -> Path:
        """Compatibility alias for Stage 2 or the legacy prepared directory."""
        if self.uses_stage_layout:
            return self.stage_directory(
                evaluation_asset_models.PipelineStage.PREPARED_INPUTS
            )
        return self.root / "prepared_inputs"

    @property
    def decision_assets(self) -> Path:
        """Return the legacy decision directory for compatibility callers."""
        return self.root / "decision_assets"

    @property
    def review_queues(self) -> Path:
        """Compatibility alias for the Stage 5 review queue directory."""
        if self.uses_stage_layout:
            return (
                self.stage_directory(
                    evaluation_asset_models.PipelineStage.COVERAGE_DECISIONS
                )
                / "review_queue"
            )
        return self.root / "review_queues"

    @property
    def dataset_splits(self) -> Path:
        """Compatibility alias for Stage 8 or the legacy split directory."""
        if self.uses_stage_layout:
            return self.stage_directory(
                evaluation_asset_models.PipelineStage.DATASET_SPLITS
            )
        return self.root / "dataset_splits"

    @property
    def published_datasets(self) -> Path:
        """Return the versioned tenant dataset directory published by Stage 8."""
        return self.tenant_root / "datasets" / "evaluation_assets" / self.asset_id

    @property
    def generations_root(self) -> Path:
        """Return the immutable generation catalog for this asset."""
        return self.published_datasets / "generations"

    @property
    def release_pointer_path(self) -> Path:
        """Return the sole mutable catalog authority pointer."""
        return self.published_datasets / "release.json"

    @property
    def config_path(self) -> Path:
        return self.root / "config.json"

    @property
    def state_path(self) -> Path:
        return self.root / "pipeline_state.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.root / "asset_manifest.json"

    @property
    def build_provenance_path(self) -> Path:
        return self.root / "build_provenance.json"

    @property
    def config_history_path(self) -> Path:
        return self.root / "config_history.jsonl"

    @property
    def recovery_journal_path(self) -> Path:
        return self.root / "recovery_journal.jsonl"

    @property
    def lineage_path(self) -> Path:
        return self.root / "lineage.json"

    @property
    def reuse_manifest_path(self) -> Path:
        return self.root / "reuse_manifest.json"

    @property
    def feedback_path(self) -> Path:
        return self.artifact_path(
            evaluation_asset_models.PipelineStage.RAW_INPUTS,
            "labeled_feedback.jsonl",
        )

    @property
    def unlabeled_path(self) -> Path:
        return self.artifact_path(
            evaluation_asset_models.PipelineStage.RAW_INPUTS,
            "unlabeled.jsonl",
        )

    @property
    def parent_snapshot(self) -> Path:
        return self.artifact_path(
            evaluation_asset_models.PipelineStage.RAW_INPUTS,
            "parent_snapshot",
        )

    @property
    def historical_feedback_path(self) -> Path:
        """Return the frozen v2 Stage 1 labeled-input authority path."""
        return self.artifact_path(
            PERSISTED_STAGE_VALUES_V2[0],
            "labeled_feedback.jsonl",
        )

    @property
    def historical_unlabeled_path(self) -> Path:
        """Return the frozen v2 Stage 1 unlabeled-input authority path."""
        return self.artifact_path(
            PERSISTED_STAGE_VALUES_V2[0],
            "unlabeled.jsonl",
        )

    @property
    def historical_parent_snapshot(self) -> Path:
        """Return the frozen v2 extension snapshot authority directory."""
        return self.artifact_path(
            PERSISTED_STAGE_VALUES_V2[0],
            "parent_snapshot",
        )

    def ensure(
        self,
        *,
        precondition: Callable[[], None] | None = None,
    ) -> None:
        """Create the canonical directories without requiring other tenant files."""
        if self.uses_stage_layout:
            paths = [
                self.stage_directory(stage)
                for stage in evaluation_asset_models.PipelineStage
            ]
        else:
            paths = [self.root / name for name in LEGACY_DIRECTORIES]
        if precondition is not None:
            precondition()
        with open_local_authority_directory(
            self.root,
            self.tenants_root,
            create=True,
        ):
            pass
        for path in paths:
            with open_local_authority_directory(
                path,
                self.tenants_root,
                create=True,
            ):
                pass

    def _write_authority_json(
        self,
        path: Path,
        payload: Mapping[str, Any],
        *,
        precondition: Callable[[], None] | None = None,
        expected_current: bytes | None = None,
        check_expected_current: bool = False,
    ) -> None:
        if not check_expected_current:
            present, current = _optional_local_authority_bytes(self, path)
            expected_current = current if present else None
            check_expected_current = True
        write_local_authority_json(
            path,
            self.tenants_root,
            payload,
            precondition=precondition,
            expected_current=expected_current,
            check_expected_current=check_expected_current,
        )

    def _write_authority_jsonl(
        self,
        path: Path,
        rows: Iterable[Mapping[str, Any]],
    ) -> None:
        present, current = _optional_local_authority_bytes(self, path)
        write_local_authority_jsonl(
            path,
            self.tenants_root,
            rows,
            expected_current=current if present else None,
            check_expected_current=True,
        )

    def _write_authority_text(
        self,
        path: Path,
        content: str,
        *,
        expected_current: bytes | None = None,
        check_expected_current: bool = False,
    ) -> None:
        if not check_expected_current:
            present, current = _optional_local_authority_bytes(self, path)
            expected_current = current if present else None
            check_expected_current = True
        write_local_authority_text(
            path,
            self.tenants_root,
            content,
            expected_current=expected_current,
            check_expected_current=check_expected_current,
        )

    def resolve_input_source(self, path: Path) -> Path:
        """Resolve one authorized JSONL source for this selected tenant."""
        requested = path.expanduser().absolute()
        try:
            resolved = requested.resolve(strict=True)
        except FileNotFoundError as exc:
            raise FileNotFoundError(requested) from exc
        if not resolved.is_file():
            raise ValueError(
                f"Evaluation asset input must be a regular file: {requested}"
            )
        if requested.suffix != ".jsonl" or resolved.suffix != ".jsonl":
            raise ValueError(f"Evaluation asset inputs must use .jsonl: {requested}")

        source_root = (self.tenant_root / "source_artifacts").resolve()
        datasets_root = (self.tenant_root / "datasets").resolve()
        generated_root = (datasets_root / "evaluation_assets").resolve()
        if not _is_beneath(resolved, self.tenant_root):
            raise ValueError(
                "Evaluation asset input must remain inside the selected tenant "
                f"after symlink resolution: {requested}"
            )
        if _is_beneath(requested, generated_root) or _is_beneath(
            resolved,
            generated_root,
        ):
            raise ValueError(
                "Evaluation asset inputs cannot use generated "
                f"datasets/evaluation_assets files: {requested}"
            )
        if not (
            _is_beneath(resolved, source_root)
            or _is_beneath(resolved, datasets_root)
        ):
            raise ValueError(
                "Evaluation asset input must be a regular .jsonl file under "
                "the selected tenant's source_artifacts/ or datasets/: "
                f"{requested}"
            )
        return resolved

    def initialize(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        *,
        initial_status: str = "draft",
        lock_timeout: float = 0,
    ) -> PipelineState:
        """Copy raw inputs into the asset and persist initial config/state."""
        with self.asset_lock(lock_timeout):
            return self._initialize_locked(
                config,
                feedback_source,
                unlabeled_source,
                initial_status=initial_status,
            )

    def _initialize_locked(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        *,
        initial_status: str,
    ) -> PipelineState:
        """Initialize while the caller holds :attr:`lock_path`."""
        if initial_status not in {"draft", "queued"}:
            raise ValueError("initial_status must be draft or queued")
        if self.config_path.exists() or self.state_path.exists():
            raise FileExistsError(f"Evaluation asset already exists: {self.root}")
        feedback_source = self.resolve_input_source(feedback_source)
        unlabeled_source = self.resolve_input_source(unlabeled_source)
        _validate_source_rows(feedback_source, labeled=True)
        _validate_source_rows(unlabeled_source, labeled=False)
        self.ensure()
        _validate_local_authority_layout(self)
        _copy_jsonl(
            feedback_source,
            self.feedback_path,
            trusted_root=self.tenants_root,
        )
        _copy_jsonl(
            unlabeled_source,
            self.unlabeled_path,
            trusted_root=self.tenants_root,
        )
        timestamp = utc_now()
        state = PipelineState.new(config, timestamp)
        state.status = initial_status
        self._write_authority_json(self.config_path, config.to_dict())
        self._write_authority_json(self.state_path, state.to_dict())
        self._append_config_revision(
            {
                "timestamp": timestamp,
                "revision": 1,
                "event": "configuration_created",
                "configuration": config.to_dict(),
            }
        )
        self.append_event("pipeline_created", {"status": state.status})
        return state

    def initialize_extension(
        self,
        parent: "EvaluationAssetLayout",
        *,
        additional_feedback: Optional[Path],
        additional_unlabeled: Optional[Path],
        clustering_mode: str,
        config_updates: Optional[Mapping[str, Any]] = None,
        initial_status: str = "draft",
        lock_timeout: float = 0,
    ) -> PipelineState:
        """Create a child only after verifying its immutable released parent."""
        with _ordered_asset_locks((parent, self), lock_timeout):
            parent._recover_locked()
            return self._initialize_extension_locked(
                parent,
                additional_feedback=additional_feedback,
                additional_unlabeled=additional_unlabeled,
                clustering_mode=clustering_mode,
                config_updates=config_updates,
                initial_status=initial_status,
            )

    def _initialize_extension_locked(
        self,
        parent: "EvaluationAssetLayout",
        *,
        additional_feedback: Optional[Path],
        additional_unlabeled: Optional[Path],
        clustering_mode: str,
        config_updates: Optional[Mapping[str, Any]],
        initial_status: str,
    ) -> PipelineState:
        """Initialize an extension while both parent and child locks are held."""
        if clustering_mode not in {"keep", "refresh"}:
            raise ValueError("clustering_mode must be 'keep' or 'refresh'")
        if initial_status not in {"draft", "queued"}:
            raise ValueError("initial_status must be draft or queued")
        if parent.tenant_id != self.tenant_id:
            raise ValueError("parent and child assets must belong to the same tenant")
        if parent.asset_id == self.asset_id:
            raise ValueError("extended asset must use a new asset_id")
        if self.config_path.exists() or self.state_path.exists():
            raise FileExistsError(f"Evaluation asset already exists: {self.root}")
        resolved_feedback = (
            self.resolve_input_source(additional_feedback)
            if additional_feedback is not None
            else None
        )
        resolved_unlabeled = (
            self.resolve_input_source(additional_unlabeled)
            if additional_unlabeled is not None
            else None
        )
        extra_feedback = (
            _validate_source_rows(resolved_feedback, labeled=True)
            if resolved_feedback is not None
            else []
        )
        extra_unlabeled = (
            _validate_source_rows(resolved_unlabeled, labeled=False)
            if resolved_unlabeled is not None
            else []
        )
        if not extra_feedback and not extra_unlabeled:
            raise ValueError(
                "extension requires additional labeled or unlabeled records"
            )
        if clustering_mode == "keep" and extra_unlabeled:
            raise ValueError(
                "keep clustering accepts labeled additions only; "
                "use refresh when adding unlabeled records"
            )

        parent_state = parent.load_state()
        if parent_state.legacy_completed:
            raise EvaluationAssetLegacyError(
                parent.tenant_id,
                parent.asset_id,
                "explicit verification and adoption are required before extension",
            )
        if parent_state.status != "released":
            raise ValueError("parent evaluation asset must be released")
        parent_asset_authority = _capture_local_authority_tree(
            parent.root,
            parent.tenants_root,
        )
        parent_publication_authority = _capture_local_authority_tree(
            parent.published_datasets,
            parent.tenant_root,
        )
        parent_release = released_parent_evidence(parent, parent_state)
        if (
            _capture_local_authority_tree(parent.root, parent.tenants_root)
            != parent_asset_authority
            or _capture_local_authority_tree(
                parent.published_datasets,
                parent.tenant_root,
            )
            != parent_publication_authority
        ):
            raise EvaluationAssetIntegrityError(
                parent.tenant_id,
                parent.asset_id,
                "released parent authority changed during verification",
            )
        guideline_artifacts = (
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
        )
        compatibility_artifacts = ("feedback_rubrics.jsonl",)
        shared_artifacts = ("trusted_intents.jsonl", "trusted_cases.jsonl")
        stage_three_paths = {
            name: parent.artifact_path(PERSISTED_STAGE_VALUES_V2[2], name)
            for name in (
                *guideline_artifacts,
                *compatibility_artifacts,
                *shared_artifacts,
            )
        }
        fixed_snapshot_sources = {
            "parent_intent_inventory.jsonl": parent.artifact_path(
                PERSISTED_STAGE_VALUES_V2[3],
                "intent_inventory.jsonl",
            ),
            "parent_intent_matches.jsonl": parent.artifact_path(
                PERSISTED_STAGE_VALUES_V2[4],
                "intent_matches.jsonl",
            ),
            "parent_inferred_cluster_rubrics.jsonl": parent.artifact_path(
                PERSISTED_STAGE_VALUES_V2[5],
                "inferred_unlabeled_cluster_rubrics.jsonl",
            ),
            "parent_synthetic_cases.jsonl": parent.artifact_path(
                PERSISTED_STAGE_VALUES_V2[6],
                "synthetic_cases.jsonl",
            ),
            **{
                f"parent_{split}.jsonl": parent.artifact_path(
                    PERSISTED_STAGE_VALUES_V2[7],
                    f"{split}.jsonl",
                )
                for split in (
                    "train",
                    "validation",
                    "test",
                    "regression_trusted",
                )
            },
        }
        parent_authority_paths = {
            parent.state_path,
            parent.config_path,
            parent.historical_feedback_path,
            parent.historical_unlabeled_path,
            *(parent.receipt_path(stage) for stage in _persisted_stages_v2()),
            *stage_three_paths.values(),
            *fixed_snapshot_sources.values(),
        }
        parent_authority_snapshot: dict[Path, bytes] = {}
        parent_authority_presence: dict[Path, bool] = {}
        for path in parent_authority_paths:
            present, payload = _optional_local_authority_bytes(parent, path)
            parent_authority_presence[path] = present
            if present:
                parent_authority_snapshot[path] = payload
        stage_three_artifacts = (
            guideline_artifacts + shared_artifacts
            if parent_authority_presence[
                stage_three_paths["evaluation_guidelines.jsonl"]
            ]
            else compatibility_artifacts + shared_artifacts
        )
        snapshot_sources = {
            **{
                f"parent_{name}": stage_three_paths[name]
                for name in stage_three_artifacts
            },
            **fixed_snapshot_sources,
        }
        required_parent_paths = {
            parent.state_path,
            parent.config_path,
            parent.historical_feedback_path,
            parent.historical_unlabeled_path,
            parent.receipt_path(PERSISTED_STAGE_VALUES_V2[2]),
            parent.receipt_path(PERSISTED_STAGE_VALUES_V2[3]),
            *(stage_three_paths[name] for name in stage_three_artifacts),
            *fixed_snapshot_sources.values(),
        }
        if any(
            not parent_authority_presence.get(path, False)
            for path in required_parent_paths
        ):
            raise EvaluationAssetIntegrityError(
                parent.tenant_id,
                parent.asset_id,
                "released parent extension authority is incomplete",
            )
        parent_config = EvaluationAssetConfig.from_dict(
            parse_strict_json_object(parent_authority_snapshot[parent.config_path])
        )
        updates = dict(config_updates or {})
        expected_rubric_identity = _required_extension_provider_identity(
            role="rubric",
            configured_provider=parent_config.rubric_provider,
            configured_model=parent_config.rubric_model,
            decision=_released_provider_decision(
                parent,
                PERSISTED_STAGE_VALUES_V2[2],
                "rubric",
                receipt_payload=parse_strict_json_object(
                    parent_authority_snapshot[
                        parent.receipt_path(PERSISTED_STAGE_VALUES_V2[2])
                    ]
                ),
            ),
            updates=updates,
        )
        expected_embedding_identity = _required_extension_provider_identity(
            role="embedding",
            configured_provider=parent_config.embedding_provider,
            configured_model=parent_config.embedding_model,
            decision=_released_provider_decision(
                parent,
                PERSISTED_STAGE_VALUES_V2[3],
                "embedding",
                receipt_payload=parse_strict_json_object(
                    parent_authority_snapshot[
                        parent.receipt_path(PERSISTED_STAGE_VALUES_V2[3])
                    ]
                ),
            ),
            updates=updates,
            allow_replacement=clustering_mode == "refresh",
        )
        merged_config = parent_config.to_dict()
        merged_config.update(updates)
        merged_config["tenant_id"] = self.tenant_id
        merged_config["asset_id"] = self.asset_id
        if "embedding_model" in updates and "embedding_provider" not in updates:
            merged_config["embedding_provider"] = (
                "tfidf"
                if updates["embedding_model"] == "tfidf"
                else "openai"
            )
        config = EvaluationAssetConfig.from_dict(merged_config)
        if (config.rubric_provider, config.rubric_model) != (
            expected_rubric_identity
        ):
            raise ValueError(
                "incremental extension must keep the parent's guideline model"
            )
        if clustering_mode == "keep" and (
            (config.embedding_provider, config.embedding_model)
            != expected_embedding_identity
            or config.cluster_count != parent_config.cluster_count
        ):
            raise ValueError(
                "keep clustering requires the parent's embedding model "
                "and cluster count"
            )

        feedback_rows = _merge_jsonl_rows(
            _jsonl_rows_from_bytes(
                parent.historical_feedback_path,
                parent_authority_snapshot[parent.historical_feedback_path],
            ),
            extra_feedback,
            source="labeled feedback",
        )
        unlabeled_rows = _merge_jsonl_rows(
            _jsonl_rows_from_bytes(
                parent.historical_unlabeled_path,
                parent_authority_snapshot[parent.historical_unlabeled_path],
            ),
            extra_unlabeled,
            source="unlabeled input",
        )
        if released_parent_evidence(parent, parent_state) != parent_release:
            raise EvaluationAssetIntegrityError(
                parent.tenant_id,
                parent.asset_id,
                "released parent evidence changed during extension initialization",
            )
        _assert_legacy_authority_unchanged(
            parent,
            parent_authority_snapshot,
            parent_authority_presence,
        )
        def parent_authority_precondition() -> None:
            if (
                released_parent_evidence(parent, parent_state) != parent_release
                or _capture_local_authority_tree(parent.root, parent.tenants_root)
                != parent_asset_authority
                or _capture_local_authority_tree(
                    parent.published_datasets,
                    parent.tenant_root,
                )
                != parent_publication_authority
            ):
                raise EvaluationAssetIntegrityError(
                    parent.tenant_id,
                    parent.asset_id,
                    "released parent authority changed before child creation",
                )

        parent_authority_precondition()
        self.ensure(precondition=parent_authority_precondition)
        _validate_local_authority_layout(self)
        self._write_authority_jsonl(self.feedback_path, feedback_rows)
        self._write_authority_jsonl(self.unlabeled_path, unlabeled_rows)

        seeded_artifacts = []
        for name in stage_three_artifacts:
            source = stage_three_paths[name]
            destination = self.artifact_path(
                evaluation_asset_models.PipelineStage.RUBRIC_EXTRACTION,
                name,
            )
            self._write_authority_text(
                destination,
                parent_authority_snapshot[source].decode("utf-8"),
            )
            seeded_artifacts.append(name)
        snapshot_artifacts = []
        for name, source in snapshot_sources.items():
            destination = self.parent_snapshot / name
            destination_bytes = parent_authority_snapshot[source]
            self._write_authority_text(
                destination,
                destination_bytes.decode("utf-8"),
            )
            snapshot_artifacts.append(
                {
                    "file": name,
                    "sha256": hashlib.sha256(destination_bytes).hexdigest(),
                    "bytes": len(destination_bytes),
                }
            )

        reused_artifacts = []
        if clustering_mode == "keep":
            source = fixed_snapshot_sources["parent_intent_inventory.jsonl"]
            destination = self.artifact_path(
                evaluation_asset_models.PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            )
            self._write_authority_text(
                destination,
                parent_authority_snapshot[source].decode("utf-8"),
            )
            reused_artifacts.append("intent_inventory.jsonl")
            clusters = _jsonl_rows_from_bytes(
                source,
                parent_authority_snapshot[source],
            )
            lineage_rows = [
                {
                    "previous_cluster_id": row["cluster_id"],
                    "new_cluster_id": row["cluster_id"],
                    "member_overlap": 1.0,
                    "relationship": "reused",
                }
                for row in clusters
            ]
            self._write_authority_jsonl(
                self.artifact_path(
                    evaluation_asset_models.PipelineStage.INTENT_CLUSTERING,
                    "cluster_lineage.jsonl",
                ),
                lineage_rows,
            )
            reused_artifacts.append("cluster_lineage.jsonl")

        timestamp = utc_now()
        state = PipelineState.new(config, timestamp)
        state.status = initial_status

        lineage = {
            "schema_version": LINEAGE_SCHEMA_VERSION,
            "asset_id": self.asset_id,
            "parent_asset_id": parent.asset_id,
            "creation_mode": "incremental_feedback",
            "clustering_mode": clustering_mode,
            "created_at": timestamp,
            "parent_release": parent_release,
            "added_labeled_record_ids": [
                str(row["record_id"]) for row in extra_feedback
            ],
            "added_unlabeled_record_ids": [
                str(row["record_id"]) for row in extra_unlabeled
            ],
            "parent_input_counts": {
                "labeled": len(feedback_rows) - len(extra_feedback),
                "unlabeled": len(unlabeled_rows) - len(extra_unlabeled),
            },
            "extended_input_counts": {
                "labeled": len(feedback_rows),
                "unlabeled": len(unlabeled_rows),
            },
        }
        reuse_manifest = {
            "schema_version": REUSE_SCHEMA_VERSION,
            "asset_id": self.asset_id,
            "parent_asset_id": parent.asset_id,
            "parent_release": parent_release,
            "parent_snapshot": {
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "path": self.parent_snapshot.relative_to(self.root).as_posix(),
                "artifacts": snapshot_artifacts,
            },
            "seeded_incremental_stage": {
                "stage": PERSISTED_STAGE_VALUES_V2[2],
                "artifacts": seeded_artifacts,
                "operation": "append_evidence_and_rebuild_guidelines",
            },
            "reused_stages": (
                [
                    {
                        "stage": PERSISTED_STAGE_VALUES_V2[3],
                        "artifacts": reused_artifacts,
                        "reason": "no unlabeled records or clustering settings changed",
                    }
                ]
                if clustering_mode == "keep"
                else []
            ),
        }
        self._write_authority_json(self.config_path, config.to_dict())
        self._write_authority_json(self.state_path, state.to_dict())
        self._write_authority_json(self.lineage_path, lineage)
        self._write_authority_json(self.reuse_manifest_path, reuse_manifest)
        self._append_config_revision(
            {
                "timestamp": timestamp,
                "revision": 1,
                "event": "configuration_inherited",
                "parent_asset_id": parent.asset_id,
                "configuration": config.to_dict(),
            }
        )
        self.append_event(
            "pipeline_extended",
            {
                "parent_asset_id": parent.asset_id,
                "clustering_mode": clustering_mode,
                "added_labeled_records": len(extra_feedback),
                "added_unlabeled_records": len(extra_unlabeled),
            },
            operation_id=uuid.uuid4().hex,
        )
        return state

    def adopt_legacy(self, *, lock_timeout: float = 0) -> PipelineState:
        """Verify and explicitly adopt one pre-v2 completed asset."""
        try:
            _validate_local_authority_layout(self)
        except (OSError, ValueError) as exc:
            raise EvaluationAssetLegacyError(
                self.tenant_id,
                self.asset_id,
                "required stage artifacts or manifests failed verification",
            ) from exc
        with self.asset_lock(lock_timeout):
            recovered = self._recover_locked()
            state = self.load_state()
            if state.status == "released":
                verify_released_asset(self, state)
                if recovered:
                    return state
                raise EvaluationAssetImmutableError(self.tenant_id, self.asset_id)
            if not state.legacy_completed:
                raise EvaluationAssetLegacyError(
                    self.tenant_id,
                    self.asset_id,
                    "only a pre-v2 completed state can be adopted",
                )
            raw_state = _local_authority_json(self, self.state_path)
            persisted_stages = _persisted_stages_v2()
            try:
                legacy_artifact_snapshot: dict[Path, bytes] = {}
                legacy_artifact_presence: dict[Path, bool] = {}
                forbidden_native_paths = {
                    self.recovery_journal_path,
                    self.release_pointer_path,
                    self.artifact_path(
                        PERSISTED_STAGE_VALUES_V2[-1],
                        "generation_manifest.json",
                    ),
                    *(self.receipt_path(stage) for stage in persisted_stages),
                    *(
                        self.artifact_path(stage, "provider_calls.jsonl")
                        for stage in persisted_stages
                    ),
                }
                control_paths = {
                    self.state_path,
                    self.config_path,
                    self.config_history_path,
                    self.events_path,
                    self.lineage_path,
                    self.build_provenance_path,
                    *forbidden_native_paths,
                    *(
                        self.stage_provenance_path(stage)
                        for stage in persisted_stages
                    ),
                }
                for path in control_paths:
                    present, payload = _optional_local_authority_bytes(self, path)
                    legacy_artifact_presence[path] = present
                    if present:
                        legacy_artifact_snapshot[path] = payload
                if any(
                    legacy_artifact_presence[path]
                    for path in forbidden_native_paths
                ):
                    raise ValueError(
                        "legacy checkpoint contains native control authority"
                    )
                legacy_events = parse_strict_jsonl_objects(
                    legacy_artifact_snapshot.get(self.events_path, b"")
                )
                if any(
                    not is_exact_legacy_event_row_v1(
                        row,
                        tenant_id=self.tenant_id,
                        asset_id=self.asset_id,
                    )
                    for row in legacy_events
                ):
                    raise ValueError(
                        "legacy checkpoint contains native event authority"
                    )
                _validate_source_rows(self.historical_feedback_path, labeled=True)
                _validate_source_rows(self.historical_unlabeled_path, labeled=False)
                raw_config = parse_strict_json_object(
                    legacy_artifact_snapshot[self.config_path]
                )
                config = EvaluationAssetConfig.from_dict(raw_config)
                if config.to_dict() != raw_config:
                    raise ValueError(
                        "legacy checkpoint configuration is not type-exact"
                    )
                legacy_artifact_paths: dict[tuple[str, str], Path] = {}
                legacy_artifact_profiles: dict[str, str] = {}
                counts = validate_legacy_release_candidate(
                    self,
                    state,
                    config,
                    artifact_snapshot_out=legacy_artifact_snapshot,
                    artifact_presence_out=legacy_artifact_presence,
                    artifact_paths_out=legacy_artifact_paths,
                    artifact_profiles_out=legacy_artifact_profiles,
                )
                legacy_history = _exact_pre_v2_history_from_authority(
                    self,
                    raw_state,
                    artifact_overrides=legacy_artifact_snapshot,
                )
                if config.to_dict() != dict(legacy_history.final_configuration):
                    raise ValueError(
                        "legacy checkpoint configuration history is inconsistent"
                    )
                parse_strict_jsonl_objects(
                    legacy_artifact_snapshot.get(self.events_path, b"")
                )
                receipts: dict[str, dict[str, Any]] = {}
                timestamp = utc_now()
                _assert_legacy_authority_unchanged(
                    self,
                    legacy_artifact_snapshot,
                    legacy_artifact_presence,
                )
                (
                    generation,
                    target_manifests,
                    target_provenance,
                    generation_split_paths,
                    generation_split_payloads,
                    generation_inventory,
                ) = self._prepare_legacy_release_artifacts(
                    config,
                    timestamp,
                    legacy_artifact_snapshot,
                    legacy_artifact_presence,
                )
                artifact_overrides = {
                    **legacy_artifact_snapshot,
                    **self._adoption_manifest_overrides(target_manifests),
                    **{
                        self.stage_provenance_path(stage): _persisted_json_bytes(
                            target_provenance["stages"][stage]
                        )
                        for stage in persisted_stages
                    },
                    self.build_provenance_path: _persisted_json_bytes(
                        target_provenance["build"]
                    ),
                }
                for stage in persisted_stages:
                    stage_state = next(
                        item for item in state.stages if item.stage == stage
                    )
                    completed_at = (
                        stage_state.completed_at or state.updated_at or timestamp
                    )
                    stage_counts = {
                        key: counts[key]
                        for key in PERSISTED_STAGE_COUNT_KEYS_V2[stage]
                    }
                    receipts[stage] = build_stage_receipt(
                        self,
                        stage,
                        config,
                        stage_counts,
                        completed_at=completed_at,
                        prompt_values={},
                        origin="legacy_adoption",
                        historical_unavailable=True,
                        upstream_receipts=receipts,
                        artifact_overrides=artifact_overrides,
                        artifact_path_overrides=legacy_artifact_paths,
                        artifact_profile_override=legacy_artifact_profiles[stage],
                    )
            except EvaluationAssetLegacyError:
                raise
            except (
                EvaluationAssetIntegrityError,
                KeyError,
                OSError,
                TypeError,
                UnicodeError,
                ValueError,
            ) as exc:
                raise EvaluationAssetLegacyError(
                    self.tenant_id,
                    self.asset_id,
                    "required stage artifacts or manifests failed verification",
                ) from exc

            operation_id = uuid.uuid4().hex
            before_config = config.to_dict()
            before_state = raw_state
            target_receipts = {
                stage: receipts[stage] for stage in persisted_stages
            }
            stage_eight_receipt_sha256 = persisted_json_sha256(
                receipts["dataset_splits"]
            )
            pointer = build_release_pointer(
                tenant_id=self.tenant_id,
                asset_id=self.asset_id,
                generation=generation,
                stage_8_receipt_sha256=stage_eight_receipt_sha256,
                build_provenance_sha256=persisted_json_sha256(
                    target_provenance["build"]
                ),
                published_at=timestamp,
            )
            plan = derive_adoption_plan(
                before_config,
                before_state,
                target_receipts,
                pointer,
                operation_id=operation_id,
                prepared_at=timestamp,
            )
            target_state = _exact_completed_state(plan["target_state"])
            try:
                _verify_prospective_legacy_adoption_candidate(
                    self,
                    target_state,
                    receipts,
                    legacy_state=state,
                    artifact_overrides=artifact_overrides,
                    artifact_path_overrides=legacy_artifact_paths,
                )
            except (
                EvaluationAssetIntegrityError,
                KeyError,
                OSError,
                TypeError,
                UnicodeError,
                ValueError,
            ) as exc:
                raise EvaluationAssetLegacyError(
                    self.tenant_id,
                    self.asset_id,
                    "required release evidence failed verification",
                ) from exc
            prepared = {
                "schema_version": JOURNAL_SCHEMA_VERSION,
                "operation_id": operation_id,
                "kind": "legacy_adoption",
                "phase": "prepared",
                "prepared_at": timestamp,
                "request": {"release_pointer": pointer},
                "before_config": before_config,
                "before_state": before_state,
                "before": {
                    "config_sha256": _local_authority_sha256(
                        self,
                        self.config_path,
                    ),
                    "state_sha256": _local_authority_sha256(self, self.state_path),
                    "release": _file_descriptor(
                        self,
                        self.release_pointer_path,
                    ),
                },
                "target": {
                    "config_sha256": _local_authority_sha256(
                        self,
                        self.config_path,
                    ),
                    "state_sha256": persisted_json_sha256(plan["target_state"]),
                    "receipt_sha256": plan["receipt_sha256"],
                    "release_sha256": persisted_json_sha256(pointer),
                    "stage_8_receipt_sha256": stage_eight_receipt_sha256,
                    "generation_manifest_sha256": (
                        generation.generation_manifest_sha256
                    ),
                    "build_provenance_sha256": persisted_json_sha256(
                        target_provenance["build"]
                    ),
                },
                "target_receipts": target_receipts,
                "before_manifests": {
                    "asset_manifest": _file_descriptor(self, self.manifest_path),
                    "dataset_manifest": _file_descriptor(
                        self,
                        self.artifact_path(
                            PERSISTED_STAGE_VALUES_V2[-1],
                            "dataset_manifest.json",
                        )
                    ),
                    "generation_manifest": _file_descriptor(
                        self,
                        self.artifact_path(
                            PERSISTED_STAGE_VALUES_V2[-1],
                            "generation_manifest.json",
                        )
                    ),
                },
                "target_manifests": target_manifests,
                "target_provenance": target_provenance,
                "target_state": plan["target_state"],
                "event_entry": plan["event_entry"],
                "result": plan["result"],
                "audit": self._journal_audit_transitions(
                    history_entry=None,
                    event_entry=plan["event_entry"],
                ),
            }
            self._append_journal_once(prepared)
            _fault_point("after_prepared_journal")
            recovery_snapshot = dict(legacy_artifact_snapshot)
            recovery_presence = dict(legacy_artifact_presence)
            recovery_present, recovery_bytes = _optional_local_authority_bytes(
                self,
                self.recovery_journal_path,
            )
            if not recovery_present:
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "prepared adoption journal authority is missing",
                )
            recovery_presence[self.recovery_journal_path] = True
            recovery_snapshot[self.recovery_journal_path] = recovery_bytes

            def check_legacy_generation_inventory() -> None:
                if _capture_legacy_generation_inventory(
                    self,
                    generation_id=generation.generation_id,
                    descriptor=generation.descriptor,
                    split_payloads=generation_split_payloads,
                ) != generation_inventory:
                    raise ValueError(
                        "legacy generation inventory changed before adoption"
                    )

            self._roll_forward_prepared(
                prepared,
                legacy_artifact_snapshot=recovery_snapshot,
                legacy_artifact_presence=recovery_presence,
                legacy_generation_precondition=check_legacy_generation_inventory,
            )
            return self.load_state()

    def _prepare_legacy_release_artifacts(
        self,
        config: EvaluationAssetConfig,
        timestamp: str,
        artifact_snapshot: Mapping[Path, bytes],
        artifact_presence: Mapping[Path, bool],
    ) -> tuple[
        InstalledGeneration,
        dict[str, Any],
        dict[str, Any],
        dict[str, Path],
        dict[str, bytes],
        tuple[tuple[str, int, int, tuple[tuple[str, str], ...]], ...],
    ]:
        """Plan exact adoption provenance and generation targets without writes."""
        input_manifest_path = self.artifact_path(
            PERSISTED_STAGE_VALUES_V2[0],
            "input_manifest.json",
        )
        input_manifest = parse_strict_json_object(
            artifact_snapshot[input_manifest_path]
        )
        copied_inputs = {}
        for name, path in (
            ("labeled_feedback", self.historical_feedback_path),
            ("unlabeled", self.historical_unlabeled_path),
        ):
            details = input_manifest["inputs"][name]
            input_bytes = artifact_snapshot[path]
            copied_inputs[name] = {
                "path": path.relative_to(self.root).as_posix(),
                "bytes": len(input_bytes),
                "rows": details["rows"],
                "sha256": details["sha256"],
            }
        lineage = (
            parse_strict_json_object(artifact_snapshot[self.lineage_path])
            if self.lineage_path in artifact_snapshot
            else None
        )
        provenance = build_legacy_provenance(
            resolved_configuration=config.to_dict(),
            copied_inputs=copied_inputs,
            lineage=lineage,
            split_seed=config.split_seed,
            created_at=timestamp,
        )
        persisted_stages = _persisted_stages_v2()
        provenance_paths = [
            self.stage_provenance_path(stage) for stage in persisted_stages
        ]
        if any(
            artifact_presence.get(path, False)
            for path in (*provenance_paths, self.build_provenance_path)
        ):
            raise ValueError("unjournaled adoption provenance authority is ambiguous")
        target_provenance = {
            "stages": {
                stage: build_legacy_stage_provenance(stage)
                for stage in persisted_stages
            },
            "build": provenance,
        }
        split_paths = {
            split: self.artifact_path(
                PERSISTED_STAGE_VALUES_V2[-1],
                f"{split}.jsonl",
            )
            for split in ("train", "validation", "test", "regression_trusted")
        }
        split_payloads = {
            split: artifact_snapshot[path]
            for split, path in split_paths.items()
        }
        descriptor = build_generation_descriptor(
            split_paths,
            provenance["identity_sha256"],
            trusted_root=self.tenant_root,
            split_payloads=split_payloads,
        )
        generation_id = generation_id_for_descriptor(descriptor)
        generation_inventory = _capture_legacy_generation_inventory(
            self,
            generation_id=generation_id,
            descriptor=descriptor,
            split_payloads=split_payloads,
        )
        if generation_inventory:
            raise ValueError("unjournaled adoption generation authority is ambiguous")
        _validate_asset_write_targets(
            self.root,
            [
                *provenance_paths,
                self.build_provenance_path,
                *(self.receipt_path(stage) for stage in persisted_stages),
                self.manifest_path,
                self.artifact_path(
                    PERSISTED_STAGE_VALUES_V2[-1],
                    "dataset_manifest.json",
                ),
                self.artifact_path(
                    PERSISTED_STAGE_VALUES_V2[-1],
                    "generation_manifest.json",
                ),
                self.state_path,
                self.events_path,
                self.recovery_journal_path,
            ],
        )
        _validate_asset_write_targets(
            self.tenant_root,
            [self.release_pointer_path],
        )
        _validate_asset_write_targets(
            self.tenant_root,
            [
                self.published_datasets,
                self.generations_root,
                self.generations_root / generation_id,
            ],
            target_kind="directory",
        )
        if _capture_legacy_generation_inventory(
            self,
            generation_id=generation_id,
            descriptor=descriptor,
            split_payloads=split_payloads,
        ) != generation_inventory:
            raise ValueError("legacy generation inventory changed before adoption")
        _assert_legacy_authority_unchanged(
            self,
            artifact_snapshot,
            artifact_presence,
        )
        if _capture_legacy_generation_inventory(
            self,
            generation_id=generation_id,
            descriptor=descriptor,
            split_payloads=split_payloads,
        ) != generation_inventory:
            raise ValueError("legacy generation inventory changed before first write")

        generation_manifest = build_generation_manifest(
            tenant_id=self.tenant_id,
            asset_id=self.asset_id,
            descriptor=descriptor,
        )
        generation_dir = self.generations_root / generation_id
        generation = InstalledGeneration(
            generation_id=generation_id,
            generation_dir=generation_dir,
            generation_manifest_sha256=persisted_json_sha256(
                generation_manifest
            ),
            descriptor=descriptor,
            manifest=generation_manifest,
            files={
                split: generation_dir / f"{split}.jsonl"
                for split in LOGICAL_SPLITS
            },
        )
        manifest = parse_strict_json_object(
            artifact_snapshot[self.manifest_path]
        )
        generation_directory = self.repository_relative_path(
            generation.generation_dir
        )
        manifest["published_datasets"] = {
            "directory": self.published_datasets.relative_to(
                self.tenant_root
            ).as_posix(),
            "release_pointer": self.release_pointer_path.relative_to(
                self.tenant_root
            ).as_posix(),
            "generation_id": generation.generation_id,
            "generation_manifest_sha256": generation.generation_manifest_sha256,
            "build_provenance_sha256": persisted_json_sha256(provenance),
            "build_fingerprint": provenance["identity_sha256"],
            "files": {
                split: f"{generation_directory}/{split}.jsonl"
                for split in ("train", "validation", "test", "regression_trusted")
            },
        }
        return (
            generation,
            {
                "asset_manifest": manifest,
                "dataset_manifest": manifest,
                "generation_manifest": generation_manifest,
            },
            target_provenance,
            split_paths,
            split_payloads,
            generation_inventory,
        )

    def _adoption_manifest_overrides(
        self,
        manifests: Mapping[str, Any],
    ) -> dict[Path, bytes]:
        """Return exact prospective bytes for pre-WAL adoption verification."""
        return {
            self.manifest_path: _persisted_json_bytes(manifests["asset_manifest"]),
            self.artifact_path(
                PERSISTED_STAGE_VALUES_V2[-1],
                "dataset_manifest.json",
            ): _persisted_json_bytes(manifests["dataset_manifest"]),
            self.artifact_path(
                PERSISTED_STAGE_VALUES_V2[-1],
                "generation_manifest.json",
            ): _persisted_json_bytes(manifests["generation_manifest"]),
        }

    def load_config(self) -> EvaluationAssetConfig:
        """Load this asset's persisted configuration."""
        return EvaluationAssetConfig.from_dict(
            parse_strict_json_object(_local_authority_bytes(self, self.config_path))
        )

    def load_state(self) -> PipelineState:
        """Load this asset's persisted run state."""
        authority = _local_authority_bytes(self, self.state_path)
        raw = parse_strict_json_object(authority)
        if raw.get("schema_version") == STATE_SCHEMA_VERSION:
            raw_stages = raw.get("stages")
            exact_persisted_stage_inventory = (
                isinstance(raw_stages, list)
                and tuple(
                    item.get("stage") if isinstance(item, Mapping) else None
                    for item in raw_stages
                )
                == PERSISTED_STAGE_VALUES_V2
            )
            completed_handoff = (
                raw.get("status") == "running"
                and exact_persisted_stage_inventory
                and all(
                    isinstance(item, Mapping)
                    and item.get("status") == "completed"
                    and item.get("receipt_sha256") is not None
                    for item in raw_stages
                )
            )
            state = _exact_v2_state(
                raw,
                historical=raw.get("status") == "released" or completed_handoff,
            )
            setattr(state, "_persisted_authority_bytes", authority)
            return state
        try:
            legacy = normalized_legacy_completed_state_v1(raw)
        except ValueError:
            state = PipelineState.from_dict(raw)
        else:
            state = PipelineState(
                tenant_id=str(legacy["tenant_id"]),
                asset_id=str(legacy["asset_id"]),
                schema_version=str(legacy["schema_version"]),
                status=str(legacy["status"]),
                current_stage=(
                    str(legacy["current_stage"])
                    if legacy["current_stage"] is not None
                    else None
                ),
                created_at=str(legacy["created_at"]),
                updated_at=str(legacy["updated_at"]),
                error=str(legacy["error"]) if legacy["error"] is not None else None,
                counts={str(key): int(value) for key, value in legacy["counts"].items()},
                stages=[StageState(**dict(item)) for item in legacy["stages"]],
                mutation_sequence=int(legacy["mutation_sequence"]),
                last_operation_id=(
                    str(legacy["last_operation_id"])
                    if legacy["last_operation_id"] is not None
                    else None
                ),
            )
        setattr(state, "_persisted_authority_bytes", authority)
        return state

    def save_state(self, state: PipelineState) -> None:
        """Atomically persist run state."""
        expected = getattr(state, "_persisted_authority_bytes", None)
        if not isinstance(expected, bytes):
            present, current = _optional_local_authority_bytes(self, self.state_path)
            expected = current if present else None
        state.updated_at = utc_now()
        payload = state.to_dict()
        self._write_authority_json(
            self.state_path,
            payload,
            expected_current=expected,
            check_expected_current=True,
        )
        setattr(state, "_persisted_authority_bytes", _persisted_json_bytes(payload))

    def _publish_release_locked(
        self,
        state: PipelineState,
        generation: InstalledGeneration,
    ) -> PipelineState:
        """Publish one complete generation through the authenticated v2 WAL."""
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        stage_eight_receipt_sha256 = _local_authority_sha256(
            self,
            self.receipt_path(PERSISTED_STAGE_VALUES_V2[-1]),
        )
        pointer = build_release_pointer(
            tenant_id=self.tenant_id,
            asset_id=self.asset_id,
            generation=generation,
            stage_8_receipt_sha256=stage_eight_receipt_sha256,
            build_provenance_sha256=_local_authority_sha256(
                self,
                self.build_provenance_path,
            ),
            published_at=timestamp,
        )
        before_config = self.load_config().to_dict()
        before_state = state.to_dict()
        plan = derive_release_publication_plan(
            before_config,
            before_state,
            pointer,
            operation_id=operation_id,
            prepared_at=timestamp,
        )
        release_before = _file_descriptor(self, self.release_pointer_path)
        prepared = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "operation_id": operation_id,
            "kind": "release_publication",
            "phase": "prepared",
            "prepared_at": timestamp,
            "request": {"release_pointer": pointer},
            "before_config": before_config,
            "before_state": before_state,
            "before": {
                "config_sha256": _local_authority_sha256(self, self.config_path),
                "state_sha256": _local_authority_sha256(self, self.state_path),
                "release": release_before,
            },
            "target": {
                "config_sha256": _local_authority_sha256(self, self.config_path),
                "state_sha256": persisted_json_sha256(plan["target_state"]),
                "release_sha256": persisted_json_sha256(pointer),
                "stage_8_receipt_sha256": stage_eight_receipt_sha256,
                "generation_manifest_sha256": (
                    generation.generation_manifest_sha256
                ),
                "build_provenance_sha256": _local_authority_sha256(
                    self,
                    self.build_provenance_path,
                ),
            },
            "target_state": plan["target_state"],
            "event_entry": plan["event_entry"],
            "result": plan["result"],
            "audit": self._journal_audit_transitions(
                history_entry=None,
                event_entry=plan["event_entry"],
            ),
        }
        self._append_journal_once(prepared)
        _fault_point("after_release_publication_prepared")
        target_state = _exact_completed_state(plan["target_state"])
        verify_release_candidate(
            self,
            target_state,
            release_pointer=pointer,
        )
        asset_authority = _capture_local_authority_tree(
            self.root,
            self.tenants_root,
        )
        generation_authority = _capture_local_authority_tree(
            generation.generation_dir,
            self.tenant_root,
        )
        _fault_point("before_release_pointer_replace")
        verify_release_candidate(
            self,
            target_state,
            release_pointer=pointer,
        )
        if (
            _capture_local_authority_tree(self.root, self.tenants_root)
            != asset_authority
            or _capture_local_authority_tree(
                generation.generation_dir,
                self.tenant_root,
            )
            != generation_authority
        ):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "release candidate authority changed before pointer installation",
            )
        pointer_preexisting, pointer_bytes = _release_pointer_write_expectation(
            self,
            release_before,
        )
        installed_pointer_identity: tuple[int, int, int] | None = None
        try:
            installed_pointer = write_release_pointer(
                self.published_datasets,
                pointer,
                trusted_root=self.tenant_root,
                expected_current=pointer_bytes,
                check_expected_current=True,
            )
            installed_pointer_identity = installed_pointer.identity
            if installed_pointer_identity is None:
                raise ValueError("installed release pointer identity is unavailable")
            resolved = resolve_evaluation_asset_release(
                self.published_datasets,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                expected_stage_8_receipt_sha256=stage_eight_receipt_sha256,
                trusted_root=self.tenant_root,
            )
            if resolved.pointer_sha256 != prepared["target"]["release_sha256"]:
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "installed release pointer does not match its WAL target",
                )
            verify_release_candidate(self, target_state)
        except Exception:
            _rollback_new_release_pointer(
                self,
                preexisting=pointer_preexisting,
                pointer=pointer,
                installed_identity=installed_pointer_identity,
            )
            raise
        _fault_point("after_release_pointer_replace")
        _fault_point("after_release_pointer_verify")
        try:
            self._write_authority_json(
                self.state_path,
                plan["target_state"],
                expected_current=_state_authority_expectation(state, before_state),
                check_expected_current=True,
            )
            verify_released_asset(self, target_state)
        except Exception:
            _handle_release_state_failure(
                self,
                before_state=before_state,
                target_state=plan["target_state"],
                preexisting=pointer_preexisting,
                pointer=pointer,
                installed_identity=installed_pointer_identity,
            )
            raise
        _fault_point("after_released_state_replace")
        self._append_jsonl_once(self.events_path, plan["event_entry"])
        _fault_point("after_release_event_append")
        self._commit_journal_operation(prepared)
        _fault_point("after_release_publication_commit")
        verify_released_asset(self, target_state)
        return target_state

    def revise_config(
        self,
        updates: Mapping[str, Any],
        *,
        lock_timeout: float = 0,
    ) -> Dict[str, Any]:
        """Persist decision changes and invalidate their dependent stages."""
        with self.asset_lock(lock_timeout):
            self._recover_locked()
            return self._revise_config_locked(updates)

    @staticmethod
    def _resolve_config_updates(
        current: EvaluationAssetConfig,
        updates: Mapping[str, Any],
    ) -> EvaluationAssetConfig:
        """Resolve a proposed decision update without touching authority files."""
        unknown = set(updates) - set(CONFIG_STAGE_DEPENDENCIES)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unsupported pipeline decision fields: {names}")
        merged = current.to_dict()
        merged.update(dict(updates))
        if "embedding_model" in updates:
            merged["embedding_provider"] = (
                "tfidf" if updates["embedding_model"] == "tfidf" else "openai"
            )
        return EvaluationAssetConfig.from_dict(merged)

    def _revise_config_locked(self, updates: Mapping[str, Any]) -> Dict[str, Any]:
        """Revise configuration while the caller holds the asset lock."""
        state = self.load_state()
        if state.status == "released":
            verify_released_asset(self, state)
            raise EvaluationAssetImmutableError(self.tenant_id, self.asset_id)
        if state.legacy_completed:
            raise EvaluationAssetLegacyError(
                self.tenant_id,
                self.asset_id,
                "explicit verification and adoption are required before revision",
        )
        verify_raw_snapshot_floor(self, state)
        current = self.load_config()
        revised = self._resolve_config_updates(current, updates)
        changes = {
            key: {"previous": current.to_dict()[key], "new": revised.to_dict()[key]}
            for key in CONFIG_STAGE_DEPENDENCIES
            if current.to_dict()[key] != revised.to_dict()[key]
        }
        if not changes:
            return {
                "changed_fields": {},
                "invalidated_from_stage": None,
                "resume_from_stage": None,
            }

        revision = self._config_revision_count() + 1
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        before_config = current.to_dict()
        before_state = state.to_dict()
        plan = derive_revision_plan(
            before_config,
            before_state,
            updates,
            operation_id=operation_id,
            prepared_at=timestamp,
            revision=revision,
        )
        target_state = PipelineState.from_dict(plan["target_state"])
        result = dict(plan["result"])
        prepared = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "operation_id": operation_id,
            "kind": "configuration_revision",
            "phase": "prepared",
            "prepared_at": timestamp,
            "request": {"updates": dict(updates)},
            "before_config": before_config,
            "before_state": before_state,
            "before": {
                "config_sha256": _local_authority_sha256(self, self.config_path),
                "state_sha256": _local_authority_sha256(self, self.state_path),
            },
            "target": {
                "config_sha256": persisted_json_sha256(plan["target_config"]),
                "state_sha256": persisted_json_sha256(plan["target_state"]),
            },
            "target_config": plan["target_config"],
            "target_state": plan["target_state"],
            "history_entry": plan["history_entry"],
            "event_entry": plan["event_entry"],
            "invalidated_stages": plan["invalidated_stages"],
            "result": result,
            "audit": self._journal_audit_transitions(
                history_entry=plan["history_entry"],
                event_entry=plan["event_entry"],
            ),
        }
        self._append_journal_once(prepared)
        _fault_point("after_prepared_journal")
        self._write_authority_json(
            self.config_path,
            plan["target_config"],
            expected_current=_persisted_json_bytes(before_config),
            check_expected_current=True,
        )
        _fault_point("after_config_replace")
        self._write_authority_json(
            self.state_path,
            target_state.to_dict(),
            expected_current=_state_authority_expectation(state, before_state),
            check_expected_current=True,
        )
        _fault_point("after_state_replace")
        self._append_jsonl_once(self.config_history_path, plan["history_entry"])
        _fault_point("after_history_append")
        self._append_jsonl_once(self.events_path, plan["event_entry"])
        _fault_point("after_event_append")
        _fault_point("before_cleanup")
        self._clear_stage_outputs(
            [PipelineStage(value) for value in plan["invalidated_stages"]]
        )
        self._commit_journal_operation(prepared)
        return result

    def recover(self, *, lock_timeout: float = 0) -> list[str]:
        """Roll every prepared recovery operation forward exactly once."""
        with self.asset_lock(lock_timeout):
            return self._recover_locked()

    def _recover_locked(self) -> list[str]:
        """Recover prepared operations while the caller holds the asset lock."""
        _validate_local_authority_layout(self)
        entries = self._read_control_log(self.recovery_journal_path)
        legacy_artifact_snapshot: dict[Path, bytes] | None = None
        legacy_artifact_presence: dict[Path, bool] | None = None
        legacy_generation_precondition: Callable[[], None] | None = None
        try:
            journal = validate_recovery_journal(self, entries)
            outstanding = journal.outstanding
            if outstanding is not None and outstanding.get("kind") == "legacy_adoption":
                target_state = PipelineState.from_dict(outstanding["target_state"])
                before_state = PipelineState.from_dict(outstanding["before_state"])
                request = outstanding.get("request")
                prepared_release = (
                    request.get("release_pointer")
                    if isinstance(request, Mapping)
                    else None
                )
                if not isinstance(prepared_release, Mapping):
                    raise ValueError("adoption release target is invalid")
                _validate_source_rows(self.historical_feedback_path, labeled=True)
                _validate_source_rows(self.historical_unlabeled_path, labeled=False)
                target_receipts = outstanding.get("target_receipts")
                if not isinstance(target_receipts, Mapping):
                    raise ValueError("adoption receipt target is invalid")
                target_manifests = outstanding.get("target_manifests")
                if not isinstance(target_manifests, Mapping):
                    raise ValueError("adoption manifest target is invalid")
                target_asset_manifest = target_manifests.get("asset_manifest")
                if not isinstance(target_asset_manifest, Mapping):
                    raise ValueError("adoption manifest target is invalid")
                legacy_artifact_snapshot = {}
                legacy_artifact_presence = {}
                for path in (
                    self.state_path,
                    self.config_path,
                    self.config_history_path,
                    self.events_path,
                    self.recovery_journal_path,
                    self.lineage_path,
                ):
                    present, payload = _optional_local_authority_bytes(self, path)
                    legacy_artifact_presence[path] = present
                    if present:
                        legacy_artifact_snapshot[path] = payload
                raw_config = parse_strict_json_object(
                    legacy_artifact_snapshot[self.config_path]
                )
                legacy_config = EvaluationAssetConfig.from_dict(raw_config)
                if legacy_config.to_dict() != raw_config:
                    raise ValueError(
                        "adoption recovery configuration is not type-exact"
                    )
                legacy_artifact_paths: dict[tuple[str, str], Path] = {}
                validate_legacy_release_candidate(
                    self,
                    before_state,
                    legacy_config,
                    prepared_release=prepared_release,
                    manifest_payload=target_asset_manifest,
                    artifact_snapshot_out=legacy_artifact_snapshot,
                    artifact_presence_out=legacy_artifact_presence,
                    artifact_paths_out=legacy_artifact_paths,
                )
                legacy_history = _exact_pre_v2_history_from_authority(
                    self,
                    outstanding["before_state"],
                    artifact_overrides=legacy_artifact_snapshot,
                )
                if legacy_config.to_dict() != dict(
                    legacy_history.final_configuration
                ):
                    raise ValueError(
                        "adoption recovery configuration history is inconsistent"
                    )
                target_provenance = outstanding.get("target_provenance")
                if not isinstance(target_provenance, Mapping) or not isinstance(
                    target_provenance.get("stages"), Mapping
                ) or not isinstance(target_provenance.get("build"), Mapping):
                    raise ValueError("adoption provenance target is invalid")
                generated_provenance_paths = (
                    *(
                        self.stage_provenance_path(stage)
                        for stage in _persisted_stages_v2()
                    ),
                    self.build_provenance_path,
                )
                for path in generated_provenance_paths:
                    present, payload = _optional_local_authority_bytes(self, path)
                    legacy_artifact_presence[path] = present
                    if present:
                        legacy_artifact_snapshot[path] = payload
                artifact_overrides = {
                    **legacy_artifact_snapshot,
                    **self._adoption_manifest_overrides(target_manifests),
                    **{
                        self.stage_provenance_path(stage): _persisted_json_bytes(
                            target_provenance["stages"][stage]
                        )
                        for stage in _persisted_stages_v2()
                    },
                    self.build_provenance_path: _persisted_json_bytes(
                        target_provenance["build"]
                    ),
                }
                _verify_prospective_legacy_adoption_candidate(
                    self,
                    target_state,
                    {
                        stage: target_receipts[stage]
                        for stage in _persisted_stages_v2()
                    },
                    legacy_state=before_state,
                    artifact_overrides=artifact_overrides,
                    artifact_path_overrides=legacy_artifact_paths,
                )
                target_generation_manifest = target_manifests.get(
                    "generation_manifest"
                )
                if not isinstance(target_generation_manifest, Mapping) or not isinstance(
                    target_generation_manifest.get("descriptor"),
                    Mapping,
                ):
                    raise ValueError("adoption generation target is invalid")
                generation_id = str(prepared_release.get("generation_id") or "")
                generation_descriptor = target_generation_manifest["descriptor"]
                split_payloads = {
                    split: legacy_artifact_snapshot[
                        self.artifact_path(
                            PERSISTED_STAGE_VALUES_V2[-1],
                            f"{split}.jsonl",
                        )
                    ]
                    for split in LOGICAL_SPLITS
                }
                generation_inventory = _capture_legacy_generation_inventory(
                    self,
                    generation_id=generation_id,
                    descriptor=generation_descriptor,
                    split_payloads=split_payloads,
                )

                def check_legacy_generation_inventory() -> None:
                    if _capture_legacy_generation_inventory(
                        self,
                        generation_id=generation_id,
                        descriptor=generation_descriptor,
                        split_payloads=split_payloads,
                    ) != generation_inventory:
                        raise ValueError(
                            "adoption generation inventory changed before recovery"
                        )

                legacy_generation_precondition = check_legacy_generation_inventory
            if (
                legacy_artifact_snapshot is not None
                and legacy_artifact_presence is not None
            ):
                _assert_legacy_authority_unchanged(
                    self,
                    legacy_artifact_snapshot,
                    legacy_artifact_presence,
                )
        except (
            EvaluationAssetLegacyError,
            KeyError,
            OSError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "recovery journal authority is inconsistent",
            ) from exc
        committed = {
            str(row.get("operation_id"))
            for row in entries
            if row.get("phase") == "committed"
        }
        recovered: list[str] = []
        for entry in entries:
            operation_id = str(entry.get("operation_id") or "")
            if entry.get("phase") != "prepared" or operation_id in committed:
                continue
            if (
                entry.get("kind") == "legacy_adoption"
                and legacy_artifact_snapshot is not None
                and legacy_artifact_presence is not None
            ):
                try:
                    _assert_legacy_authority_unchanged(
                        self,
                        legacy_artifact_snapshot,
                        legacy_artifact_presence,
                    )
                except (OSError, ValueError) as exc:
                    raise EvaluationAssetIntegrityError(
                        self.tenant_id,
                        self.asset_id,
                        "recovery journal authority changed before roll-forward",
                    ) from exc
            self._roll_forward_prepared(
                entry,
                legacy_artifact_snapshot=legacy_artifact_snapshot,
                legacy_artifact_presence=legacy_artifact_presence,
                legacy_generation_precondition=legacy_generation_precondition,
            )
            recovered.append(operation_id)
            committed.add(operation_id)
        current_state = self.load_state()
        if current_state.status == "released":
            verify_released_asset(self, current_state)
        return recovered

    def _roll_forward_prepared(
        self,
        entry: Mapping[str, Any],
        *,
        legacy_artifact_snapshot: Mapping[Path, bytes] | None = None,
        legacy_artifact_presence: Mapping[Path, bool] | None = None,
        legacy_generation_precondition: Callable[[], None] | None = None,
    ) -> None:
        kind = entry.get("kind")
        if kind == "release_publication":
            request = entry.get("request")
            pointer = (
                request.get("release_pointer")
                if isinstance(request, Mapping)
                else None
            )
            target_state = entry.get("target_state")
            if not isinstance(pointer, Mapping) or not isinstance(
                target_state, Mapping
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing release targets",
                )
            generation_id = str(pointer.get("generation_id") or "")
            generation = validate_historical_generation(
                self.generations_root / generation_id,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                trusted_root=self.tenant_root,
            )
            target = entry.get("target")
            if not isinstance(target, Mapping) or (
                generation.generation_manifest_sha256
                != target.get("generation_manifest_sha256")
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery generation does not match its WAL target",
                )
            recovered_state = _exact_completed_state(target_state)
            verify_release_candidate(
                self,
                recovered_state,
                release_pointer=pointer,
            )
            asset_authority = _capture_local_authority_tree(
                self.root,
                self.tenants_root,
            )
            generation_authority = _capture_local_authority_tree(
                generation.generation_dir,
                self.tenant_root,
            )
            verify_release_candidate(
                self,
                recovered_state,
                release_pointer=pointer,
            )
            if (
                _capture_local_authority_tree(self.root, self.tenants_root)
                != asset_authority
                or _capture_local_authority_tree(
                    generation.generation_dir,
                    self.tenant_root,
                )
                != generation_authority
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "release candidate authority changed before pointer installation",
                )
            before = entry.get("before")
            if not isinstance(before, Mapping) or not isinstance(
                before.get("release"),
                Mapping,
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing prior release authority",
                )
            pointer_preexisting, pointer_bytes = _release_pointer_write_expectation(
                self,
                before["release"],
                owned_retry=pointer,
            )
            installed_pointer_identity: tuple[int, int, int] | None = None
            try:
                installed_pointer = write_release_pointer(
                    self.published_datasets,
                    pointer,
                    trusted_root=self.tenant_root,
                    expected_current=pointer_bytes,
                    check_expected_current=True,
                )
                installed_pointer_identity = installed_pointer.identity
                if installed_pointer_identity is None:
                    raise ValueError("installed release pointer identity is unavailable")
                resolved = resolve_evaluation_asset_release(
                    self.published_datasets,
                    expected_tenant_id=self.tenant_id,
                    expected_asset_id=self.asset_id,
                    expected_stage_8_receipt_sha256=str(
                        target.get("stage_8_receipt_sha256") or ""
                    ),
                    trusted_root=self.tenant_root,
                )
                if resolved.pointer_sha256 != target.get("release_sha256"):
                    raise EvaluationAssetIntegrityError(
                        self.tenant_id,
                        self.asset_id,
                        "the recovered release pointer does not match its WAL target",
                    )
                verify_release_candidate(self, recovered_state)
            except Exception:
                _rollback_new_release_pointer(
                    self,
                    preexisting=pointer_preexisting,
                    pointer=pointer,
                    installed_identity=installed_pointer_identity,
                )
                raise
            before_state = entry.get("before_state")
            if not isinstance(before_state, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing prior state authority",
                )
            expected_state = _wal_json_write_expectation(
                self,
                self.state_path,
                before_state,
                target_state,
            )
            try:
                self._write_authority_json(
                    self.state_path,
                    target_state,
                    expected_current=expected_state,
                    check_expected_current=True,
                )
                verify_released_asset(self, recovered_state)
            except Exception:
                _handle_release_state_failure(
                    self,
                    before_state=before_state,
                    target_state=target_state,
                    preexisting=pointer_preexisting,
                    pointer=pointer,
                    installed_identity=installed_pointer_identity,
                )
                raise
            event_entry = entry.get("event_entry")
            if isinstance(event_entry, Mapping):
                self._append_jsonl_once(self.events_path, event_entry)
            self._commit_journal_operation(entry)
            verify_released_asset(self, recovered_state)
            return
        if kind == "legacy_adoption":
            if (
                legacy_artifact_snapshot is None
                or legacy_artifact_presence is None
                or legacy_generation_precondition is None
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing its legacy authority snapshot",
                )

            adoption_write_checked = False

            def adoption_write_precondition() -> None:
                nonlocal adoption_write_checked
                if adoption_write_checked:
                    return
                try:
                    _assert_legacy_authority_unchanged(
                        self,
                        legacy_artifact_snapshot,
                        legacy_artifact_presence,
                    )
                    legacy_generation_precondition()
                except (OSError, ValueError) as exc:
                    raise EvaluationAssetIntegrityError(
                        self.tenant_id,
                        self.asset_id,
                        "legacy authority changed at the recovery write boundary",
                    ) from exc
                adoption_write_checked = True

            self._install_adoption_provenance(
                entry,
                precondition=adoption_write_precondition,
            )
            self._install_adoption_generation(
                entry,
                legacy_artifact_snapshot=legacy_artifact_snapshot,
                precondition=adoption_write_precondition,
            )
            self._install_adoption_manifests(
                entry,
                precondition=adoption_write_precondition,
            )
            self._install_adoption_receipts(
                entry,
                precondition=adoption_write_precondition,
            )
            _fault_point("after_receipts_install")
            request = entry.get("request")
            pointer = (
                request.get("release_pointer")
                if isinstance(request, Mapping)
                else None
            )
            if not isinstance(pointer, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing its adoption pointer",
                )
            target_state = entry.get("target_state")
            if not isinstance(target_state, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing target state",
                )
            recovered_state = _exact_completed_state(target_state)
            verify_release_candidate(
                self,
                recovered_state,
                release_pointer=pointer,
            )
            generation_id = str(pointer.get("generation_id") or "")
            generation_dir = self.generations_root / generation_id
            asset_authority = _capture_local_authority_tree(
                self.root,
                self.tenants_root,
            )
            generation_authority = _capture_local_authority_tree(
                generation_dir,
                self.tenant_root,
            )
            verify_release_candidate(
                self,
                recovered_state,
                release_pointer=pointer,
            )
            if (
                _capture_local_authority_tree(self.root, self.tenants_root)
                != asset_authority
                or _capture_local_authority_tree(
                    generation_dir,
                    self.tenant_root,
                )
                != generation_authority
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "adoption candidate authority changed before pointer installation",
                )
            before = entry.get("before")
            if not isinstance(before, Mapping) or not isinstance(
                before.get("release"),
                Mapping,
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing prior adoption release authority",
                )
            pointer_preexisting, pointer_bytes = _release_pointer_write_expectation(
                self,
                before["release"],
                owned_retry=pointer,
            )
            installed_pointer_identity: tuple[int, int, int] | None = None
            try:
                installed_pointer = write_release_pointer(
                    self.published_datasets,
                    pointer,
                    trusted_root=self.tenant_root,
                    expected_current=pointer_bytes,
                    check_expected_current=True,
                )
                installed_pointer_identity = installed_pointer.identity
                if installed_pointer_identity is None:
                    raise ValueError("installed release pointer identity is unavailable")
                _fault_point("after_adoption_pointer_replace")
                resolve_evaluation_asset_release(
                    self.published_datasets,
                    expected_tenant_id=self.tenant_id,
                    expected_asset_id=self.asset_id,
                    expected_stage_8_receipt_sha256=str(
                        pointer.get("stage_8_receipt_sha256") or ""
                    ),
                    trusted_root=self.tenant_root,
                )
                verify_release_candidate(self, recovered_state)
            except Exception:
                _rollback_new_release_pointer(
                    self,
                    preexisting=pointer_preexisting,
                    pointer=pointer,
                    installed_identity=installed_pointer_identity,
                )
                raise
            before_state = entry.get("before_state")
            if not isinstance(before_state, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing prior state authority",
                )
            expected_state = _wal_json_write_expectation(
                self,
                self.state_path,
                before_state,
                target_state,
            )
            try:
                self._write_authority_json(
                    self.state_path,
                    target_state,
                    expected_current=expected_state,
                    check_expected_current=True,
                )
                verify_released_asset(self, recovered_state)
            except Exception:
                _handle_release_state_failure(
                    self,
                    before_state=before_state,
                    target_state=target_state,
                    preexisting=pointer_preexisting,
                    pointer=pointer,
                    installed_identity=installed_pointer_identity,
                )
                raise
            _fault_point("after_state_replace")
            event_entry = entry.get("event_entry")
            if isinstance(event_entry, Mapping):
                self._append_jsonl_once(self.events_path, event_entry)
            _fault_point("after_event_append")
            self._commit_journal_operation(entry)
            return
        if kind not in {"configuration_revision", "checkpoint_rebuild"}:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal contains an unsupported operation",
            )
        target_config = entry.get("target_config")
        if isinstance(target_config, Mapping):
            before_config = entry.get("before_config")
            if not isinstance(before_config, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing prior config authority",
                )
            expected_config = _wal_json_write_expectation(
                self,
                self.config_path,
                before_config,
                target_config,
            )
            self._write_authority_json(
                self.config_path,
                target_config,
                expected_current=expected_config,
                check_expected_current=True,
            )
        target_state = entry.get("target_state")
        if not isinstance(target_state, Mapping):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal is missing target state",
            )
        before_state = entry.get("before_state")
        if not isinstance(before_state, Mapping):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal is missing prior state authority",
            )
        expected_state = _wal_json_write_expectation(
            self,
            self.state_path,
            before_state,
            target_state,
        )
        self._write_authority_json(
            self.state_path,
            target_state,
            expected_current=expected_state,
            check_expected_current=True,
        )
        history_entry = entry.get("history_entry")
        if isinstance(history_entry, Mapping):
            self._append_jsonl_once(self.config_history_path, history_entry)
        event_entry = entry.get("event_entry")
        if isinstance(event_entry, Mapping):
            self._append_jsonl_once(self.events_path, event_entry)
        invalidated = entry.get("invalidated_stages")
        if not isinstance(invalidated, list):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal is missing its cleanup boundary",
            )
        try:
            stages = [PipelineStage(str(stage)) for stage in invalidated]
        except ValueError as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an invalid cleanup boundary",
            ) from exc
        self._clear_stage_outputs(stages)
        self._commit_journal_operation(entry)

    def _install_adoption_provenance(
        self,
        entry: Mapping[str, Any],
        *,
        precondition: Callable[[], None] | None = None,
    ) -> None:
        """Install the exact WAL-owned provenance prefix idempotently."""
        target = entry.get("target_provenance")
        if not isinstance(target, Mapping) or set(target) != {"stages", "build"}:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an invalid provenance target",
            )
        stages = target.get("stages")
        if not isinstance(stages, Mapping) or set(stages) != set(
            _persisted_stages_v2()
        ):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an incomplete provenance target",
            )
        targets = [
            (
                self.stage_provenance_path(stage),
                stages[stage],
                f"after_adoption_provenance_{stage}",
            )
            for stage in _persisted_stages_v2()
        ]
        targets.append(
            (
                self.build_provenance_path,
                target.get("build"),
                "after_adoption_build_provenance",
            )
        )
        for path, payload, fault_name in targets:
            if not isinstance(payload, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal has an invalid provenance payload",
                )
            target_bytes = _persisted_json_bytes(payload)
            present, current_bytes = _optional_local_authority_bytes(self, path)
            if present:
                if current_bytes != target_bytes:
                    raise EvaluationAssetIntegrityError(
                        self.tenant_id,
                        self.asset_id,
                        "adoption provenance authority differs from its WAL target",
                    )
            else:
                self._write_authority_json(
                    path,
                    payload,
                    precondition=precondition,
                    expected_current=None,
                    check_expected_current=True,
                )
            _fault_point(fault_name)

    def _install_adoption_generation(
        self,
        entry: Mapping[str, Any],
        *,
        legacy_artifact_snapshot: Mapping[Path, bytes],
        precondition: Callable[[], None] | None = None,
    ) -> None:
        """Install and authenticate the immutable WAL generation target."""
        manifests = entry.get("target_manifests")
        provenance = entry.get("target_provenance")
        if not isinstance(manifests, Mapping) or not isinstance(
            provenance, Mapping
        ):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal is missing its generation target",
            )
        target_manifest = manifests.get("generation_manifest")
        build = provenance.get("build")
        if not isinstance(target_manifest, Mapping) or not isinstance(
            build, Mapping
        ):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an invalid generation target",
            )
        split_paths = {
            split: self.artifact_path(
                PERSISTED_STAGE_VALUES_V2[-1],
                f"{split}.jsonl",
            )
            for split in LOGICAL_SPLITS
        }
        try:
            split_payloads = {
                split: legacy_artifact_snapshot[path]
                for split, path in split_paths.items()
            }
            if precondition is not None:
                precondition()
            installed = install_generation(
                self.published_datasets,
                tenant_id=self.tenant_id,
                asset_id=self.asset_id,
                split_paths=split_paths,
                split_payloads=split_payloads,
                build_fingerprint=str(build.get("identity_sha256") or ""),
                fault_hook=_fault_point,
                trusted_root=self.tenant_root,
            )
        except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the adoption generation could not be installed",
            ) from exc
        target = entry.get("target")
        if not isinstance(target, Mapping) or (
            installed.generation_id != target_manifest.get("generation_id")
            or installed.manifest != target_manifest
            or installed.descriptor != target_manifest.get("descriptor")
            or installed.generation_manifest_sha256
            != target.get("generation_manifest_sha256")
        ):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the installed generation differs from its WAL target",
            )

    def _install_adoption_receipts(
        self,
        entry: Mapping[str, Any],
        *,
        precondition: Callable[[], None] | None = None,
    ) -> None:
        receipts = entry.get("target_receipts")
        if not isinstance(receipts, Mapping) or set(receipts) != {
            stage for stage in _persisted_stages_v2()
        }:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an incomplete receipt set",
            )
        for stage in _persisted_stages_v2():
            receipt = receipts.get(stage)
            if not isinstance(receipt, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal has an invalid receipt",
                )
            path = self.receipt_path(stage)
            target_bytes = _persisted_json_bytes(receipt)
            present, current_bytes = _optional_local_authority_bytes(self, path)
            if present:
                if current_bytes != target_bytes:
                    raise EvaluationAssetIntegrityError(
                        self.tenant_id,
                        self.asset_id,
                        "adoption receipt authority changed before installation",
                    )
                continue
            self._write_authority_json(
                path,
                receipt,
                precondition=precondition,
                expected_current=None,
                check_expected_current=True,
            )

    def _install_adoption_manifests(
        self,
        entry: Mapping[str, Any],
        *,
        precondition: Callable[[], None] | None = None,
    ) -> None:
        manifests = entry.get("target_manifests")
        if not isinstance(manifests, Mapping) or set(manifests) != {
            "asset_manifest",
            "dataset_manifest",
            "generation_manifest",
        }:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an incomplete adoption manifest set",
            )
        before_manifests = entry.get("before_manifests")
        if not isinstance(before_manifests, Mapping) or set(before_manifests) != {
            "asset_manifest",
            "dataset_manifest",
            "generation_manifest",
        }:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an incomplete prior manifest set",
            )
        targets = (
            (self.manifest_path, "asset_manifest", manifests["asset_manifest"],
             "after_adoption_asset_manifest_replace"),
            (
                self.artifact_path(
                    PERSISTED_STAGE_VALUES_V2[-1],
                    "dataset_manifest.json",
                ),
                "dataset_manifest",
                manifests["dataset_manifest"],
                "after_adoption_dataset_manifest_replace",
            ),
            (
                self.artifact_path(
                    PERSISTED_STAGE_VALUES_V2[-1],
                    "generation_manifest.json",
                ),
                "generation_manifest",
                manifests["generation_manifest"],
                "after_adoption_generation_manifest_replace",
            ),
        )
        for path, name, payload, fault_name in targets:
            if not isinstance(payload, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal has an invalid adoption manifest",
                )
            descriptor = before_manifests.get(name)
            if not isinstance(descriptor, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal has an invalid prior manifest",
                )
            already_target, expected_current = _wal_descriptor_write_expectation(
                self,
                path,
                descriptor,
                payload,
            )
            if not already_target:
                self._write_authority_json(
                    path,
                    payload,
                    precondition=precondition,
                    expected_current=expected_current,
                    check_expected_current=True,
                )
            _fault_point(fault_name)

    def _commit_journal_operation(self, prepared: Mapping[str, Any]) -> None:
        self._append_journal_once(
            {
                "schema_version": JOURNAL_SCHEMA_VERSION,
                "operation_id": str(prepared["operation_id"]),
                "kind": str(prepared["kind"]),
                "phase": "committed",
                "committed_at": utc_now(),
            }
        )

    def _journal_audit_transitions(
        self,
        *,
        history_entry: Mapping[str, Any] | None,
        event_entry: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Authenticate both append-only prefixes before preparing a mutation."""
        history_present, history_bytes = _optional_local_authority_bytes(
            self,
            self.config_history_path,
        )
        events_present, events_bytes = _optional_local_authority_bytes(
            self,
            self.events_path,
        )
        parse_strict_jsonl_objects(history_bytes)
        parse_strict_jsonl_objects(events_bytes)
        return {
            "config_history": derive_audit_transition(
                history_bytes,
                present=history_present,
                appended_row=history_entry,
            ),
            "events": derive_audit_transition(
                events_bytes,
                present=events_present,
                appended_row=event_entry,
            ),
        }

    def _append_journal_once(self, payload: Mapping[str, Any]) -> None:
        self._append_jsonl_once(
            self.recovery_journal_path,
            payload,
            identity_fields=("operation_id", "phase"),
        )

    def _append_jsonl_once(
        self,
        path: Path,
        payload: Mapping[str, Any],
        *,
        identity_fields: Sequence[str] = ("operation_id",),
    ) -> None:
        identity = tuple(payload.get(field) for field in identity_fields)
        if any(
            tuple(row.get(field) for field in identity_fields) == identity
            for row in self._read_control_log(path)
        ):
            return
        self._append_control_row(path, payload)

    def _append_control_row(
        self,
        path: Path,
        payload: Mapping[str, Any],
    ) -> None:
        """Append from bytes captured by one no-follow authority handle."""
        present, before = _optional_local_authority_bytes(self, path)
        if before:
            parse_strict_jsonl_objects(before)
        self._write_authority_text(
            path,
            append_jsonl_bytes(before, payload).decode("utf-8"),
            expected_current=before if present else None,
            check_expected_current=True,
        )

    def _read_control_log(self, path: Path) -> list[Dict[str, Any]]:
        try:
            _, authority = _optional_local_authority_bytes(self, path)
            rows = parse_strict_jsonl_objects(authority)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "a durable control log is malformed",
            ) from exc
        return rows

    def config_revision_summary(self) -> Dict[str, Any]:
        """Return bounded configuration revision metadata for the Studio."""
        present, history_bytes = _optional_local_authority_bytes(
            self,
            self.config_history_path,
        )
        if not present:
            return {"count": 0, "latest": None}
        latest = None
        count = 0
        for line in history_bytes.decode("utf-8").splitlines():
            if not line.strip():
                continue
            count += 1
            latest = json.loads(line)
        return {"count": count, "latest": latest}

    def append_event(
        self,
        event: str,
        details: Optional[Mapping[str, Any]] = None,
        *,
        operation_id: str | None = None,
    ) -> None:
        """Append an audit event after state has been safely persisted."""
        payload = {
            "timestamp": utc_now(),
            "event": event,
            "tenant_id": self.tenant_id,
            "asset_id": self.asset_id,
            "details": dict(details or {}),
        }
        if operation_id is not None:
            payload["operation_id"] = operation_id
        self._append_control_row(self.events_path, payload)

    def _config_revision_count(self) -> int:
        present, history_bytes = _optional_local_authority_bytes(
            self,
            self.config_history_path,
        )
        if not present:
            return 0
        return sum(
            1
            for line in history_bytes.decode("utf-8").splitlines()
            if line.strip()
        )

    def _append_config_revision(self, payload: Mapping[str, Any]) -> None:
        self._append_control_row(self.config_history_path, payload)

    def _clear_stage_outputs(self, stages: Iterable[PipelineStage]) -> None:
        stages = tuple(stages)
        for stage in stages:
            specification = STAGE_SPECIFICATIONS[stage]
            relative_names = list(specification.required_outputs)
            relative_names.extend(specification.legacy_required_outputs)
            if stage == PipelineStage.INTENT_CLUSTERING:
                relative_names.append("cluster_lineage.jsonl")
            for relative_name in relative_names:
                path = self.artifact_path(stage, relative_name)
                remove_local_authority_file(path, self.tenants_root)
            for relative_name in specification.required_asset_outputs:
                path = self.root / relative_name
                remove_local_authority_file(path, self.tenants_root)
            remove_local_authority_file(
                self.receipt_path(stage),
                self.tenants_root,
            )

    def _invalidate_checkpoints_locked(
        self,
        state: PipelineState,
        boundary: PipelineStage,
    ) -> PipelineState:
        """Make a stage suffix nonauthoritative before best-effort cleanup."""
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        before_config = self.load_config().to_dict()
        before_state = state.to_dict()
        plan = derive_rebuild_plan(
            before_config,
            before_state,
            boundary,
            operation_id=operation_id,
            prepared_at=timestamp,
        )
        target_state = PipelineState.from_dict(plan["target_state"])
        prepared = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "operation_id": operation_id,
            "kind": "checkpoint_rebuild",
            "phase": "prepared",
            "prepared_at": timestamp,
            "request": {"boundary": boundary.value},
            "before_config": before_config,
            "before_state": before_state,
            "before": {
                "config_sha256": _local_authority_sha256(self, self.config_path),
                "state_sha256": _local_authority_sha256(self, self.state_path),
            },
            "target": {
                "config_sha256": _local_authority_sha256(self, self.config_path),
                "state_sha256": persisted_json_sha256(plan["target_state"]),
            },
            "target_state": plan["target_state"],
            "event_entry": plan["event_entry"],
            "invalidated_stages": plan["invalidated_stages"],
            "result": plan["result"],
            "audit": self._journal_audit_transitions(
                history_entry=None,
                event_entry=plan["event_entry"],
            ),
        }
        self._append_journal_once(prepared)
        _fault_point("after_prepared_journal")
        self._write_authority_json(
            self.state_path,
            target_state.to_dict(),
            expected_current=_state_authority_expectation(state, before_state),
            check_expected_current=True,
        )
        _fault_point("after_state_replace")
        self._append_jsonl_once(self.events_path, plan["event_entry"])
        _fault_point("after_event_append")
        _fault_point("before_cleanup")
        self._clear_stage_outputs(
            [PipelineStage(value) for value in plan["invalidated_stages"]]
        )
        self._commit_journal_operation(prepared)
        return target_state

    def artifact_summary(self) -> Dict[str, Any]:
        """Return API-safe paths and file counts for the canonical directories."""
        if self.uses_stage_layout:
            directories = [
                (STAGE_DIRECTORIES[stage.value], self.stage_directory(stage))
                for stage in PipelineStage
            ]
        else:
            directories = [
                (name, self.root / name)
                for name in LEGACY_DIRECTORIES
                if (self.root / name).is_dir()
            ]
        return {
            "asset_id": self.asset_id,
            "path": self.root.relative_to(self.tenant_root).as_posix(),
            "lineage": (
                _local_authority_json(self, self.lineage_path)
                if self.lineage_path.is_file()
                else None
            ),
            "directories": {
                name: {
                    "path": path.relative_to(self.tenant_root).as_posix(),
                    "file_count": sum(1 for item in path.rglob("*") if item.is_file()),
                }
                for name, path in directories
            },
            "config_revisions": self.config_revision_summary(),
        }


def _legacy_artifact_path(stage: str, relative_name: str) -> Path:
    """Map a canonical stage artifact back to its pre-stage-layout location."""
    name = Path(relative_name).name
    if stage == "raw_inputs":
        return Path("raw_inputs") / name
    if stage == "prepared_inputs":
        return Path("prepared_inputs") / name
    if stage == "rubric_extraction":
        parent = (
            "decision_assets"
            if name
            in {
                "feedback_evidence.jsonl",
                "candidate_guidelines.jsonl",
                "evaluation_guidelines.jsonl",
                "feedback_rubrics.jsonl",
            }
            else "prepared_inputs"
        )
        return Path(parent) / name
    if stage == "intent_clustering":
        return Path("decision_assets") / name
    if stage == "coverage_decisions":
        parent = "review_queues" if name == "labeling_queue.jsonl" else "decision_assets"
        return Path(parent) / name
    if stage == "label_inference":
        parent = "prepared_inputs" if name == "inferred_cases.jsonl" else "decision_assets"
        return Path(parent) / name
    if stage == "synthetic_coverage":
        parent = "prepared_inputs" if name == "synthetic_cases.jsonl" else "decision_assets"
        return Path(parent) / name
    if stage == "dataset_splits":
        return Path("dataset_splits") / name
    raise ValueError(f"Unknown evaluation asset stage: {stage}")


def list_asset_layouts(
    tenants_root: Path,
    tenant_id: str,
    *,
    repository_base: Path | None = None,
) -> Iterable[EvaluationAssetLayout]:
    """List safe asset workspaces newest-first by directory modification time."""
    if not SAFE_NAME.fullmatch(tenant_id):
        return []
    probe = EvaluationAssetLayout(
        tenants_root,
        tenant_id,
        "layout_probe",
        repository_base=(
            repository_base if repository_base is not None else Path.cwd()
        ),
    )
    assets_root = probe.assets_root
    if not assets_root.is_dir():
        return []
    layouts = [
        EvaluationAssetLayout(
            probe.tenants_root,
            tenant_id,
            child.name,
            repository_base=probe.repository_base,
        )
        for child in assets_root.iterdir()
        if child.is_dir() and SAFE_NAME.fullmatch(child.name)
    ]
    return sorted(layouts, key=lambda item: item.root.stat().st_mtime, reverse=True)


def _file_descriptor(
    layout: EvaluationAssetLayout,
    path: Path,
) -> dict[str, Any]:
    """Describe one optional regular release pointer for the recovery WAL."""
    prospective = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="write",
    )
    if not prospective.exists:
        return {"present": False, "bytes": 0, "sha256": None}
    data = _local_authority_bytes(layout, path)
    return {
        "present": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _copy_jsonl(
    source: Path,
    destination: Path,
    *,
    trusted_root: Path | None = None,
) -> None:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".jsonl":
        raise ValueError(f"Evaluation asset inputs must be JSONL: {source}")
    if trusted_root is None:
        atomic_copy_file(source, destination)
        return
    current = resolve_local_authority_file(
        destination,
        trusted_root,
        access="read_optional",
    )
    write_local_authority_text(
        destination,
        trusted_root,
        source.read_text(encoding="utf-8"),
        expected_current=current.data if current.exists else None,
        check_expected_current=True,
    )


def _copy_local_authority(
    source_layout: EvaluationAssetLayout,
    source: Path,
    destination_layout: EvaluationAssetLayout,
    destination: Path,
) -> None:
    """Copy exact local authority bytes without reopening the source path."""
    current = resolve_local_authority_file(
        destination,
        destination_layout.tenants_root,
        access="read_optional",
    )
    write_local_authority_text(
        destination,
        destination_layout.tenants_root,
        _local_authority_bytes(source_layout, source).decode("utf-8"),
        expected_current=current.data if current.exists else None,
        check_expected_current=True,
    )


def _read_local_jsonl_rows(
    layout: EvaluationAssetLayout,
    path: Path,
) -> list[Dict[str, Any]]:
    """Read JSONL rows from one no-follow local authority handle."""
    return _jsonl_rows_from_bytes(path, _local_authority_bytes(layout, path))


def _jsonl_rows_from_bytes(path: Path, payload: bytes) -> list[Dict[str, Any]]:
    """Parse JSONL rows from one already captured authority payload."""
    rows: list[Dict[str, Any]] = []
    for line_number, line in enumerate(
        payload.decode("utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object at {path}:{line_number}")
        rows.append(row)
    return rows


def _read_jsonl_rows(path: Optional[Path]) -> list[Dict[str, Any]]:
    rows, _ = _read_jsonl_rows_with_line_numbers(path)
    return rows


def _read_jsonl_rows_with_line_numbers(
    path: Optional[Path],
) -> tuple[list[Dict[str, Any]], list[int]]:
    if path is None:
        return [], []
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    if resolved.suffix.lower() != ".jsonl":
        raise ValueError(f"Evaluation asset inputs must be JSONL: {resolved}")
    rows: list[Dict[str, Any]] = []
    row_numbers: list[int] = []
    for line_number, line in enumerate(
        resolved.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{resolved}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object at {resolved}:{line_number}")
        rows.append(row)
        row_numbers.append(line_number)
    return rows, row_numbers


def _validate_source_rows(path: Path, *, labeled: bool) -> list[Dict[str, Any]]:
    rows, row_numbers = _read_jsonl_rows_with_line_numbers(path)
    if not rows:
        kind = "labeled feedback" if labeled else "unlabeled"
        raise ValueError(f"{path}: {kind} input is empty")
    validate_input_records(
        rows,
        labeled=labeled,
        path=path,
        row_numbers=row_numbers,
    )
    return rows


def _is_beneath(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _validate_asset_write_targets(
    root: Path,
    targets: Sequence[Path],
    *,
    target_kind: str = "file",
) -> None:
    """Reject any prospective asset write whose path traverses a symlink."""
    if target_kind not in {"file", "directory"}:
        raise ValueError("evaluation asset write target kind is invalid")
    lexical_root = root.absolute()
    if lexical_root.is_symlink():
        raise ValueError("evaluation asset root cannot be a symlink")
    resolved_root = lexical_root.resolve(strict=True)
    for supplied in targets:
        target = supplied.absolute()
        if not _is_beneath(target, lexical_root):
            raise ValueError("evaluation asset write target escapes its root")
        relative = target.relative_to(lexical_root)
        current = lexical_root
        for component in relative.parts:
            current = current / component
            if current.is_symlink():
                raise ValueError("evaluation asset write target traverses a symlink")
            if current.exists() and current != target and not current.is_dir():
                raise ValueError("evaluation asset write target parent is not a directory")
        if target.exists() and (
            (target_kind == "file" and not target.is_file())
            or (target_kind == "directory" and not target.is_dir())
        ):
            raise ValueError("evaluation asset write target has the wrong file type")
        resolved_target = target.resolve(strict=False)
        if not _is_beneath(resolved_target, resolved_root):
            raise ValueError("evaluation asset write target escapes its root")


def _merge_jsonl_rows(
    parent_rows: Sequence[Mapping[str, Any]],
    added_rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> list[Dict[str, Any]]:
    merged: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in [*parent_rows, *added_rows]:
        record_id = str(row.get("record_id") or "").strip()
        if not record_id:
            raise ValueError(f"{source} record is missing record_id")
        if record_id in seen:
            raise ValueError(f"duplicate {source} record_id: {record_id}")
        seen.add(record_id)
        merged.append(dict(row))
    return merged
