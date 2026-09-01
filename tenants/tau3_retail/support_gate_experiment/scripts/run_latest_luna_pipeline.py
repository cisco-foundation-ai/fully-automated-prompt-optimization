# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Run the latest retrieval-plus-Luna applicability experiment.

This is a non-mutating experiment runner: it reads a completed FAFO asset
through Stage 5 and writes a sidecar result directory.  Guideline extraction
therefore remains pinned to the asset's original model, while only episode
applicability is evaluated by Luna.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from functools import partial
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
)
from src.hephaestus.evaluation_assets.pipeline import (
    EPISODE_GUIDELINE_APPLICABILITY_PROMPT,
    INFERRED_FROM_TRUSTED_FEEDBACK,
    EvaluationAssetPipeline,
    _applicability_batches,
    _applicability_provider_payload,
    _build_applicability_groups,
    _episode_cluster_support,
    _inferred_episode_cases,
    _intent_cluster,
    _intent_match,
    _merge_applicability_decision,
    _normalize_applicability_response,
    _record_applicability_row,
    _rubric_from_guidelines,
    has_scoreable_rubric,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ASSET_ROOT = (
    REPOSITORY_ROOT
    / "tenants"
    / "tau3_retail"
    / "evaluation_assets"
    / "baseline-gpt55-episode-v1"
)
DEFAULT_OUTPUT_ROOT = (
    REPOSITORY_ROOT
    / "tenants"
    / "tau3_retail"
    / "support_gate_experiment"
    / "latest_retrieval_luna_v1"
)
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "low"


class LunaSelectorProvider(OpenAIRubricProvider):
    """OpenAI JSON provider with an explicit, auditable reasoning effort."""

    def __init__(self, *, reasoning_effort: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.reasoning_effort = reasoning_effort

    def _completion_kwargs(
        self,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        kwargs = super()._completion_kwargs(messages)
        kwargs["reasoning_effort"] = self.reasoning_effort
        return kwargs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply Stage 5 retrieval candidates with direct per-episode Luna "
            "review and derive cluster support afterward."
        )
    )
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_REASONING_EFFORT,
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Validate inputs and write the run plan without making model calls.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object at {path}:{line_number}")
            rows.append(value)
    return rows


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def by_id(
    rows: Sequence[Mapping[str, Any]],
    key: str,
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = str(row[key])
        if identity in output:
            raise ValueError(f"Duplicate {key}: {identity}")
        output[identity] = dict(row)
    return output


def request_id(
    *,
    model: str,
    reasoning_effort: str,
    payload: Mapping[str, Any],
) -> str:
    body = {
        "model": model,
        "reasoning_effort": reasoning_effort,
        "system_prompt": EPISODE_GUIDELINE_APPLICABILITY_PROMPT,
        "payload": dict(payload),
    }
    return hashlib.sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def prepare(asset_root: Path) -> dict[str, Any]:
    config = EvaluationAssetConfig.from_dict(load_json(asset_root / "config.json"))
    intent_rows = load_jsonl(
        asset_root / "stages/02_prepared_inputs/intent_records.jsonl"
    )
    normalized = load_jsonl(
        asset_root / "stages/02_prepared_inputs/normalized_feedback.jsonl"
    )
    raw_rows = load_jsonl(asset_root / "stages/01_raw_inputs/unlabeled.jsonl")
    guidelines = load_jsonl(
        asset_root
        / "stages/03_evaluation_guidelines/evaluation_guidelines.jsonl"
    )
    clusters = [
        _intent_cluster(row)
        for row in load_jsonl(
            asset_root / "stages/04_intent_clustering/intent_inventory.jsonl"
        )
    ]
    matches = [
        _intent_match(row)
        for row in load_jsonl(
            asset_root / "stages/05_coverage_decisions/intent_matches.jsonl"
        )
    ]
    candidate_rows = load_jsonl(
        asset_root
        / "stages/05_coverage_decisions/episode_guideline_candidates.jsonl"
    )
    raw_by_id = by_id(raw_rows, "record_id")
    row_by_id = by_id(intent_rows, "record_id")
    guideline_by_id = by_id(guidelines, "guideline_id")
    candidate_by_record = by_id(candidate_rows, "record_id")
    trusted_record_ids = {str(row["record_id"]) for row in normalized}
    eligible_record_ids = {
        record_id
        for cluster in clusters
        for record_id in cluster.record_ids
        if record_id not in trusted_record_ids
    }
    if eligible_record_ids - set(candidate_by_record):
        raise ValueError("Stage 5 candidate rows do not cover every unlabeled episode")
    groups, group_by_record, deterministic_rows = _build_applicability_groups(
        eligible_record_ids=eligible_record_ids,
        candidate_by_record=candidate_by_record,
        raw_by_id=raw_by_id,
        guideline_by_id=guideline_by_id,
        unknown_policy="llm_fallback",
        use_applicability_contracts=False,
        use_deterministic_candidate_filters=False,
    )
    return {
        "config": config,
        "intent_rows": intent_rows,
        "raw_rows": raw_rows,
        "raw_by_id": raw_by_id,
        "row_by_id": row_by_id,
        "guideline_by_id": guideline_by_id,
        "clusters": clusters,
        "matches": matches,
        "candidate_by_record": candidate_by_record,
        "eligible_record_ids": eligible_record_ids,
        "groups": groups,
        "group_by_record": group_by_record,
        "deterministic_rows": deterministic_rows,
    }


def main() -> None:
    args = parse_args()
    prepared = prepare(args.asset_root)
    groups = prepared["groups"]
    deterministic_rows = prepared["deterministic_rows"]
    batches = list(_applicability_batches(groups))
    candidate_counts = [
        len(row["candidates"])
        for record_id, row in prepared["candidate_by_record"].items()
        if record_id in prepared["eligible_record_ids"]
    ]
    plan = {
        "schema_version": "fapo-latest-retrieval-luna-plan-v1",
        "source_asset": str(args.asset_root.resolve()),
        "guideline_extraction_model": prepared["config"].rubric_model,
        "applicability_model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "retrieval": "route-constrained union of cluster and episode similarity",
        "applicability": "direct Luna review; zero, one, or many guidelines",
        "cluster_support": "derived after episode applicability",
        "episode_count": len(prepared["eligible_record_ids"]),
        "guideline_count": len(prepared["guideline_by_id"]),
        "decision_group_count": len(groups),
        "deterministic_empty_candidate_decisions": len(deterministic_rows),
        "model_call_batch_count": len(batches),
        "candidate_count": {
            "minimum": min(candidate_counts, default=0),
            "maximum": max(candidate_counts, default=0),
            "average": (
                round(sum(candidate_counts) / len(candidate_counts), 4)
                if candidate_counts
                else 0.0
            ),
        },
    }
    write_json(args.output_root / "run_plan.json", plan)
    if args.prepare_only:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return

    provider = LunaSelectorProvider(
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=16384,
    )
    pipeline = EvaluationAssetPipeline.__new__(EvaluationAssetPipeline)
    pipeline.rubric_provider = provider
    pipeline._provider_identities = {
        "rubric": {"provider": "openai", "model": args.model}
    }
    pipeline._provider_settings = {
        "rubric": {
            "settings": {
                "response_format": "json_object",
                "max_output_tokens": 16384,
                "reasoning_effort": args.reasoning_effort,
                "temperature": provider.temperature,
            }
        }
    }
    pipeline._stage_call_rows = []
    decisions_by_id = {
        str(row["decision_id"]): dict(row) for row in deterministic_rows
    }
    cache_root = args.output_root / "batch_cache"
    started = time.monotonic()
    for index, batch in enumerate(batches, start=1):
        payload = _applicability_provider_payload(
            batch,
            prepared["guideline_by_id"],
        )
        cache_key = request_id(
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            payload=payload,
        )
        cache_path = cache_root / f"{cache_key}.json"
        if cache_path.is_file():
            cached = load_json(cache_path)
            generated = cached["normalized_response"]
            pipeline._stage_call_rows.extend(cached["provider_calls"])
            print(f"reused Luna batch {index}/{len(batches)}", flush=True)
        else:
            call_start = len(pipeline._stage_call_rows)
            generated = pipeline._call_rubric_provider(
                PipelineStage.LABEL_INFERENCE,
                EPISODE_GUIDELINE_APPLICABILITY_PROMPT,
                payload,
                partial(
                    _normalize_applicability_response,
                    decision_groups=batch,
                ),
            )
            write_json(
                cache_path,
                {
                    "schema_version": "fapo-luna-applicability-cache-v1",
                    "request_sha256": cache_key,
                    "normalized_response": generated,
                    "provider_calls": pipeline._stage_call_rows[call_start:],
                },
            )
            print(f"completed Luna batch {index}/{len(batches)}", flush=True)
        group_by_decision_id = {
            str(group["decision_id"]): group for group in batch
        }
        for decision in generated:
            decision_id = str(decision["decision_id"])
            decisions_by_id[decision_id] = _merge_applicability_decision(
                group_by_decision_id[decision_id],
                decision,
            )

    selected_ids_by_record: dict[str, tuple[str, ...]] = {}
    decision_by_record: dict[str, dict[str, Any]] = {}
    applicability_rows: list[dict[str, Any]] = []
    episode_rubrics: list[dict[str, Any]] = []
    held_outputs: list[dict[str, Any]] = []
    for record_id in sorted(prepared["eligible_record_ids"]):
        group = prepared["group_by_record"][record_id]
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
        rubric = _rubric_from_guidelines(
            record_id,
            [prepared["guideline_by_id"][item] for item in selected_ids],
            prepared["config"].rubric_provider,
            prepared["config"].rubric_model,
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
                }
            )

    rubric_by_record = {
        str(row["record_id"]): row for row in episode_rubrics
    }
    labels, inferred_cases = _inferred_episode_cases(
        clusters=prepared["clusters"],
        matches=prepared["matches"],
        intent_rows=prepared["intent_rows"],
        raw_rows=prepared["raw_rows"],
        rubric_by_record=rubric_by_record,
        decision_by_record=decision_by_record,
        config=prepared["config"],
    )
    cluster_support, missing = _episode_cluster_support(
        clusters=prepared["clusters"],
        matches=prepared["matches"],
        row_by_id=prepared["row_by_id"],
        eligible_record_ids=prepared["eligible_record_ids"],
        selected_ids_by_record=selected_ids_by_record,
        rubric_by_record=rubric_by_record,
    )
    for name, rows in (
        ("episode_guideline_applicability.jsonl", applicability_rows),
        ("inferred_unlabeled_episode_rubrics.jsonl", episode_rubrics),
        ("inferred_unlabeled_labels.jsonl", labels),
        ("inferred_cases.jsonl", inferred_cases),
        ("held_inference_outputs.jsonl", held_outputs),
        ("cluster_feedback_support.jsonl", cluster_support),
        ("missing_labeled_feedback_clusters.jsonl", missing),
        ("provider_calls.jsonl", pipeline._stage_call_rows),
    ):
        write_jsonl(args.output_root / name, rows)
    status_counts: dict[str, int] = {}
    for row in cluster_support:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    summary = {
        **plan,
        "schema_version": "fapo-latest-retrieval-luna-result-v1",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "provider_call_count": len(pipeline._stage_call_rows),
        "inferred_case_count": len(inferred_cases),
        "held_episode_count": len(held_outputs),
        "review_cluster_count": len(missing),
        "cluster_status_counts": status_counts,
    }
    write_json(args.output_root / "run_result.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
