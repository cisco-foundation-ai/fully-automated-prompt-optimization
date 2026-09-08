#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Convert Tau result episodes into unlabeled FAFO V3 input records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from src.hephaestus.evaluation_assets.input_contract import validate_input_records


SCHEMA_VERSION = "fapo-evaluation-input-v1"
TENANT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT = TENANT_ROOT / "recipe/retail-split.json"
DEFAULT_OUTPUT = TENANT_ROOT / "source_artifacts/all_unlabeled.jsonl"
FORBIDDEN_KEYS = frozenset(
    {
        "action_checks",
        "communicate_checks",
        "db_check",
        "env_assertions",
        "evaluation_criteria",
        "expected",
        "feedback",
        "nl_assertions",
        "reward",
        "reward_breakdown",
        "reward_info",
    }
)


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object."""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nested_keys(value: Any) -> set[str]:
    """Return every object key in a JSON-compatible value."""
    if isinstance(value, Mapping):
        return {
            *(str(key) for key in value),
            *(key for item in value.values() for key in nested_keys(item)),
        }
    if isinstance(value, list):
        return {key for item in value for key in nested_keys(item)}
    return set()


def message_content(message: Mapping[str, Any]) -> str:
    """Return required nonempty message content."""
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Tau conversation message has empty content")
    return content


def result_payload(message: Mapping[str, Any]) -> dict[str, Any]:
    """Map a Tau tool result without interpreting its content."""
    content = message_content(message)
    if message.get("error") is True:
        return {"error": content}
    return {"result": content}


def build_episode(
    simulation: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], Counter[str]]:
    """Build ordered FAFO episode events and the flat tool-call summary."""
    raw_messages = simulation.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError(f"Simulation {simulation.get('id')} has no messages")
    messages: list[Mapping[str, Any]] = []
    for message in raw_messages:
        if not isinstance(message, Mapping):
            raise TypeError("Tau conversation contains a non-object message")
        messages.append(message)

    result_by_id: dict[str, Mapping[str, Any]] = {}
    for message in messages:
        if message.get("role") != "tool":
            continue
        call_id = str(message.get("id") or "")
        if not call_id or call_id in result_by_id:
            raise ValueError("Tau tool results require unique nonempty call IDs")
        result_by_id[call_id] = message

    events: list[dict[str, Any]] = []
    flat_calls: list[dict[str, Any]] = []
    observed_calls: set[str] = set()
    counts: Counter[str] = Counter()

    def append_event(event: dict[str, Any]) -> None:
        event["sequence"] = len(events)
        events.append(event)

    for message in messages:
        role = message.get("role")
        source_turn = message.get("turn_idx")
        if role in {"assistant", "user"}:
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                append_event(
                    {
                        "type": "message",
                        "role": role,
                        "content": content,
                        "source_turn_idx": source_turn,
                    }
                )
                counts[f"{role}_messages"] += 1
            calls = message.get("tool_calls") or []
            if not isinstance(calls, list):
                raise TypeError("Tau tool_calls must be a list")
            for call in calls:
                if not isinstance(call, Mapping):
                    raise TypeError("Tau tool call must be an object")
                call_id = str(call.get("id") or "")
                name = str(call.get("name") or "")
                arguments = call.get("arguments")
                if not call_id or not name or not isinstance(arguments, Mapping):
                    raise ValueError("Tau tool call has invalid ID, name, or arguments")
                if call_id in observed_calls:
                    raise ValueError(f"Tau tool call ID is reused: {call_id}")
                observed_calls.add(call_id)
                append_event(
                    {
                        "type": "tool_call",
                        "call_id": call_id,
                        "name": name,
                        "arguments": dict(arguments),
                        "source_turn_idx": source_turn,
                    }
                )
                flattened: dict[str, Any] = {
                    "call_id": call_id,
                    "name": name,
                    "arguments": dict(arguments),
                }
                if call_id in result_by_id:
                    flattened.update(result_payload(result_by_id[call_id]))
                    if result_by_id[call_id].get("error") is not True:
                        flattened["error"] = None
                flat_calls.append(flattened)
                counts["tool_calls"] += 1
            continue
        if role == "tool":
            call_id = str(message.get("id") or "")
            if call_id not in observed_calls:
                raise ValueError(f"Tool result does not follow call: {call_id}")
            append_event(
                {
                    "type": "tool_result",
                    "call_id": call_id,
                    **result_payload(message),
                    "source_turn_idx": source_turn,
                }
            )
            counts["tool_results"] += 1
            counts["tool_errors"] += int(message.get("error") is True)
            continue
        raise ValueError(f"Unsupported Tau message role: {role!r}")

    if observed_calls != set(result_by_id):
        raise ValueError("Every Tau tool call must have exactly one linked result")
    episode_id = str(simulation.get("id") or "")
    termination = str(simulation.get("termination_reason") or "")
    if not episode_id or not termination:
        raise ValueError("Tau simulation is missing episode ID or termination reason")
    return (
        {
            "episode_id": episode_id,
            "termination_reason": termination,
            "events": events,
        },
        flat_calls,
        counts,
    )


def conversation_summary(
    simulation: Mapping[str, Any],
) -> tuple[str, list[dict[str, str]], str]:
    """Extract the first request, prior dialogue, and final assistant text."""
    messages = simulation["messages"]
    first_user = next(
        (index for index, message in enumerate(messages) if message.get("role") == "user"),
        None,
    )
    if first_user is None:
        raise ValueError("Tau simulation has no user message")
    user_input = message_content(messages[first_user])
    context = [
        {"role": str(message["role"]), "content": message_content(message)}
        for message in messages[:first_user]
        if message.get("role") in {"assistant", "user"}
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]
    assistant_output = next(
        (
            message_content(message)
            for message in reversed(messages)
            if message.get("role") == "assistant"
            and isinstance(message.get("content"), str)
            and message["content"].strip()
        ),
        None,
    )
    if assistant_output is None:
        raise ValueError("Tau simulation has no textual assistant response")
    return user_input, context, assistant_output


def assignments(split: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Index the frozen partition and scenario-family assignment by task ID."""
    output: dict[str, dict[str, str]] = {}
    for row in split.get("task_assignments") or []:
        task_id = str(row["task_id"])
        if task_id in output:
            raise ValueError(f"Duplicate split assignment for task {task_id}")
        output[task_id] = {
            "partition": str(row["partition"]),
            "scenario_family_id": str(row["scenario_family_id"]),
        }
    return output


def build_record(
    simulation: Mapping[str, Any],
    *,
    assignment: Mapping[str, str],
    split: Mapping[str, Any],
    source_run: str,
) -> tuple[dict[str, Any], Counter[str]]:
    """Convert one entire Tau episode into one FAFO record."""
    task_id = str(simulation.get("task_id"))
    trial = simulation.get("trial")
    seed = simulation.get("seed")
    if not isinstance(trial, int) or isinstance(trial, bool):
        raise TypeError("Tau trial must be an integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("Tau seed must be an integer")
    episode, tool_calls, counts = build_episode(simulation)
    user_input, context, assistant_output = conversation_summary(simulation)
    record_id = f"tau3-retail-task-{task_id}-trial-{trial}"
    return (
        {
            "schema_version": SCHEMA_VERSION,
            "record_id": record_id,
            "request_id": record_id,
            "group_id": assignment["scenario_family_id"],
            "task_type": "retail_customer_support",
            "route": "tau3_retail",
            "user_input": user_input,
            "conversation_context": context,
            "assistant_output": assistant_output,
            "tool_calls": tool_calls,
            "episode": episode,
            "runtime": {
                "benchmark": "tau3-bench",
                "benchmark_release": split["release"],
                "benchmark_commit": split["release_commit"],
                "domain": "retail",
                "task_set": "retail",
                "task_split": "base",
                "task_id": task_id,
                "trial": trial,
                "seed": seed,
                "mode": simulation.get("mode"),
                "agent": "llm_agent",
                "agent_model": "gpt-4.1-2025-04-14",
                "agent_temperature": 0.0,
                "user_simulator": "user_simulator",
                "user_simulator_model": "gpt-4.1-2025-04-14",
                "user_simulator_temperature": 0.0,
            },
            "metadata": {
                "source": "tau3_baseline_rollout",
                "source_run": source_run,
                "source_simulation_id": episode["episode_id"],
                "freeze_id": split["freeze_id"],
                "partition": assignment["partition"],
                "scenario_family_id": assignment["scenario_family_id"],
            },
        },
        counts,
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write compact, deterministic JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    temporary.replace(path)


def export_records(
    results: Mapping[str, Any],
    split: Mapping[str, Any],
    *,
    partition: str,
    source_run: str,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Convert and validate every episode in the selected partition."""
    split_assignments = assignments(split)
    simulations = results.get("simulations")
    if not isinstance(simulations, list):
        raise TypeError("Tau results must contain a simulations array")
    rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    source_identities: set[tuple[str, int, int]] = set()
    for simulation in simulations:
        if not isinstance(simulation, Mapping):
            raise TypeError("Tau simulations must be objects")
        task_id = str(simulation.get("task_id"))
        assignment = split_assignments.get(task_id)
        if assignment is None or assignment["partition"] != partition:
            raise ValueError(f"Task {task_id} is not assigned to {partition}")
        identity = (task_id, int(simulation["trial"]), int(simulation["seed"]))
        if identity in source_identities:
            raise ValueError(f"Duplicate Tau task/trial/seed: {identity}")
        source_identities.add(identity)
        row, counts = build_record(
            simulation,
            assignment=assignment,
            split=split,
            source_run=source_run,
        )
        rows.append(row)
        totals.update(counts)
    rows.sort(
        key=lambda row: (
            int(row["runtime"]["task_id"]),
            int(row["runtime"]["trial"]),
            int(row["runtime"]["seed"]),
        )
    )
    if len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("FAFO record IDs are not unique")
    leaked = set().union(*(nested_keys(row) for row in rows)) & FORBIDDEN_KEYS
    if leaked:
        raise ValueError("Protected Tau scoring fields leaked: " + ", ".join(sorted(leaked)))
    validate_input_records(rows, labeled=False, path=Path("tau-export.jsonl"))
    return rows, totals


def main() -> int:
    """Convert a Tau results file and emit an audit summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--partition", default="development")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    results_path = args.results.resolve()
    split_path = args.split.resolve()
    output_path = args.output.resolve()
    results = load_json(results_path)
    split = load_json(split_path)
    source_run = results_path.parent.name
    rows, totals = export_records(
        results,
        split,
        partition=args.partition,
        source_run=source_run,
    )
    write_jsonl(output_path, rows)
    validate_input_records(
        [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()],
        labeled=False,
        path=output_path,
    )
    summary_path = (args.summary or output_path.with_name("export-summary.json")).resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": "tau3-fafo-export-v2",
                "source_results_sha256": sha256(results_path),
                "split_sha256": sha256(split_path),
                "output_sha256": sha256(output_path),
                "records": len(rows),
                "tasks": len({row["runtime"]["task_id"] for row in rows}),
                "groups": len({row["group_id"] for row in rows}),
                "event_counts": dict(sorted(totals.items())),
                "protected_scoring_fields": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(rows)} unlabeled episodes to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
