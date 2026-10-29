# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Input records and a scripted model shared by the data pipeline tests."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.hephaestus.data_pipeline.prompts import OBSERVE_PROMPT, RUBRIC_PROMPT, SYNTHESIZE_PROMPT

CRITERION = {
    "kind": "required",
    "statement": "Confirms the order before changing it",
    "applicability": "The user asks to change an order",
    "severity": "critical",
    "scoring": "Satisfied when the agent confirms first",
}


def make_record(
    record_id: str,
    *,
    labeled: bool,
    group_id: Optional[str] = None,
    rationale: str = "The agent changed the order without confirming it.",
    route: Optional[str] = None,
) -> Dict[str, Any]:
    """Return one valid input record."""
    row: Dict[str, Any] = {
        "schema_version": "fafo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": group_id or f"group-{record_id}",
        "task_type": "support",
        "user_input": f"Please change order {record_id}.",
        "conversation_context": [],
        "tool_calls": [
            {"name": "update_order", "arguments": {"order": record_id}, "result": {"status": "ok"}}
        ],
        "runtime": {},
        "metadata": {},
    }
    if route:
        row["route"] = route
    if labeled:
        row["assistant_output"] = "Done."
        row["feedback"] = {"polarity": "negative", "rationale": rationale}
    return row


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class ScriptedModel:
    """Deterministic stand-in for the pipeline model.

    Observe returns one lesson per episode that quotes the feedback rationale
    (or the user input when there is no feedback). Synthesize returns one
    guideline per route citing every lesson, with the lessons' text in its
    title. Rubric picks every catalog guideline and copies any feedback
    rationale into a case criterion, so tests can trace where text travels.
    """

    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.fail_rubrics_for: set[str] = set()
        self.empty_rubrics_for: set[str] = set()

    def generate_json(self, system_prompt: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self.requests.append({"system_prompt": system_prompt, "payload": json.loads(json.dumps(payload))})
        if system_prompt == OBSERVE_PROMPT:
            return {"episodes": [self._observe(episode) for episode in payload["episodes"]]}
        if system_prompt == SYNTHESIZE_PROMPT:
            lessons = list(payload["lessons"])
            if payload.get("current"):
                lessons_seen = payload["current"]["guidelines"][0]["lesson_ids"]
            else:
                lessons_seen = []
            ids = [*lessons_seen, *(lesson["lesson_id"] for lesson in lessons)]
            return {
                "guidelines": [
                    {
                        "title": " / ".join(lesson["lesson"] for lesson in lessons)[:200],
                        "dividing_line": "The user asked for a change",
                        "criteria": [CRITERION],
                        "lesson_ids": ids,
                        "counter_examples": [],
                    }
                ],
                "facts": [],
                "cannot_fix": [],
                "set_aside": [],
            }
        if system_prompt == RUBRIC_PROMPT:
            record_id = payload["episode"]["record_id"]
            if record_id in self.fail_rubrics_for:
                raise ConnectionError("provider unavailable")
            if record_id in self.empty_rubrics_for:
                return {"applicable_guideline_ids": [], "case_criteria": [], "confidence": 0.2}
            feedback = payload.get("trusted_feedback") or {}
            case_criteria = []
            if feedback.get("rationale"):
                case_criteria.append({**CRITERION, "statement": feedback["rationale"]})
            return {
                "applicable_guideline_ids": [g["guideline_id"] for g in payload["catalog"]],
                "case_criteria": case_criteria,
                "tool_expectations": {},
                "reference_output": None,
                "intent_label": "change order",
                "confidence": 0.8,
            }
        raise AssertionError("unexpected system prompt")

    def count(self, system_prompt: str) -> int:
        return sum(1 for request in self.requests if request["system_prompt"] == system_prompt)

    @staticmethod
    def _observe(episode: Mapping[str, Any]) -> Dict[str, Any]:
        feedback = episode.get("feedback")
        if feedback:
            quote = {"source": "feedback", "text": feedback["rationale"]}
            text, signal = f"Lesson from feedback: {feedback['rationale']}", "explicit"
        else:
            quote = {"source": "trace", "text": episode["transcript"][0]["content"]}
            text, signal = "Lesson from the trace", "clear"
        lesson = {
            "type": "failure",
            "lesson": text,
            "evidence": [quote],
            "signal": signal,
            "knowable": True,
            "confidence": 0.9,
        }
        return {"record_id": episode["record_id"], "lessons": [lesson]}
