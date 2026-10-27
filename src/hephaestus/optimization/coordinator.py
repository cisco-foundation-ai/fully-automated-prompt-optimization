# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Headless optimization coordinator for prompt and parameter levels.

Runs evaluate -> attribute -> plan -> propose -> review -> evaluate -> accept
without a meta agent. The coordinator is plain code and owns the invariants:

- role payloads only contain per-case data from the training split;
- val and test contribute aggregate scores only, and test runs at most once per
  workspace, after optimization has stopped;
- every variant is a new file, branched from the current best;
- every decision is appended to ``ledger.jsonl``, which a later run resumes from.
"""

from __future__ import annotations

import copy
import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.hephaestus.analysis.step_attribution import attribute_results, summarize
from src.hephaestus.datasets.jsonl_loader import load_cases
from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.optimization.policy import OptimizationPolicy
from src.hephaestus.optimization.review import (
    ReviewIssue,
    has_blocking,
    placeholders,
    review_prompt_variant,
)
from src.hephaestus.optimization.roles import (
    ANALYST_SYSTEM_PROMPT,
    PROMPT_PROPOSER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    Analysis,
    JsonGenerator,
    Plan,
    RoleClient,
    RoleError,
    parse_analysis,
    parse_prompt_proposal,
    parse_review,
)
from src.hephaestus.runs.bundle import load_run_bundle
from src.hephaestus.runs.eval_runner import load_eval_config, run_evaluation

logger = logging.getLogger(__name__)

LEDGER_FILE = "ledger.jsonl"
BEST_CONFIG_FILE = "best-config.json"
BASELINE_ID = "c000"
ROLE_MAX_OUTPUT_TOKENS = 16000
TEXT_LIMIT = 1500
OVERVIEW_TEXT_LIMIT = 300
FLIP_LIMIT = 40
DOCUMENT_LIMIT = 8000
HISTORY_LIMIT = 20
PROPOSAL_ATTEMPTS = 2

_LICENSE_HEADER = re.compile(r"\A\s*<!--.*?-->[ \t]*\n?", re.S)
_VARIANT_FILE = re.compile(r"^variant-(\d+)\.md$")
_PER_EVAL_KEYS = ("dataset", "output_dir", "run_id")


@dataclass
class SplitScore:
    """Aggregate result of one candidate on one split."""

    score: float  # mean composite score, failed executions counted as 0
    cases: int
    failed: int
    output_dirs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "cases": self.cases,
            "failed": self.failed,
            "output_dirs": list(self.output_dirs),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SplitScore":
        return cls(
            score=float(raw["score"]),
            cases=int(raw["cases"]),
            failed=int(raw["failed"]),
            output_dirs=list(raw.get("output_dirs", [])),
        )


@dataclass
class CandidateState:
    """A fully evaluated candidate the loop can branch from."""

    candidate_id: str
    config: Dict[str, Any]
    train: SplitScore
    val: Optional[SplitScore]
    train_results: List[Mapping[str, Any]]

    @property
    def selection_score(self) -> float:
        return self.val.score if self.val is not None else self.train.score


@dataclass
class OptimizationResult:
    """Outcome of one :func:`run_optimization` call."""

    stop_reason: str
    iterations: int
    baseline: CandidateState
    best: CandidateState
    best_config_path: Path
    ledger_path: Path
    test: Optional[Dict[str, Any]] = None


def run_optimization(
    policy: OptimizationPolicy,
    workspace: Path,
    *,
    generator: Optional[JsonGenerator] = None,
    resume: bool = False,
    final_test: bool = False,
) -> OptimizationResult:
    """Run the headless optimization loop.

    Args:
        policy: Validated optimization policy.
        workspace: Directory for the ledger, generated eval configs, and eval outputs.
        generator: JSON generator used by every role. Defaults to an OpenAI
            generator on ``policy.role_model``.
        resume: Continue the ledger already in ``workspace``.
        final_test: After optimization stops, evaluate the baseline and best
            candidate once on the test split.

    Returns:
        The optimization result.
    """
    if generator is None:
        generator = OpenAIRubricProvider(model=policy.role_model, max_output_tokens=ROLE_MAX_OUTPUT_TOKENS)
    return _Coordinator(policy, workspace, generator).run(resume=resume, final_test=final_test)


class _Coordinator:
    def __init__(self, policy: OptimizationPolicy, workspace: Path, generator: JsonGenerator) -> None:
        self.policy = policy
        self.workspace = workspace
        self.ledger_path = workspace / LEDGER_FILE
        self.roles = RoleClient(generator)
        self.base_config = _candidate_config(json.loads(Path(policy.base_config).read_text(encoding="utf-8")))
        prompt_paths = self.base_config.get("chain", {}).get("config", {}).get("prompt_paths", {})
        self.modules = list(policy.prompt_modules or prompt_paths)
        unknown = sorted(set(self.modules) - set(prompt_paths))
        if unknown:
            raise ValueError(f"prompt_modules {unknown} are not in the base config's prompt_paths")
        if "prompt" in policy.levels and not self.modules:
            raise ValueError("the prompt level requires prompt_paths in the base config")
        self.train_cases = load_cases(Path(policy.train_dataset))
        self.train_cases_by_id = {case.case_id: case for case in self.train_cases}
        # Held-out inputs are used only by the static review; they never enter a role payload.
        self.heldout_cases = [
            case
            for path in (policy.val_dataset, policy.test_dataset)
            if path
            for case in load_cases(Path(path))
        ]
        self.guidance = {
            path: _clip(Path(path).read_text(encoding="utf-8"), DOCUMENT_LIMIT)
            for path in policy.guidance_paths
        }
        scorer_path = self.base_config.get("scoring_profile", {}).get("scorer", {}).get("module_path")
        self.scorer_source = (
            _clip(Path(scorer_path).read_text(encoding="utf-8"), DOCUMENT_LIMIT)
            if scorer_path and Path(scorer_path).is_file()
            else ""
        )

    def run(self, *, resume: bool, final_test: bool) -> OptimizationResult:
        if final_test and not self.policy.test_dataset:
            raise ValueError("final_test requires datasets.test in the policy")
        records = self._read_ledger()
        if records and not resume:
            raise ValueError(f"{self.ledger_path} already exists; resume it or choose another workspace")
        if any(record.get("test") for record in records):
            raise ValueError("the test split was already evaluated in this workspace; start a new workspace")

        if records:
            if records[0].get("type") != "baseline":
                raise ValueError(f"{self.ledger_path} does not start with a baseline record")
            baseline = self._restore(records[0])
            if (baseline.val is None) != (self.policy.val_dataset is None):
                raise ValueError("the policy's val split does not match the ledger being resumed")
            best = self._restore(_last_accepted(records) or records[0])
        else:
            baseline = best = self._evaluate_baseline()
            records.append(self._append(_baseline_record(baseline)))
        iterations = [record for record in records if record["type"] == "iteration"]
        iteration = max((record["iteration"] for record in iterations), default=0)
        misses, techniques = _level_state(iterations, self.policy.levels)

        stop_reason = "max_iterations"
        while iteration < self.policy.budget.max_iterations:
            target = self.policy.budget.target_score
            if target is not None and best.selection_score >= target:
                stop_reason = "target_reached"
                break
            patience = self.policy.budget.plateau_patience
            allowed = [level for level in self.policy.levels if misses[level] < patience]
            if not allowed:
                stop_reason = "levels_exhausted"
                break
            failing = self._failing_results(best)
            if not failing:
                stop_reason = "no_train_failures"
                break
            iteration += 1
            record, candidate = self._iterate(iteration, best, allowed, failing, techniques, iterations)
            iterations.append(self._append(record))
            logger.info(
                "iteration %d: %s %s (train %+.2f, val %s)",
                iteration,
                record.get("level"),
                record["reason"],
                record.get("train_delta") or 0.0,
                "n/a" if record.get("val_delta") is None else f"{record['val_delta']:+.2f}",
            )
            if candidate is not None:
                best = candidate
                misses, techniques = _level_state([], self.policy.levels)
            elif record.get("level") in misses:
                misses[record["level"]] += 1
                techniques[record["level"]].append(record["plan"]["technique"])

        best_config_path = self._write_best_config(best)
        test = self._final_test(baseline, best) if final_test else None
        self._append(
            {
                "type": "final",
                "stop_reason": stop_reason,
                "best_candidate_id": best.candidate_id,
                "best_config_path": str(best_config_path),
                "test": test,
            }
        )
        return OptimizationResult(
            stop_reason=stop_reason,
            iterations=iteration,
            baseline=baseline,
            best=best,
            best_config_path=best_config_path,
            ledger_path=self.ledger_path,
            test=test,
        )

    # -- one iteration ------------------------------------------------------

    def _iterate(
        self,
        iteration: int,
        best: CandidateState,
        allowed: Sequence[str],
        failing: Sequence[Mapping[str, Any]],
        techniques: Mapping[str, List[str]],
        history: Sequence[Mapping[str, Any]],
    ) -> Tuple[Dict[str, Any], Optional[CandidateState]]:
        candidate_id = f"c{iteration:03d}"
        record: Dict[str, Any] = {
            "type": "iteration",
            "iteration": iteration,
            "candidate_id": candidate_id,
            "parent_id": best.candidate_id,
            "level": None,
            "accepted": False,
        }
        rng = random.Random(candidate_id)
        shown = sorted(
            rng.sample(list(failing), min(len(failing), self.policy.max_failures_shown)),
            key=lambda result: float(result["composite_score"]),
        )
        failing_cases = [self._case_view(result) for result in shown]
        overview = self._training_overview(best)
        current_values = {
            spec.path: _get_path(best.config, spec.path) for spec in self.policy.parameter_space
        }
        payload = self._analyst_payload(
            best, allowed, len(failing), failing_cases, overview, current_values, techniques, history
        )
        evaluated = [self.base_config] + [record["config"] for record in history if "config" in record]

        def parse(raw: Dict[str, Any]) -> Analysis:
            analysis = parse_analysis(
                raw,
                allowed_levels=allowed,
                modules=self.modules,
                current_values=current_values,
                policy=self.policy,
            )
            changes = analysis.plan.parameter_changes
            if changes and _with_parameters(best.config, changes) in evaluated:
                raise ValueError("these parameter values were already evaluated in this run; choose others")
            return analysis

        try:
            analysis = self.roles.call("analyst", ANALYST_SYSTEM_PROMPT, payload, parse)
            record.update(level=analysis.plan.level, plan=analysis.plan.to_dict(), clusters=analysis.clusters)
            if analysis.plan.level == "prompt":
                config, details = self._prompt_candidate(
                    best, analysis.plan, analysis.clusters, failing_cases, overview
                )
            else:
                config = _with_parameters(best.config, analysis.plan.parameter_changes)
                details = {"parameter_changes": analysis.plan.parameter_changes}
        except RoleError as exc:
            record.update(reason="role_error", error=str(exc), usage=self.roles.take_usage())
            return record, None
        record.update(details, usage=self.roles.take_usage())
        if config is None:
            record["reason"] = "review_failed"
            return record, None

        record["config"] = config
        train, train_results = self._evaluate(candidate_id, config, "train")
        record["train"] = train.to_dict()
        record["train_delta"] = train.score - best.train.score
        record.update(_case_flips(best.train_results, train_results))
        if record["train_delta"] < self.policy.acceptance.min_train_delta:
            record["reason"] = "train_screen"
            return record, None

        acceptance = self.policy.acceptance
        val = None
        selection_delta = record["train_delta"]
        if self.policy.val_dataset:
            val, _ = self._evaluate(candidate_id, config, "val", repeats=acceptance.val_repeats)
            record["val"] = val.to_dict()
            record["val_delta"] = selection_delta = val.score - best.val.score
        val_tie = val is not None and selection_delta >= 0 and record["train_delta"] > 0
        if selection_delta > 0 and selection_delta >= acceptance.min_val_delta:
            reason = "accepted"
        elif acceptance.train_tiebreak and val_tie:
            reason = "accepted_train_tiebreak"
        else:
            reason = "selection_below_threshold"
        accepted = reason != "selection_below_threshold"
        record.update(accepted=accepted, reason=reason)
        if not accepted:
            return record, None
        return record, CandidateState(candidate_id, config, train, val, train_results)

    def _prompt_candidate(
        self,
        best: CandidateState,
        plan: Plan,
        clusters: Sequence[Mapping[str, Any]],
        failing_cases: Sequence[Mapping[str, Any]],
        overview: Optional[List[Dict[str, Any]]],
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        module = plan.module
        parent_path = Path(best.config["chain"]["config"]["prompt_paths"][module])
        header, parent_body = _split_header(parent_path.read_text(encoding="utf-8"))
        targeted = [
            case for case in failing_cases if case["case_id"] in plan.target_case_ids
        ] or list(failing_cases)
        payload: Dict[str, Any] = {
            "module": module,
            "current_prompt": parent_body,
            "placeholders": sorted(placeholders(parent_body)),
            "plan": plan.to_dict(),
            "clusters": list(clusters),
            "failing_cases": targeted,
            "guidance": self.guidance,
            "scorer_source": self.scorer_source,
        }
        if overview is not None:
            payload["training_overview"] = overview
        details: Dict[str, Any] = {"module": module, "parent_prompt_path": str(parent_path), "review": []}
        for _ in range(PROPOSAL_ATTEMPTS):
            proposal = self.roles.call(
                "prompt_proposer", PROMPT_PROPOSER_SYSTEM_PROMPT, payload, parse_prompt_proposal
            )
            issues = self._review(parent_body, proposal.prompt, plan, targeted)
            details["review"].append([issue.to_dict() for issue in issues])
            if not has_blocking(issues):
                break
            payload = dict(
                payload,
                previous_attempt=proposal.prompt,
                review_issues=[issue.to_dict() for issue in issues],
            )
        else:
            return None, details

        new_path = _write_variant(parent_path, header, proposal.prompt)
        config = copy.deepcopy(best.config)
        config["chain"]["config"]["prompt_paths"][module] = str(new_path)
        details.update(prompt_path=str(new_path), change_summary=proposal.change_summary)
        return config, details

    def _review(
        self,
        previous: str,
        proposed: str,
        plan: Plan,
        targeted: Sequence[Mapping[str, Any]],
    ) -> List[ReviewIssue]:
        issues = review_prompt_variant(previous, proposed, self.train_cases, self.heldout_cases)
        if has_blocking(issues) or not self.policy.llm_review:
            return issues
        samples = [{"context": case["context"], "expected": case["expected"]} for case in targeted]
        return issues + self.roles.call(
            "reviewer",
            REVIEWER_SYSTEM_PROMPT,
            {
                "previous_prompt": previous,
                "proposed_prompt": proposed,
                "scope": plan.scope,
                "hypothesis": plan.hypothesis,
                "training_samples": samples,
            },
            parse_review,
        )

    # -- payloads ---------------------------------------------------------

    def _analyst_payload(
        self,
        best: CandidateState,
        allowed: Sequence[str],
        failure_count: int,
        failing_cases: Sequence[Mapping[str, Any]],
        overview: Optional[List[Dict[str, Any]]],
        current_values: Mapping[str, Any],
        techniques: Mapping[str, List[str]],
        history: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        ordered_cases = [self.train_cases_by_id[str(result["case_id"])] for result in best.train_results]
        attribution = attribute_results(
            best.train_results, ordered_cases, threshold=self.policy.failure_threshold
        )
        prompt_paths = best.config["chain"]["config"].get("prompt_paths", {})
        payload: Dict[str, Any] = {
            "allowed_levels": list(allowed),
            "modules": {
                module: _split_header(Path(prompt_paths[module]).read_text(encoding="utf-8"))[1]
                for module in self.modules
            },
            "train_score": best.train.score,
            "failure_count": failure_count,
            "failing_cases": list(failing_cases),
            "attribution": {
                "summary": summarize(attribution),
                "steps": {
                    step: {key: info.get(key) for key in ("count", "heuristic_counts", "confidence_counts")}
                    for step, info in attribution.items()
                },
            },
            "history": [_history_entry(record) for record in history[-HISTORY_LIMIT:]],
            "techniques_tried_since_improvement": {level: techniques[level] for level in allowed},
            "guidance": self.guidance,
            "scorer_source": self.scorer_source,
        }
        if overview is not None:
            payload["training_overview"] = overview
        if "parameter" in self.policy.levels:
            payload["parameter_space"] = {
                spec.path: spec.to_payload() for spec in self.policy.parameter_space
            }
            payload["current_values"] = dict(current_values)
        return payload

    def _failing_results(self, best: CandidateState) -> List[Mapping[str, Any]]:
        return [
            result
            for result in best.train_results
            if result.get("execution_status") != "failed"
            and float(result["composite_score"]) < self.policy.failure_threshold
        ]

    def _training_overview(self, best: CandidateState) -> Optional[List[Dict[str, Any]]]:
        """Every training case in compact form, or None when the split exceeds the policy limit."""
        if len(best.train_results) > self.policy.train_overview_limit:
            return None
        overview = []
        for result in best.train_results:
            case = self.train_cases_by_id[str(result["case_id"])]
            overview.append(
                {
                    "case_id": case.case_id,
                    "context": _clip_value(case.context, OVERVIEW_TEXT_LIMIT),
                    "expected": _clip_value(case.expected, OVERVIEW_TEXT_LIMIT),
                    "metadata": _clip_value(case.metadata, OVERVIEW_TEXT_LIMIT),
                    "passed": result.get("execution_status") != "failed"
                    and float(result["composite_score"]) >= self.policy.failure_threshold,
                }
            )
        return overview

    def _case_view(self, result: Mapping[str, Any]) -> Dict[str, Any]:
        case = self.train_cases_by_id[str(result["case_id"])]
        return {
            "case_id": case.case_id,
            "score": result["composite_score"],
            "score_breakdown": result.get("score_breakdown", {}),
            "context": _clip_value(case.context),
            "expected": _clip_value(case.expected),
            "metadata": _clip_value(case.metadata),
            "output": _clip(str(result.get("output_text", ""))),
            "step_outputs": {
                name: _clip(str(value)) for name, value in (result.get("step_outputs") or {}).items()
            },
            "diagnostics": [_clip(str(item), 500) for item in (result.get("diagnostics") or [])[:5]],
        }

    # -- evaluation -------------------------------------------------------

    def _evaluate(
        self,
        candidate_id: str,
        config: Mapping[str, Any],
        split: str,
        repeats: int = 1,
    ) -> Tuple[SplitScore, List[Mapping[str, Any]]]:
        dataset = {
            "train": self.policy.train_dataset,
            "val": self.policy.val_dataset,
            "test": self.policy.test_dataset,
        }[split]
        total = 0.0
        output_dirs: List[str] = []
        first_results: List[Mapping[str, Any]] = []
        cases = failed = 0
        for repeat in range(1, repeats + 1):
            name = f"{candidate_id}-{split}" + (f"-r{repeat}" if repeats > 1 else "")
            output_dir = _fresh_path(self.workspace / "evals" / name)
            raw = copy.deepcopy(dict(config))
            raw["dataset"] = {"path": dataset}
            raw["output_dir"] = str(output_dir)
            config_path = _fresh_path(self.workspace / "configs" / f"{output_dir.name}.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            results = run_evaluation(load_eval_config(config_path))
            if repeat == 1:
                first_results = results
                cases = len(results)
                failed = sum(1 for result in results if result.get("execution_status") == "failed")
            total += _mean_score(results)
            output_dirs.append(str(output_dir))
        return SplitScore(total / repeats, cases, failed, output_dirs), first_results

    def _evaluate_baseline(self) -> CandidateState:
        config = copy.deepcopy(self.base_config)
        train, train_results = self._evaluate(BASELINE_ID, config, "train")
        val = None
        if self.policy.val_dataset:
            val, _ = self._evaluate(BASELINE_ID, config, "val", repeats=self.policy.acceptance.val_repeats)
        return CandidateState(BASELINE_ID, config, train, val, train_results)

    def _final_test(self, baseline: CandidateState, best: CandidateState) -> Dict[str, Any]:
        test = {"baseline": self._evaluate(BASELINE_ID, baseline.config, "test")[0].to_dict()}
        if best.candidate_id != baseline.candidate_id:
            test["best"] = self._evaluate(best.candidate_id, best.config, "test")[0].to_dict()
        return test

    # -- persistence ------------------------------------------------------

    def _restore(self, record: Mapping[str, Any]) -> CandidateState:
        train = SplitScore.from_dict(record["train"])
        bundle = load_run_bundle(Path(train.output_dirs[0]))
        return CandidateState(
            candidate_id=record["candidate_id"],
            config=copy.deepcopy(record["config"]),
            train=train,
            val=SplitScore.from_dict(record["val"]) if record.get("val") else None,
            train_results=list(bundle.results),
        )

    def _write_best_config(self, best: CandidateState) -> Path:
        raw = copy.deepcopy(best.config)
        raw["dataset"] = {"path": self.policy.val_dataset or self.policy.train_dataset}
        raw["output_dir"] = str(self.workspace / "evals" / f"{best.candidate_id}-rerun")
        path = self.workspace / BEST_CONFIG_FILE
        path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        return path

    def _read_ledger(self) -> List[Dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record, created_at=datetime.now(timezone.utc).isoformat())
        self.workspace.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record


def _baseline_record(baseline: CandidateState) -> Dict[str, Any]:
    return {
        "type": "baseline",
        "candidate_id": baseline.candidate_id,
        "config": baseline.config,
        "train": baseline.train.to_dict(),
        "val": baseline.val.to_dict() if baseline.val else None,
    }


def _last_accepted(records: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    accepted = [record for record in records if record.get("type") == "iteration" and record.get("accepted")]
    return accepted[-1] if accepted else None


def _level_state(
    iterations: Sequence[Mapping[str, Any]],
    levels: Sequence[str],
) -> Tuple[Dict[str, int], Dict[str, List[str]]]:
    """Replay rejections since the last acceptance into per-level plateau counters."""
    misses = {level: 0 for level in levels}
    techniques: Dict[str, List[str]] = {level: [] for level in levels}
    for record in iterations:
        if record.get("accepted"):
            misses = {level: 0 for level in levels}
            techniques = {level: [] for level in levels}
        elif record.get("level") in misses:
            misses[record["level"]] += 1
            techniques[record["level"]].append(record["plan"]["technique"])
    return misses, techniques


def _history_entry(record: Mapping[str, Any]) -> Dict[str, Any]:
    plan = record.get("plan") or {}
    return {
        "iteration": record.get("iteration"),
        "parent_id": record.get("parent_id"),
        "level": record.get("level"),
        "module": plan.get("module"),
        "scope": plan.get("scope"),
        "parameter_changes": plan.get("parameter_changes"),
        "technique": plan.get("technique"),
        "hypothesis": plan.get("hypothesis"),
        "change_summary": record.get("change_summary"),
        "train_delta": record.get("train_delta"),
        "val_delta": record.get("val_delta"),
        "improved_case_ids": record.get("improved_case_ids"),
        "regressed_case_ids": record.get("regressed_case_ids"),
        "accepted": record.get("accepted"),
        "reason": record.get("reason"),
    }


def _case_flips(
    parent_results: Sequence[Mapping[str, Any]],
    candidate_results: Sequence[Mapping[str, Any]],
) -> Dict[str, List[str]]:
    """Training cases whose score went up or down relative to the parent."""
    parent = {str(result["case_id"]): _case_score(result) for result in parent_results}
    improved, regressed = [], []
    for result in candidate_results:
        case_id = str(result["case_id"])
        if case_id not in parent:
            continue
        score = _case_score(result)
        if score > parent[case_id]:
            improved.append(case_id)
        elif score < parent[case_id]:
            regressed.append(case_id)
    return {"improved_case_ids": improved[:FLIP_LIMIT], "regressed_case_ids": regressed[:FLIP_LIMIT]}


def _case_score(result: Mapping[str, Any]) -> float:
    return 0.0 if result.get("execution_status") == "failed" else float(result["composite_score"])


def _candidate_config(raw: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in raw.items() if key not in _PER_EVAL_KEYS}


def _mean_score(results: Sequence[Mapping[str, Any]]) -> float:
    if not results:
        return 0.0
    total = sum(
        float(result["composite_score"]) for result in results if result.get("execution_status") != "failed"
    )
    return total / len(results)


def _split_header(text: str) -> Tuple[str, str]:
    match = _LICENSE_HEADER.match(text)
    if match is None:
        return "", text
    return text[: match.end()].strip() + "\n\n", text[match.end() :].lstrip("\n")


def _write_variant(parent_path: Path, header: str, body: str) -> Path:
    directory = parent_path.parent
    numbers = [
        int(match.group(1)) for path in directory.iterdir() if (match := _VARIANT_FILE.match(path.name))
    ]
    number = max(numbers, default=0) + 1
    while True:
        path = directory / f"variant-{number:03d}.md"
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(header + body.strip() + "\n")
            return path
        except FileExistsError:
            number += 1


def _fresh_path(path: Path) -> Path:
    """Return ``path`` or a numbered sibling, so interrupted runs never collide on resume."""
    candidate, attempt = path, 1
    while candidate.exists():
        attempt += 1
        candidate = path.with_name(f"{path.stem}-a{attempt}{path.suffix}")
    return candidate


def _get_path(config: Mapping[str, Any], dotted: str) -> Any:
    node: Any = config
    for key in dotted.split("."):
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _with_parameters(config: Mapping[str, Any], changes: Mapping[str, Any]) -> Dict[str, Any]:
    updated = copy.deepcopy(dict(config))
    for dotted, value in changes.items():
        *parents, leaf = dotted.split(".")
        node = updated
        for key in parents:
            node = node.setdefault(key, {})
        node[leaf] = value
    return updated


def _clip(text: str, limit: int = TEXT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [{len(text) - limit} chars truncated]"


def _clip_value(value: Any, limit: int = TEXT_LIMIT) -> Any:
    if isinstance(value, str):
        return _clip(value, limit)
    if isinstance(value, Mapping):
        return {str(key): _clip_value(item, limit) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clip_value(item, limit) for item in value[:20]]
    return value
