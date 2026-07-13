#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Standalone evaluator for the software-name mini challenge."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEST_DATA = BASE_DIR / "data" / "mini_test.jsonl"
DEFAULT_FAPO_RESULTS = BASE_DIR / "data" / "fapo_v006_results.json"
DEFAULT_LEVEL = "difficult"
DEFAULT_API_URL = os.environ.get(
    "OPENAI_CHAT_COMPLETIONS_URL",
    "https://api.openai.com/v1/chat/completions",
)

LABELS = [
    "network_and_remote_access",
    "exposure_testing",
    "data_transfer_and_sync",
    "runtime_and_server_stack",
    "user_endpoint_clients",
    "sensitive_key_material",
    "security_posture_changes",
    "general_utility_other",
]

LEVEL_CONFIG = {
    "easy": {
        "name": "Easy",
        "labels": [
            "network_and_remote_access",
            "general_utility_other",
        ],
        "test_data": BASE_DIR / "data" / "mini_test_easy.jsonl",
        "fapo_results": BASE_DIR / "data" / "fapo_v006_results_easy.json",
    },
    "medium": {
        "name": "Medium",
        "labels": [
            "network_and_remote_access",
            "exposure_testing",
            "data_transfer_and_sync",
            "general_utility_other",
        ],
        "test_data": BASE_DIR / "data" / "mini_test_medium.jsonl",
        "fapo_results": BASE_DIR / "data" / "fapo_v006_results_medium.json",
    },
    "difficult": {
        "name": "Difficult",
        "labels": LABELS,
        "test_data": DEFAULT_TEST_DATA,
        "fapo_results": DEFAULT_FAPO_RESULTS,
    },
}


@dataclass(frozen=True)
class MiniCase:
    case_id: str
    software_name: str
    expected: str
    difficulty: str
    ambiguity_type: str


def get_level_config(level: str) -> dict[str, Any]:
    try:
        return LEVEL_CONFIG[level]
    except KeyError as exc:
        allowed = ", ".join(LEVEL_CONFIG)
        raise ValueError(f"Unknown level '{level}'. Choose one of: {allowed}.") from exc


def build_starter_prompt(labels: list[str]) -> str:
    label_block = "\n".join(labels)
    return (
        "You classify software names into domains of security concern.\n\n"
        "Choose exactly one label from this list:\n\n"
        f"{label_block}\n"
        "Use only the software name provided by the user. Do not infer from vendor, description, URL, "
        "operating system, or any external field.\n\n"
        "Return exactly one label and nothing else.\n"
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} is not valid JSON") from exc
    return rows


def load_test_cases(path: Path = DEFAULT_TEST_DATA) -> list[MiniCase]:
    cases: list[MiniCase] = []
    for row in load_jsonl(path):
        metadata = row.get("metadata", {})
        cases.append(
            MiniCase(
                case_id=row["case_id"],
                software_name=row["context"]["software_name"],
                expected=row["expected"]["category"],
                difficulty=metadata.get("difficulty", ""),
                ambiguity_type=metadata.get("ambiguity_type", ""),
            )
        )
    return cases


def load_fapo_results(path: Path = DEFAULT_FAPO_RESULTS) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    data["summary"] = summarize_pairs(
        [(case["expected"], case["prediction"]) for case in data.get("cases", [])]
    )
    return data


def normalize_label(value: str) -> str:
    stripped = strip_code_fences(value).strip()
    lowered = stripped.lower()
    searchable = re.sub(r"[\s-]+", "_", lowered)
    searchable = searchable.replace("`", "").replace('"', "").replace("'", "")

    for label in LABELS:
        if re.search(rf"(?<![a-z0-9_]){re.escape(label)}(?![a-z0-9_])", searchable):
            return label

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    candidate = lines[-1] if lines else stripped
    candidate = candidate.strip("`'\".,;:()[]{}")
    candidate = re.sub(r"[\s-]+", "_", candidate.lower())
    candidate = re.sub(r"[^a-z0-9_]", "", candidate)
    return candidate


def strip_code_fences(value: str) -> str:
    lines = value.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def summarize_pairs(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    total = len(pairs)
    correct = sum(1 for expected, predicted in pairs if expected == predicted)
    active_labels = sorted({label for pair in pairs for label in pair if label})
    per_label: dict[str, dict[str, float]] = {}

    for label in active_labels:
        true_positive = sum(1 for expected, predicted in pairs if expected == label and predicted == label)
        false_positive = sum(1 for expected, predicted in pairs if expected != label and predicted == label)
        false_negative = sum(1 for expected, predicted in pairs if expected == label and predicted != label)
        precision_denominator = true_positive + false_positive
        recall_denominator = true_positive + false_negative
        precision = true_positive / precision_denominator if precision_denominator else 0.0
        recall = true_positive / recall_denominator if recall_denominator else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "precision_percent": round(precision * 100, 2),
            "recall_percent": round(recall * 100, 2),
            "f1_percent": round(f1 * 100, 2),
        }

    macro_f1 = sum(label_score["f1_percent"] for label_score in per_label.values())
    macro_f1 = macro_f1 / len(per_label) if per_label else 0.0
    accuracy = correct / total if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy_percent": round(accuracy * 100, 2),
        "micro_f1_percent": round(accuracy * 100, 2),
        "macro_f1_percent": round(macro_f1, 2),
        "per_label": per_label,
    }


def build_messages(prompt: str, software_name: str) -> list[dict[str, str]]:
    if "${software_name}" in prompt:
        return [{"role": "user", "content": prompt.replace("${software_name}", software_name)}]
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Software name: {software_name}"},
    ]


def call_openai(
    *,
    prompt: str,
    software_name: str,
    model: str,
    api_key: str,
    api_url: str,
    timeout_seconds: int,
) -> str:
    payload = {
        "model": model,
        "messages": build_messages(prompt, software_name),
        "temperature": 0,
        "max_tokens": 32,
    }
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc

    return body["choices"][0]["message"]["content"]


def evaluate_prompt(
    *,
    prompt: str,
    model: str = "gpt-4o-mini",
    test_data: Path = DEFAULT_TEST_DATA,
    fapo_results_path: Path = DEFAULT_FAPO_RESULTS,
    level: str = DEFAULT_LEVEL,
    allowed_labels: list[str] | None = None,
    api_key: str | None = None,
    api_url: str = DEFAULT_API_URL,
    timeout_seconds: int = 60,
    use_fapo_reference: bool = False,
) -> dict[str, Any]:
    level_config = get_level_config(level)
    active_labels = allowed_labels or list(level_config["labels"])
    valid_labels = set(active_labels)
    cases = load_test_cases(test_data)
    fapo_results = load_fapo_results(fapo_results_path)
    fapo_by_id = {case["case_id"]: case["prediction"] for case in fapo_results.get("cases", [])}

    if not use_fapo_reference and not api_key:
        raise ValueError("OPENAI_API_KEY is required unless --fapo-reference is used.")

    rows: list[dict[str, Any]] = []
    for case in cases:
        if use_fapo_reference:
            raw_output = fapo_by_id.get(case.case_id, "")
        else:
            raw_output = call_openai(
                prompt=prompt,
                software_name=case.software_name,
                model=model,
                api_key=api_key or "",
                api_url=api_url,
                timeout_seconds=timeout_seconds,
            )
        prediction = normalize_label(raw_output)
        rows.append(
            {
                "case_id": case.case_id,
                "software_name": case.software_name,
                "expected": case.expected,
                "prediction": prediction,
                "raw_output": raw_output,
                "correct": prediction == case.expected,
                "valid_label": prediction in valid_labels,
                "difficulty": case.difficulty,
                "ambiguity_type": case.ambiguity_type,
                "fapo_prediction": fapo_by_id.get(case.case_id, ""),
                "fapo_correct": fapo_by_id.get(case.case_id, "") == case.expected,
            }
        )

    summary = summarize_pairs([(row["expected"], row["prediction"]) for row in rows])
    return {
        "level": level,
        "allowed_labels": active_labels,
        "model": model,
        "use_fapo_reference": use_fapo_reference,
        "summary": summary,
        "fapo_reference": fapo_results,
        "cases": rows,
    }


def print_result(result: dict[str, Any]) -> None:
    summary = result["summary"]
    fapo_summary = result["fapo_reference"]["summary"]
    print(f"Level: {result['level']} ({len(result['allowed_labels'])} labels)")
    print(
        "Manual prompt: "
        f"{summary['micro_f1_percent']:.2f} micro-F1 "
        f"({summary['correct']}/{summary['total']})"
    )
    print(
        "FAPO reference: "
        f"{fapo_summary['micro_f1_percent']:.2f} micro-F1 "
        f"({fapo_summary['correct']}/{fapo_summary['total']})"
    )
    print()
    print("case_id       software_name       expected                       predicted")
    print("-" * 86)
    for row in result["cases"]:
        marker = "OK" if row["correct"] else "MISS"
        print(
            f"{row['case_id']:<13} {row['software_name']:<19} "
            f"{row['expected']:<30} {row['prediction']:<30} {marker}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone mini challenge evaluator.")
    parser.add_argument("--prompt", type=Path, required=True, help="Path to a prompt text file.")
    parser.add_argument(
        "--level",
        choices=sorted(LEVEL_CONFIG),
        default=DEFAULT_LEVEL,
        help="Mini challenge level. Defaults to difficult.",
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to evaluate.")
    parser.add_argument("--test-data", type=Path, help="Optional custom mini test JSONL path.")
    parser.add_argument(
        "--fapo-results",
        type=Path,
        help="Optional custom bundled FAPO v006 results JSON.",
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="OpenAI chat completions endpoint.")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="Per-request timeout.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--fapo-reference",
        dest="use_fapo_reference",
        action="store_true",
        help="Score the bundled FAPO v006 reference instead of calling OpenAI.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prompt = args.prompt.read_text(encoding="utf-8")
    level_config = get_level_config(args.level)
    result = evaluate_prompt(
        prompt=prompt,
        model=args.model,
        test_data=args.test_data or level_config["test_data"],
        fapo_results_path=args.fapo_results or level_config["fapo_results"],
        level=args.level,
        allowed_labels=list(level_config["labels"]),
        api_key=os.environ.get("OPENAI_API_KEY"),
        api_url=args.api_url,
        timeout_seconds=args.timeout_seconds,
        use_fapo_reference=args.use_fapo_reference,
    )
    print_result(result)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
