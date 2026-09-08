#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Select, render, and join manual trusted feedback for Tau FAFO episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from src.hephaestus.evaluation_assets.input_contract import validate_input_records


TENANT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALL = TENANT_ROOT / "source_artifacts/all_unlabeled.jsonl"
DEFAULT_SELECTION = TENANT_ROOT / "source_artifacts/feedback-selection.jsonl"
DEFAULT_MANIFEST = TENANT_ROOT / "source_artifacts/feedback-selection-manifest.json"
DEFAULT_REVIEWS = TENANT_ROOT / "source_artifacts/feedback-review"
DEFAULT_LABELED = TENANT_ROOT / "source_artifacts/labeled_feedback.jsonl"
DEFAULT_UNLABELED = TENANT_ROOT / "source_artifacts/unlabeled_traffic.jsonl"
PROTECTED_KEYS = frozenset(
    {
        "action_checks",
        "communicate_checks",
        "db_check",
        "env_assertions",
        "evaluation_criteria",
        "expected",
        "nl_assertions",
        "reward",
        "reward_breakdown",
        "reward_info",
    }
)
POLARITY_PREFIX = "**Polarity** (`positive`, `negative`, or `mixed`):"
RATIONALE_PREFIX = "**Rationale**:"
CORRECTION_PREFIX = "**Correction** (optional):"
TRUST_PREFIX = "**Reviewed as trusted** (`yes` or `no`):"
ALLOWED_POLARITIES = frozenset({"positive", "negative", "mixed"})
ACTION_CATEGORIES = {
    "exchange_delivered_order_items": "exchange",
    "return_delivered_order_items": "return",
    "cancel_pending_order": "cancel",
    "modify_pending_order_items": "modify_items",
    "modify_pending_order_address": "modify_order_address",
    "modify_user_address": "modify_user_address",
    "modify_pending_order_payment": "modify_payment",
    "transfer_to_human_agents": "transfer",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read nonblank JSON objects from a JSONL file."""
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"{path}:{line_number}: blank row")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write deterministic JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    temporary.replace(path)


def sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(*parts: object) -> str:
    """Return a deterministic selection key."""
    return hashlib.sha256("\x1f".join(map(str, parts)).encode()).hexdigest()


def nested_keys(value: Any) -> set[str]:
    """Return every nested mapping key."""
    if isinstance(value, Mapping):
        return {
            *(str(key) for key in value),
            *(key for item in value.values() for key in nested_keys(item)),
        }
    if isinstance(value, list):
        return {key for item in value for key in nested_keys(item)}
    return set()


def validate_unlabeled(rows: list[dict[str, Any]], path: Path) -> None:
    """Reject labels and protected Tau oracle fields before sampling."""
    validate_input_records(rows, labeled=False, path=path)
    leaked = set().union(*(nested_keys(row) for row in rows)) & PROTECTED_KEYS
    if leaked:
        raise ValueError("Protected Tau fields reached feedback sampling: " + ", ".join(sorted(leaked)))


def record_metrics(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return observable, outcome-blind features for sampling."""
    events = (record.get("episode") or {}).get("events") or []
    tool_calls = record.get("tool_calls") or []
    categories = sorted(
        {
            ACTION_CATEGORIES[str(call.get("name"))]
            for call in tool_calls
            if str(call.get("name")) in ACTION_CATEGORIES
        }
    )
    return {
        "record": record,
        "record_id": str(record["record_id"]),
        "task_id": str((record.get("runtime") or {}).get("task_id")),
        "trial": int((record.get("runtime") or {}).get("trial", 0)),
        "group_id": str(record["group_id"]),
        "event_count": len(events),
        "tool_call_count": len(tool_calls),
        "tool_error_count": sum(call.get("error") not in (None, "") for call in tool_calls),
        "categories": categories,
    }


def select_records(
    rows: list[dict[str, Any]],
    *,
    count: int,
    seed: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select a group-diverse, outcome-blind manual-feedback sample."""
    if count < 1 or count >= len(rows):
        raise ValueError("count must leave at least one unlabeled record")
    metrics = [record_metrics(row) for row in rows]
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_groups: set[str] = set()
    selected_tasks: set[str] = set()
    trial_counts: Counter[int] = Counter()

    def candidate_key(metric: Mapping[str, Any], slot: str) -> tuple[Any, ...]:
        return (
            trial_counts[int(metric["trial"])],
            abs(int(metric["event_count"]) - 20),
            stable_hash(seed, slot, metric["record_id"]),
        )

    def choose(candidates: list[dict[str, Any]], slot: str) -> bool:
        eligible = [
            metric
            for metric in candidates
            if metric["record_id"] not in selected_ids
            and metric["group_id"] not in selected_groups
            and metric["task_id"] not in selected_tasks
        ]
        if not eligible:
            return False
        chosen = min(eligible, key=lambda metric: candidate_key(metric, slot))
        chosen = dict(chosen)
        chosen["selection_stratum"] = slot
        selected.append(chosen)
        selected_ids.add(chosen["record_id"])
        selected_groups.add(chosen["group_id"])
        selected_tasks.add(chosen["task_id"])
        trial_counts[int(chosen["trial"])] += 1
        return True

    for category in sorted(set(ACTION_CATEGORIES.values())):
        if len(selected) >= count:
            break
        choose(
            [metric for metric in metrics if category in metric["categories"]],
            f"operation:{category}",
        )
    if len(selected) < count:
        choose(
            [metric for metric in metrics if not metric["categories"]],
            "operation:no_consequential_action",
        )
    if len(selected) < count:
        choose(
            [metric for metric in metrics if metric["tool_error_count"] > 0],
            "shape:tool_error",
        )
    if len(selected) < count:
        choose(
            [metric for metric in metrics if len(metric["categories"]) >= 2],
            "shape:multi_action",
        )

    group_order = sorted(
        {metric["group_id"] for metric in metrics} - selected_groups,
        key=lambda group_id: stable_hash(seed, "group", group_id),
    )
    for group_id in group_order:
        if len(selected) >= count:
            break
        choose(
            [metric for metric in metrics if metric["group_id"] == group_id],
            "group_coverage",
        )
    if len(selected) < count:
        remaining = [metric for metric in metrics if metric["record_id"] not in selected_ids]
        remaining.sort(key=lambda metric: candidate_key(metric, "fill"))
        for metric in remaining:
            if len(selected) >= count:
                break
            chosen = dict(metric)
            chosen["selection_stratum"] = "fill"
            selected.append(chosen)
            selected_ids.add(chosen["record_id"])
            trial_counts[int(chosen["trial"])] += 1
    if len(selected) != count:
        raise ValueError(f"Selected {len(selected)} records, expected {count}")
    selected.sort(key=lambda metric: stable_hash(seed, "annotation", metric["record_id"]))
    selected_rows = [dict(metric["record"]) for metric in selected]
    return selected_rows, selected


def select_command(args: argparse.Namespace) -> None:
    """Write the selected records and a content-bound manifest."""
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    manifest_path = args.manifest.resolve()
    rows = load_jsonl(input_path)
    validate_unlabeled(rows, input_path)
    selected_rows, metrics = select_records(rows, count=args.count, seed=args.seed)
    write_jsonl(output_path, selected_rows)
    manifest = {
        "schema_version": "tau3-fafo-feedback-selection-v2",
        "source_sha256": sha256(input_path),
        "selection_sha256": sha256(output_path),
        "seed": args.seed,
        "source_count": len(rows),
        "selected_count": len(selected_rows),
        "outcome_blind": True,
        "selected": [
            {
                "annotation_order": index,
                "record_id": metric["record_id"],
                "group_id": metric["group_id"],
                "task_id": metric["task_id"],
                "trial": metric["trial"],
                "selection_stratum": metric["selection_stratum"],
            }
            for index, metric in enumerate(metrics, start=1)
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Selected {len(selected_rows)} records for manual feedback")


def _review_text(record: Mapping[str, Any], order: int) -> str:
    """Render user/assistant dialogue only, followed by empty feedback fields."""
    lines = [f"# Episode {order:02d}: {record['record_id']}", "", "## Conversation", ""]
    events = (record.get("episode") or {}).get("events") or []
    for event in events:
        if event.get("type") != "message" or event.get("role") not in {"user", "assistant"}:
            continue
        role = "User" if event["role"] == "user" else "Assistant"
        lines.extend([f"### {role}", "", str(event.get("content", "")).strip(), ""])
    lines.extend(
        [
            "## Trusted user feedback",
            "",
            f"{POLARITY_PREFIX} ",
            "",
            f"{RATIONALE_PREFIX} ",
            "",
            f"{CORRECTION_PREFIX} ",
            "",
            f"{TRUST_PREFIX} no",
            "",
        ]
    )
    return "\n".join(lines)


def render_command(args: argparse.Namespace) -> None:
    """Create one human-editable conversation file per selected record."""
    rows = load_jsonl(args.selection.resolve())
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    index = [
        "# Tau feedback review queue",
        "",
        "Edit each episode file, then set `Reviewed as trusted` to `yes`.",
        "",
    ]
    for order, row in enumerate(rows, start=1):
        filename = f"{order:02d}_{row['record_id']}.md"
        path = output_dir / filename
        if not path.exists():
            path.write_text(_review_text(row, order), encoding="utf-8")
        index.append(f"- [{row['record_id']}]({filename})")
    (output_dir / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Rendered {len(rows)} conversations in {output_dir}")


def _field(text: str, prefix: str, path: Path) -> str:
    matches = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one {prefix}")
    return matches[0]


def _read_feedback(review_dir: Path, selected_ids: list[str]) -> dict[str, dict[str, str]]:
    feedback: dict[str, dict[str, str]] = {}
    for order, record_id in enumerate(selected_ids, start=1):
        matches = list(review_dir.glob(f"{order:02d}_{record_id}.md"))
        if len(matches) != 1:
            raise ValueError(f"Expected one review file for {record_id}")
        path = matches[0]
        text = path.read_text(encoding="utf-8")
        polarity = _field(text, POLARITY_PREFIX, path)
        rationale = _field(text, RATIONALE_PREFIX, path)
        correction = _field(text, CORRECTION_PREFIX, path)
        trusted = _field(text, TRUST_PREFIX, path).lower()
        if polarity not in ALLOWED_POLARITIES or not rationale or trusted != "yes":
            raise ValueError(f"{path}: feedback is incomplete or not marked trusted")
        value = {"polarity": polarity, "rationale": rationale, "source": "human_review"}
        if correction:
            value["correction"] = correction
        feedback[record_id] = value
    return feedback


def join_command(args: argparse.Namespace) -> None:
    """Join reviewed feedback and emit disjoint labeled/unlabeled inputs."""
    all_path = args.input.resolve()
    selection_path = args.selection.resolve()
    rows = load_jsonl(all_path)
    selected = load_jsonl(selection_path)
    validate_unlabeled(rows, all_path)
    validate_unlabeled(selected, selection_path)
    by_id = {str(row["record_id"]): row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("Source record IDs must be unique")
    selected_ids = [str(row["record_id"]) for row in selected]
    if len(set(selected_ids)) != len(selected_ids) or not set(selected_ids) <= set(by_id):
        raise ValueError("Selection must be a unique subset of the source export")
    for row in selected:
        if row != by_id[str(row["record_id"])]:
            raise ValueError("Selected record differs from the source export")
    feedback = _read_feedback(args.review_dir.resolve(), selected_ids)
    labeled = []
    for record_id in selected_ids:
        row = dict(by_id[record_id])
        row["feedback"] = feedback[record_id]
        labeled.append(row)
    unlabeled = [dict(row) for row in rows if str(row["record_id"]) not in feedback]
    validate_input_records(labeled, labeled=True, path=args.labeled_output)
    validate_input_records(unlabeled, labeled=False, path=args.unlabeled_output)
    if {row["record_id"] for row in labeled} & {row["record_id"] for row in unlabeled}:
        raise ValueError("Labeled and unlabeled outputs overlap")
    write_jsonl(args.labeled_output.resolve(), labeled)
    write_jsonl(args.unlabeled_output.resolve(), unlabeled)
    print(f"Wrote {len(labeled)} trusted and {len(unlabeled)} unlabeled episodes")


def build_parser() -> argparse.ArgumentParser:
    """Build the three-command annotation CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    select = subparsers.add_parser("select", help="Select an outcome-blind sample")
    select.add_argument("--input", type=Path, default=DEFAULT_ALL)
    select.add_argument("--output", type=Path, default=DEFAULT_SELECTION)
    select.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    select.add_argument("--count", type=int, default=37)
    select.add_argument("--seed", default="tau3-fafo-feedback-v1")
    select.set_defaults(handler=select_command)

    render = subparsers.add_parser("render", help="Render conversations for review")
    render.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    render.add_argument("--output-dir", type=Path, default=DEFAULT_REVIEWS)
    render.set_defaults(handler=render_command)

    join = subparsers.add_parser("join", help="Join completed trusted feedback")
    join.add_argument("--input", type=Path, default=DEFAULT_ALL)
    join.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    join.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEWS)
    join.add_argument("--labeled-output", type=Path, default=DEFAULT_LABELED)
    join.add_argument("--unlabeled-output", type=Path, default=DEFAULT_UNLABELED)
    join.set_defaults(handler=join_command)
    return parser


def main() -> int:
    """Dispatch one annotation workflow command."""
    args = build_parser().parse_args()
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
