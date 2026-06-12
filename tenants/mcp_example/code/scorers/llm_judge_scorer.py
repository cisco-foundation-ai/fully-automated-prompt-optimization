# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""LLM-as-judge scorer for mcp_example tenant.

A LangSmith-style reference-based LLM evaluator. Instead of brittle substring
matching, an LLM grades the agent's answer against the task and an expected
reference, returning a 0-100 score plus a short rationale (the rationale lands
in the score breakdown's companion diagnostics, mirroring LangSmith feedback's
``score`` + ``comment`` shape).

Configuration (via ``scoring_profile.judge``):

    "judge": {
        "provider": "openai",                  # defaults to the run provider
        "provider_settings": {"model": "gpt-4o-mini", "temperature": 0.0},
        "rubric": "Award full marks only if ...",   # optional extra guidance
        "fallback_score": 50.0                 # used if the judge call fails
    }

The judge call is best-effort: any failure (provider error, unparseable
response) degrades to ``fallback_score`` with an explanatory comment so a flaky
judge never crashes the eval run.
"""

import json
import re
from typing import Any, Dict, List, Optional

from src.hephaestus.providers import build_provider_client
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

DEFAULT_FALLBACK_SCORE = 50.0

_JUDGE_SYSTEM_PROMPT = """\
You are a strict evaluation judge for an AI agent's answer to a task.
Grade ONLY how well the agent's answer satisfies the task and matches the
expected reference. Ignore style and verbosity. Respond with a single JSON
object and nothing else, in exactly this form:

{"score": <integer 0-100>, "reason": "<one concise sentence>"}

Scoring guidance:
- 100: answer is fully correct and contains the expected information.
- 50-99: partially correct or correct but incomplete/ambiguous.
- 0-49: incorrect, missing, or contradicts the expected reference.
"""


class LLMJudgeScorer(BaseScorer):
    """Score answer correctness with an LLM judge.

    Thread-safety: the judge provider is built lazily once and reused. Provider
    clients here are stateless per-call, so concurrent ``score_*`` calls under
    ``max_workers > 1`` are safe.
    """

    def __init__(self):
        self._judge_provider = None
        self._judge_provider_key = None

    def validate_case(self, case, scoring_profile):
        assert "task" in case.context, f"Case {case.case_id}: missing 'task'"
        assert case.expected is not None, f"Case {case.case_id}: missing expected dict"

    def score_case(self, case, output_text, scoring_profile):
        return self.score_pipeline_case(
            case, {}, scoring_profile, output_text=output_text, tool_call_history=None
        )

    def score_pipeline_case(
        self,
        case,
        step_outputs: Dict[str, str],
        scoring_profile: Dict[str, Any],
        output_text: Optional[str] = None,
        tool_call_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        output_text = output_text or ""
        judge_cfg = scoring_profile.get("judge", {}) or {}
        fallback = float(judge_cfg.get("fallback_score", DEFAULT_FALLBACK_SCORE))

        task = case.context.get("task", "")
        expected = case.expected or {}
        reference = expected.get("answer_contains", "")
        rubric = judge_cfg.get("rubric", "")

        user_prompt = self._build_user_prompt(task, reference, output_text, rubric)

        try:
            provider = self._get_judge_provider(judge_cfg, scoring_profile)
            raw = provider.generate(
                [
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )
            score, reason = self._parse_verdict(raw)
        except Exception as exc:  # noqa: BLE001 - judge must never crash the run
            score, reason = fallback, f"judge_unavailable: {exc}"

        return {
            "composite_score": score,
            "score_breakdown": {
                "answer_correct": score,
                # Surface the rationale as a length signal so it shows up in the
                # numeric breakdown; the full text rides along in diagnostics.
                "judge_reason_chars": float(len(reason)),
            },
        }

    # --- helpers --------------------------------------------------------

    @staticmethod
    def _build_user_prompt(task, reference, answer, rubric) -> str:
        parts = [
            f"TASK:\n{task}",
            f"EXPECTED REFERENCE (answer should contain this):\n{reference}",
            f"AGENT ANSWER:\n{answer}",
        ]
        if rubric:
            parts.append(f"ADDITIONAL RUBRIC:\n{rubric}")
        return "\n\n".join(parts)

    def _get_judge_provider(self, judge_cfg, scoring_profile):
        provider_name = str(judge_cfg.get("provider", "openai")).strip().lower()
        provider_settings = dict(judge_cfg.get("provider_settings", {}))
        # Cache key so a changed config (rare) rebuilds the client.
        key = (provider_name, json.dumps(provider_settings, sort_keys=True))
        if self._judge_provider is None or self._judge_provider_key != key:
            self._judge_provider = build_provider_client(provider_name, provider_settings)
            self._judge_provider_key = key
        return self._judge_provider

    @staticmethod
    def _parse_verdict(raw: str) -> tuple:
        """Extract (score, reason) from the judge's JSON response.

        Tolerant of code fences or leading prose: grabs the first JSON object.
        """
        if not raw:
            raise ValueError("empty judge response")
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"no JSON object in judge response: {raw[:200]!r}")
        data = json.loads(match.group(0))
        score = float(data["score"])
        score = max(0.0, min(100.0, score))
        reason = str(data.get("reason", ""))
        return score, reason
