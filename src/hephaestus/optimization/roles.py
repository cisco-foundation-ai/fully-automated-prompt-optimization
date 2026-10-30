# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""LLM roles for the headless optimization loop.

Each role is one JSON-in/JSON-out call against any provider exposing
``generate_json(system_prompt, payload)``. Responses are validated in code and
retried once with the validation errors before the role is declared failed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, TypeVar

from src.hephaestus.optimization.policy import OptimizationPolicy
from src.hephaestus.optimization.review import ReviewIssue, has_blocking, review_parameter_changes

T = TypeVar("T")

PLAN_SCOPES = ("edit", "rewrite")

ANALYST_SYSTEM_PROMPT = """\
You are the failure analyst and planner in an automated optimization loop for an LLM chain.

You receive the parent candidate's prompt modules (the pool member this iteration branches from,
not necessarily the best one), `training_overview` (every training case with its input, expected
output, metadata, and whether the parent passes it, when the training split is small enough),
detailed views of the parent's failing TRAINING cases, a rule-based failure attribution, tenant
guidance, the scorer source, and the history of attempts in this run. History covers every
candidate tried, including ones that were not selected. Each entry lists which training cases it
fixed (`improved_case_ids`) and broke (`regressed_case_ids`) relative to its `parent_id`, and
`p_improve` (the probability that its validation gain was real) when it was validated. Entries
with `merge_of` combined the changes of two earlier candidates. Learn from rejected attempts too.

Do the following:
1. Study the whole training overview, including passing cases and metadata, to understand the
   structure of the task: what kinds of inputs map to each expected output, and which kinds are
   easy to confuse.
2. Group the failing training cases into clusters by the nature of the failure (for example
   "answer includes explanation preamble" or "multi-entity questions miss the second entity"),
   not merely by step name. Give each cluster a concise label.
3. Assign each cluster the optimization level from `allowed_levels` that would fix it:
   "prompt" for reasoning, format, or instruction-following failures that better prompt text can
   fix; "parameter" for failures that a change to a parameter in `parameter_space` can fix.
4. Choose up to `max_plans` changes to try next (the plans). Each one is evaluated separately
   and the best is kept, so make them as different as possible: different modules, or different
   techniques for the same module. Order them from most to least promising. A prompt plan
   changes exactly one module and has a `scope`:
   - "rewrite": restructure the whole prompt. Choose this when the prompt lacks explicit
     definitions or a decision procedure for the output space, or when several clusters share
     that root cause. A good rewrite generalizes from the whole training overview, for example
     by defining every output category through the kinds of inputs that belong to it and adding
     decision rules for recurring confusions.
   - "edit": one focused change to a prompt that is already comprehensive.
   When levels tie, prefer "prompt".
5. Never repeat a technique listed in `techniques_tried_since_improvement` for the chosen level.
   Pick a distinct technique, for example: comprehensive category definitions, output-format
   constraints, step-by-step decomposition, explicit decision rules, negative examples,
   synthetic few-shot examples, role framing, constraint tightening, or ablating a recent
   addition that did not help.
6. A parameter plan sets `parameter_changes` using only paths in `parameter_space`, with values
   inside their declared bounds that differ from `current_values`.
7. If `previous_errors` is present, your previous answer was rejected for those reasons; fix them.

Return one JSON object:
{"clusters": [{"label": str, "count": int, "case_ids": [str], "level": "prompt" | "parameter",
               "module": str | null, "suggested_fix": str}],
 "plans": [{"level": "prompt" | "parameter", "module": str | null, "scope": "edit" | "rewrite",
            "parameter_changes": {"<path>": <value>} | null, "technique": str,
            "hypothesis": str, "target_case_ids": [str]}]}
"""

PROMPT_PROPOSER_SYSTEM_PROMPT = """\
You write a new version of one prompt module of an LLM chain. You receive the current prompt,
the plan (scope, technique, hypothesis), the analyst's failure clusters, the failing training
cases the plan targets, `training_overview` (every training case with its input, expected
output, metadata, and pass/fail status, when available), tenant guidance, and the scorer source.

Follow the plan's scope:
- "rewrite": write a complete, well-structured prompt that generalizes from the whole training
  overview. For classification-like tasks, define every output category through the kinds of
  inputs that belong to it and add decision rules for the recurring confusions. Keep anything
  in the current prompt that still holds.
- "edit": make one focused change that implements the plan's technique, and keep the rest of the
  prompt intact unless the plan says to remove something.

Rules. Violations are detected automatically and the variant is rejected:
- Instructions must be general. Never add clauses that target a specific case, case ID, entity,
  or answer from the cases you are shown.
- Never copy training inputs into the prompt, not even a single name or identifier. Describe the
  kind of input instead of naming a specific one.
- If you add few-shot examples, invent synthetic ones that are clearly different from every
  training case.
- Keep every `${placeholder}` exactly as in the current prompt. Do not add, remove, or rename any.
- Keep the `System:` / `User:` section markers if the current prompt has them.
- Keep the output format the scorer depends on.
- If `review_issues` is present, your previous attempt was rejected for those reasons; fix them.
- If `previous_errors` is present, your previous answer was malformed; fix it.

Return one JSON object:
{"prompt": "<the complete new prompt text>", "change_summary": "<one or two sentences>"}
"""

REVIEWER_SYSTEM_PROMPT = """\
You independently review a proposed prompt change before it is evaluated. You did not write it
and have no stake in it. You receive the previous prompt, the proposed prompt, the plan's scope
and hypothesis, and a sample of training cases.

Check:
1. example_specific_hint (block): instructions that only make sense for one particular input,
   rules so narrow they could fire on only one case, or references to specific entities or
   answers from the training samples.
2. train_leakage (block): few-shot examples or text copied from, or closely paraphrasing, the
   training samples.
3. scorer_compatibility (block): the change breaks an output format the previous prompt required.
4. focus (warn): for `scope` "edit" only, the change addresses concerns unrelated to the
   hypothesis. A "rewrite" is expected to restructure the whole prompt.

Return one JSON object:
{"verdict": "pass" | "warn" | "fail",
 "issues": [{"check": str, "severity": "block" | "warn", "description": str}]}
Use "fail" only when at least one issue has severity "block".
"""


class JsonGenerator(Protocol):
    """Provider interface used by every role."""

    def generate_json(self, system_prompt: str, payload: Mapping[str, Any]) -> Dict[str, Any]: ...


class RoleError(RuntimeError):
    """A role kept returning output that failed validation."""


@dataclass
class Plan:
    """The single change the analyst chose to try next."""

    level: str
    module: Optional[str]
    parameter_changes: Dict[str, Any]
    technique: str
    hypothesis: str
    target_case_ids: List[str] = field(default_factory=list)
    scope: str = "edit"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "module": self.module,
            "scope": self.scope,
            "parameter_changes": dict(self.parameter_changes) or None,
            "technique": self.technique,
            "hypothesis": self.hypothesis,
            "target_case_ids": list(self.target_case_ids),
        }


@dataclass
class Analysis:
    """Analyst output: failure clusters plus the plans to try, most promising first."""

    clusters: List[Dict[str, Any]]
    plans: List[Plan]

    @property
    def plan(self) -> Plan:
        return self.plans[0]


@dataclass
class PromptProposal:
    """Prompt proposer output."""

    prompt: str
    change_summary: str


class RoleClient:
    """Runs role calls with validation retries and per-role token accounting."""

    def __init__(self, generator: JsonGenerator, max_attempts: int = 2) -> None:
        self.generator = generator
        self.max_attempts = max_attempts
        self._usage: Dict[str, Dict[str, int]] = {}

    def call(
        self,
        role: str,
        system_prompt: str,
        payload: Mapping[str, Any],
        parse: Callable[[Dict[str, Any]], T],
    ) -> T:
        """Call ``role`` and return its parsed output.

        Raises:
            RoleError: If every attempt returned output that ``parse`` rejected.
        """
        errors: List[str] = []
        for _ in range(self.max_attempts):
            request = dict(payload, role=role)
            if errors:
                request["previous_errors"] = list(errors)
            try:
                raw = self.generator.generate_json(system_prompt, request)
            finally:
                self._record_usage(role)
            try:
                if not isinstance(raw, dict):
                    raise ValueError("response must be a JSON object")
                return parse(raw)
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(str(exc))
        raise RoleError(f"{role} returned invalid output: {errors[-1]}")

    def take_usage(self) -> Dict[str, Dict[str, int]]:
        """Return token usage accumulated since the last call and reset it."""
        usage, self._usage = self._usage, {}
        return usage

    def _record_usage(self, role: str) -> None:
        drain = getattr(self.generator, "drain_call_metadata", None)
        if not callable(drain):
            return
        totals = self._usage.setdefault(role, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        for row in drain():
            totals["calls"] += 1
            usage = row.get("usage") or {}
            for key in ("input_tokens", "output_tokens"):
                if isinstance(usage.get(key), int):
                    totals[key] += usage[key]


def parse_analysis(
    raw: Dict[str, Any],
    *,
    allowed_levels: Sequence[str],
    modules: Sequence[str],
    current_values: Mapping[str, Any],
    policy: OptimizationPolicy,
    max_plans: int = 1,
) -> Analysis:
    """Validate analyst output against the levels, modules, and parameters in scope.

    Accepts ``plans`` (a list) or a single ``plan``. Duplicate plans are dropped
    and at most ``max_plans`` are kept.
    """
    plans_raw = raw.get("plans")
    single = plans_raw is None and "plan" in raw
    if single:
        plans_raw = [raw.get("plan")]
    if not isinstance(plans_raw, list) or not plans_raw:
        raise ValueError("plans must be a non-empty list")
    plans: List[Plan] = []
    for index, plan_raw in enumerate(plans_raw):
        name = "plan" if single else f"plans[{index}]"
        plan = _parse_plan(plan_raw, name, allowed_levels, modules, current_values, policy)
        if all(plan.to_dict() != kept.to_dict() for kept in plans):
            plans.append(plan)
    clusters = raw.get("clusters") if isinstance(raw.get("clusters"), list) else []
    return Analysis(
        clusters=[cluster for cluster in clusters if isinstance(cluster, dict)],
        plans=plans[:max_plans],
    )


def _parse_plan(
    plan_raw: Any,
    scope_name: str,
    allowed_levels: Sequence[str],
    modules: Sequence[str],
    current_values: Mapping[str, Any],
    policy: OptimizationPolicy,
) -> Plan:
    if not isinstance(plan_raw, dict):
        raise ValueError(f"{scope_name} must be an object")
    level = plan_raw.get("level")
    if level not in allowed_levels:
        raise ValueError(f"{scope_name}.level must be one of {list(allowed_levels)}, got {level!r}")
    technique = _required_text(plan_raw, "technique", scope_name)
    hypothesis = _required_text(plan_raw, "hypothesis", scope_name)
    module = plan_raw.get("module")
    scope = plan_raw.get("scope") or "edit"
    parameter_changes: Dict[str, Any] = {}
    if level == "prompt":
        if module not in modules:
            raise ValueError(f"{scope_name}.module must be one of {list(modules)}, got {module!r}")
        if scope not in PLAN_SCOPES:
            raise ValueError(f"{scope_name}.scope must be one of {list(PLAN_SCOPES)}, got {scope!r}")
    else:
        module = None
        scope = "edit"
        changes = plan_raw.get("parameter_changes")
        if not isinstance(changes, dict):
            raise ValueError(f"{scope_name}.parameter_changes must be an object for a parameter plan")
        issues = review_parameter_changes(changes, current_values, policy)
        if has_blocking(issues):
            raise ValueError("; ".join(issue.description for issue in issues))
        parameter_changes = dict(changes)
    target_case_ids = plan_raw.get("target_case_ids") or []
    return Plan(
        level=level,
        module=module,
        parameter_changes=parameter_changes,
        technique=technique,
        hypothesis=hypothesis,
        target_case_ids=[str(case_id) for case_id in target_case_ids if isinstance(case_id, str)],
        scope=scope,
    )


def parse_prompt_proposal(raw: Dict[str, Any]) -> PromptProposal:
    """Validate prompt proposer output."""
    prompt = raw.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    summary = raw.get("change_summary")
    return PromptProposal(prompt=prompt, change_summary=summary if isinstance(summary, str) else "")


def parse_review(raw: Dict[str, Any]) -> List[ReviewIssue]:
    """Validate reviewer output and return its issues."""
    verdict = raw.get("verdict")
    if verdict not in ("pass", "warn", "fail"):
        raise ValueError(f"verdict must be 'pass', 'warn', or 'fail', got {verdict!r}")
    issues_raw = raw.get("issues") or []
    if not isinstance(issues_raw, list):
        raise ValueError("issues must be a list")
    issues = []
    for item in issues_raw:
        if not isinstance(item, dict):
            raise ValueError("each issue must be an object")
        severity = "block" if item.get("severity") == "block" else "warn"
        issues.append(
            ReviewIssue(
                check=f"llm_{item.get('check', 'review')}",
                severity=severity,
                description=str(item.get("description", "")),
            )
        )
    if verdict == "fail" and not has_blocking(issues):
        issues.append(ReviewIssue("llm_review", "block", "reviewer returned 'fail' without a blocking issue"))
    return issues


def _required_text(raw: Mapping[str, Any], key: str, scope: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{scope}.{key} must be a non-empty string")
    return value.strip()
