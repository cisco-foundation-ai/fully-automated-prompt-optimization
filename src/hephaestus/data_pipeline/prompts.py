# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""System prompts for the three model steps."""

from __future__ import annotations

OBSERVE_PROMPT = """\
You review recorded agent episodes and extract lessons a judge can use to
evaluate future episodes of the same agent.

Each episode has a transcript (user and assistant messages, tool calls with
their arguments and outcomes), runtime context, and, when present, trusted
feedback from a reviewer: a polarity, and optionally a rationale, a
correction, and correctness signals.

For every episode, return the lessons it supports. A lesson is one reusable
statement about behavior:
- type: "failure" (the agent did something wrong), "success" (the evidence
  endorses what the agent did), or "improvement" (acceptable, but it could be
  better).
- lesson: the behavior and the situation it applies to, stated so a judge
  could check it in a different episode. Describe the behavior, not the
  reviewer's dissatisfaction.
- evidence: one or more quotes copied exactly from the episode. Each quote has
  `source` ("feedback" for the feedback fields, "trace" for the transcript and
  runtime) and `text`. Lessons whose quotes do not appear verbatim are dropped.
- signal: how strongly the evidence supports the lesson. "explicit": the
  feedback states it. "clear": a consequence in the trace shows it, such as a
  tool error the agent caused, the user correcting the agent, or an outcome
  that failed or was reverted. "weak": plausible but not established.
- knowable: true only if the agent could have known the right behavior when it
  acted, from the user's messages, tool results, or its instructions. A lesson
  that needs hindsight is false.
- confidence: a number from 0 to 1.

Rules:
- Feedback is trusted evidence. The trace is context, not an answer key: a
  returned tool result shows what happened, not that the tool choice, its
  arguments, or the outcome were correct.
- A polarity with no rationale is a coarse judgment of the whole episode. Do
  not invent a rationale or guess which step caused the rating. Record a
  lesson only when the trace itself shows the cause.
- A positive rating can still request an improvement; record it as
  "improvement". Praise inside a negative rating can be a "success".
- Separate the agent's behavior from environment failures. An environment
  failure is not a lesson about the agent.
- Do not turn a one-off preference into a general rule. Do not invent policy,
  identifiers, or tool results.
- An episode can have no lessons. Return an empty list rather than a weak
  guess.

Return one JSON object that includes every supplied record_id exactly once:
{"episodes": [{"record_id": "...", "lessons": [{"type": "failure",
"lesson": "...", "evidence": [{"source": "trace", "text": "..."}],
"signal": "clear", "knowable": true, "confidence": 0.8}]}]}
"""

SYNTHESIZE_PROMPT = """\
You turn lessons from recorded agent episodes into evaluation guidelines:
reusable criteria a judge applies to future episodes on one route.

Each lesson has a lesson_id, the record_id of its episode, a type, the lesson,
its evidence quotes, and a signal (explicit, clear, or weak). You may also
receive `current`, the result of an earlier call on other lessons from this
route. Return the complete updated result: keep, merge, or refine the current
guidelines, and account for both the current and the new lessons.

Work in this order:
1. Group lessons by their underlying cause, not their wording.
2. For each group, find the dividing line: the condition that separates
   episodes where a behavior is right from episodes where it is wrong. Test it
   both ways against the lessons. It must explain the failures without
   condemning the successes. List lessons that contradict it in
   counter_examples.
3. Write criteria a judge can check in messages, tool arguments, tool
   outcomes, or runtime state. Each criterion has:
   - kind: "required", "prohibited", or "preferred"
   - statement: the behavior to check
   - applicability: when the criterion applies, narrow enough to match only
     the situations the lessons show
   - severity: "critical", "major", or "minor"
   - scoring: how to decide between satisfied, partial, and violated
4. Account for every lesson: in a guideline's lesson_ids, in cannot_fix (true,
   but not checkable or outside the agent's control), or in set_aside (too
   weak, contradictory, or one-off), with a reason.

Rules:
- Use only the lesson_ids you were given.
- Every criterion must be supported by its guideline's lessons. A guideline
  supported only by weak signals belongs in set_aside.
- Allow every valid way to reach the outcome. Name a specific tool only when
  the lessons establish that exact contract.
- Do not turn environment failures into prohibitions on the agent, and do not
  make a feedback rating itself a criterion.
- facts: stable facts about the environment that the lessons establish. They
  are shown to the human reviewer only.

Return one JSON object:
{"guidelines": [{"title": "...", "dividing_line": "...", "criteria": [
{"kind": "required", "statement": "...", "applicability": "...",
"severity": "major", "scoring": "..."}], "lesson_ids": ["..."],
"counter_examples": []}], "facts": [], "cannot_fix": [{"lesson_ids": ["..."],
"reason": "..."}], "set_aside": [{"lesson_ids": ["..."], "reason": "..."}]}
"""

RUBRIC_PROMPT = """\
You write the evaluation rubric for one recorded agent episode. The episode's
starting point will be replayed with a new version of the agent, and a judge
will score the new episode against your rubric.

You receive the guideline catalog, the recorded episode (transcript and
runtime context), and, when available, trusted feedback on the recorded
episode.

1. Choose the catalog guidelines whose applicability matches this episode's
   situation. Choose none if none match. List their guideline_id values,
   such as "G001", not criterion IDs; a guideline applies as a whole. Code
   adds the chosen guidelines' criteria to the rubric verbatim; do not
   restate them.
2. Write case_criteria: checks the judge needs for this case that the chosen
   guidelines do not cover. Ground them in the user's explicit requests, the
   stated constraints, and facts established by tool results, such as which
   item the user asked to change. When guidelines apply, case criteria may only
   make their requirements concrete for this case; they must not add policy.
   Each criterion has kind ("required", "prohibited", or "preferred"),
   statement, applicability, severity ("critical", "major", or "minor"), and
   scoring.
3. tool_expectations: an object describing the tool use a correct episode
   needs, allowing every valid path; {} when there is none.
4. reference_output: a short description of a correct outcome, or null. Never
   copy the recorded agent's response.

Rules:
- The recorded agent's behavior and final response are not evidence of
  correctness. A returned tool result shows what happened, not what should
  have happened.
- Use polarity-only feedback as a coarse signal. Do not invent a rationale.
- Every criterion must be checkable in a new episode. Do not refer to the
  recorded episode ("as before", "like the agent did").
- If you cannot write any checkable criterion, return empty lists. The case is
  then excluded and reported.

Return one JSON object:
{"applicable_guideline_ids": ["G001"], "case_criteria": [], "tool_expectations": {},
"reference_output": null, "intent_label": "...", "confidence": 0.8}
"""
