# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Headless optimization coordinator for prompt and parameter levels.

Each iteration picks a parent from a pool of accepted candidates, asks the
analyst for several distinct plans, screens every resulting candidate (and an
optional merge of two pool members) on train, and evaluates the best one on
val. A paired test against its parent decides whether it joins the pool. When
the loop stops, the top pool members are re-evaluated and the best fresh score
wins. The coordinator is plain code and owns the invariants:

- role payloads only contain per-case data from the training split;
- val and test reach roles as aggregate scores only; per-case val scores are
  used in code for the paired test and never leave it;
- test runs at most once per workspace, after optimization has stopped;
- every variant is a new file, branched from a pool member;
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
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

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
from src.hephaestus.optimization.stats import paired_improvement
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
    parent_id: Optional[str] = None
    # Per-case val scores, averaged over repeats; used in code only.
    val_case_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def selection_score(self) -> float:
        return self.val.score if self.val is not None else self.train.score

    @property
    def train_case_scores(self) -> Dict[str, float]:
        return _case_scores(self.train_results)


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
        if any(record.get("test") or record.get("type") == "test_started" for record in records):
            raise ValueError("the test split was already evaluated in this workspace; start a new workspace")

        if records:
            if records[0].get("type") != "baseline":
                raise ValueError(f"{self.ledger_path} does not start with a baseline record")
            baseline = self._restore(records[0])
            if (baseline.val is None) != (self.policy.val_dataset is None):
                raise ValueError("the policy's val split does not match the ledger being resumed")
            pool = [baseline] + [
                self._restore(record)
                for record in records
                if record.get("type") == "iteration" and record.get("accepted")
            ]
        else:
            baseline = self._evaluate_baseline()
            pool = [baseline]
            records.append(self._append(_baseline_record(baseline)))
        iterations = [record for record in records if record["type"] == "iteration"]
        iteration = max((record["iteration"] for record in iterations), default=0)
        misses, techniques = _level_state(iterations, self.policy.levels)
        tried_merges = {
            "+".join(sorted(entry["merge_of"])) for entry in _entries(iterations) if entry.get("merge_of")
        }

        stop_reason = "max_iterations"
        while iteration < self.policy.budget.max_iterations:
            best = _best(pool)
            target = self.policy.budget.target_score
            if target is not None and best.selection_score >= target:
                stop_reason = "target_reached"
                break
            patience = self.policy.budget.plateau_patience
            allowed = [level for level in self.policy.levels if misses[level] < patience]
            if not allowed:
                stop_reason = "levels_exhausted"
                break
            parent = self._select_parent(pool, iteration + 1)
            failing = self._failing_results(parent)
            if not failing and parent is not best:
                parent, failing = best, self._failing_results(best)
            if not failing:
                stop_reason = "no_train_failures"
                break
            iteration += 1
            record, candidate = self._iterate(
                iteration, parent, pool, allowed, failing, techniques, iterations, tried_merges
            )
            iterations.append(self._append(record))
            logger.info(
                "iteration %d: %s %s (train %+.2f, val %s, p %s)",
                iteration,
                record.get("level"),
                record["reason"],
                record.get("train_delta") or 0.0,
                "n/a" if record.get("val_delta") is None else f"{record['val_delta']:+.2f}",
                record.get("p_improve", "n/a"),
            )
            if candidate is not None:
                pool.append(candidate)
                misses, techniques = _level_state([], self.policy.levels)
            else:
                _count_misses(record, misses, techniques)

        best = self._final_selection(pool, records)
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
        parent: CandidateState,
        pool: Sequence[CandidateState],
        allowed: Sequence[str],
        failing: Sequence[Mapping[str, Any]],
        techniques: Mapping[str, List[str]],
        history: Sequence[Mapping[str, Any]],
        tried_merges: Set[str],
    ) -> Tuple[Dict[str, Any], Optional[CandidateState]]:
        record: Dict[str, Any] = {
            "type": "iteration",
            "iteration": iteration,
            "candidate_id": None,
            "parent_id": parent.candidate_id,
            "level": None,
            "accepted": False,
        }
        rng = random.Random(f"c{iteration:03d}")
        shown = sorted(
            rng.sample(list(failing), min(len(failing), self.policy.max_failures_shown)),
            key=lambda result: float(result["composite_score"]),
        )
        failing_cases = [self._case_view(result) for result in shown]
        overview = self._training_overview(parent)
        current_values = {
            spec.path: _get_path(parent.config, spec.path) for spec in self.policy.parameter_space
        }
        payload = self._analyst_payload(
            parent, allowed, len(failing), failing_cases, overview, current_values, techniques, history
        )
        evaluated = [self.base_config] + [entry["config"] for entry in _entries(history) if "config" in entry]

        def parse(raw: Dict[str, Any]) -> Analysis:
            analysis = parse_analysis(
                raw,
                allowed_levels=allowed,
                modules=self.modules,
                current_values=current_values,
                policy=self.policy,
                max_plans=self.policy.search.candidates,
            )
            fresh = [
                plan
                for plan in analysis.plans
                if not plan.parameter_changes
                or _with_parameters(parent.config, plan.parameter_changes) not in evaluated
            ]
            if not fresh:
                raise ValueError("these parameter values were already evaluated in this run; choose others")
            analysis.plans = fresh
            return analysis

        try:
            analysis = self.roles.call("analyst", ANALYST_SYSTEM_PROMPT, payload, parse)
        except RoleError as exc:
            record.update(reason="role_error", error=str(exc), usage=self.roles.take_usage())
            return record, None
        record["clusters"] = analysis.clusters

        entries: List[Dict[str, Any]] = []
        for index, plan in enumerate(analysis.plans):
            entry: Dict[str, Any] = {
                "iteration": iteration,
                "candidate_id": _candidate_id(iteration, index, self.policy.search.candidates),
                "parent": parent,
                "level": plan.level,
                "plan": plan.to_dict(),
            }
            entries.append(entry)
            try:
                if plan.level == "prompt":
                    config, details = self._prompt_candidate(
                        parent, plan, analysis.clusters, failing_cases, overview
                    )
                else:
                    config = _with_parameters(parent.config, plan.parameter_changes)
                    details = {"parameter_changes": plan.parameter_changes}
            except RoleError as exc:
                entry.update(reason="role_error", error=str(exc))
                continue
            entry.update(details)
            if config is None:
                entry["reason"] = "review_failed"
            else:
                entry["config"] = config
        if self.policy.search.merge:
            merge = self._merge_entry(iteration, pool, tried_merges, evaluated)
            if merge is not None:
                entries.append(merge)
        record["usage"] = self.roles.take_usage()

        seen = list(evaluated)
        screened: List[Dict[str, Any]] = []
        for entry in entries:
            if "config" not in entry:
                continue
            if entry["config"] in seen:
                entry["reason"] = "duplicate_config"
                continue
            seen.append(entry["config"])
            if self._screen(entry):
                screened.append(entry)
        # Every candidate ran on the same train cases, so absolute scores compare fairly
        # even when candidates branch from different references (a merge and a plan).
        candidate: Optional[CandidateState] = None
        if screened:
            chosen = max(screened, key=_train_score)
            candidate = self._select(chosen)
            for entry in screened:
                if entry is not chosen:
                    entry["reason"] = "not_selected"
        else:
            trained = [entry for entry in entries if "train" in entry]
            chosen = max(trained, key=_train_score) if trained else entries[0]
        record.update(_entry_record(chosen))
        record["alternatives"] = [_entry_record(entry) for entry in entries if entry is not chosen]
        return record, candidate

    def _screen(self, entry: Dict[str, Any]) -> bool:
        """Evaluate one candidate on train; return whether it passes the train screen."""
        reference: CandidateState = entry["parent"]
        train, results, _ = self._evaluate(entry["candidate_id"], entry["config"], "train")
        entry["train"] = train.to_dict()
        entry["train_delta"] = train.score - reference.train.score
        entry["train_results"] = results
        entry.update(_case_flips(reference.train_results, results))
        if entry["train_delta"] < self.policy.acceptance.min_train_delta:
            entry["reason"] = "train_screen"
            return False
        return True

    def _select(self, entry: Dict[str, Any]) -> Optional[CandidateState]:
        """Evaluate the chosen candidate on val and apply the paired acceptance test."""
        reference: CandidateState = entry["parent"]
        acceptance = self.policy.acceptance
        candidate_id = entry["candidate_id"]
        train = SplitScore.from_dict(entry["train"])
        train_results = entry["train_results"]
        _, train_p = paired_improvement(
            _case_scores(train_results), reference.train_case_scores, seed=f"{candidate_id}-train"
        )
        val: Optional[SplitScore] = None
        val_case_scores: Dict[str, float] = {}
        if self.policy.val_dataset:
            val, _, val_case_scores = self._evaluate(
                candidate_id, entry["config"], "val", repeats=acceptance.val_repeats
            )
            entry["val"] = val.to_dict()
            entry["val_delta"] = selection_delta = val.score - reference.val.score
            _, p_improve = paired_improvement(
                val_case_scores, reference.val_case_scores, seed=f"{candidate_id}-val"
            )
        else:
            selection_delta, p_improve = entry["train_delta"], train_p
        entry["p_improve"] = round(p_improve, 4)
        if (
            selection_delta > 0
            and selection_delta >= acceptance.min_val_delta
            and p_improve >= acceptance.confidence
        ):
            reason = "accepted"
        elif (
            acceptance.train_tiebreak
            and val is not None
            and selection_delta >= 0
            and entry["train_delta"] > 0
            and train_p >= acceptance.confidence
        ):
            reason = "accepted_train_tiebreak"
        else:
            reason = "selection_below_threshold"
        entry.update(accepted=reason != "selection_below_threshold", reason=reason)
        if not entry["accepted"]:
            return None
        return CandidateState(
            candidate_id,
            entry["config"],
            train,
            val,
            train_results,
            parent_id=reference.candidate_id,
            val_case_scores=val_case_scores,
        )

    # -- pool -------------------------------------------------------------

    def _select_parent(self, pool: Sequence[CandidateState], iteration: int) -> CandidateState:
        """Sample a parent by the train cases each pool member does best on.

        Members dominated by another member (no better on any case, worse on
        one) are dropped. Each remaining member gets one vote for every case
        where it reaches the top score and the pool does not all tie. With
        "best" selection, or when no member stands out, the current best is
        the parent.
        """
        best = _best(pool)
        if self.policy.search.parent_selection == "best" or len(pool) < 2:
            return best
        case_ids = sorted(pool[0].train_case_scores)
        scores = [[member.train_case_scores.get(case_id, 0.0) for case_id in case_ids] for member in pool]
        frontier = [
            index
            for index, own in enumerate(scores)
            if not any(
                all(o >= m for o, m in zip(other, own)) and any(o > m for o, m in zip(other, own))
                for other in scores
            )
        ]
        votes = {index: 0 for index in frontier}
        for position in range(len(case_ids)):
            values = [scores[index][position] for index in range(len(pool))]
            top = max(values)
            if top == min(values):
                continue
            for index in frontier:
                if scores[index][position] == top:
                    votes[index] += 1
        if not any(votes.values()):
            return best
        rng = random.Random(f"parent-{iteration}")
        members = list(votes)
        return pool[rng.choices(members, weights=[votes[index] for index in members], k=1)[0]]

    def _merge_entry(
        self,
        iteration: int,
        pool: Sequence[CandidateState],
        tried: Set[str],
        evaluated: Sequence[Mapping[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Combine two pool members that changed different settings since their common ancestor."""
        by_id = {member.candidate_id: member for member in pool}

        def lineage(member: CandidateState) -> List[str]:
            ids: List[str] = []
            current: Optional[CandidateState] = member
            while current is not None:
                ids.append(current.candidate_id)
                current = by_id.get(current.parent_id) if current.parent_id else None
            return ids

        best_pair: Optional[Tuple[float, str, CandidateState, CandidateState, Dict[str, Any]]] = None
        for first, second in combinations(pool, 2):
            first_line, second_line = lineage(first), lineage(second)
            if first.candidate_id in second_line or second.candidate_id in first_line:
                continue
            common_id = next((cid for cid in first_line if cid in second_line), None)
            if common_id is None:
                continue
            common = by_id[common_id]
            first_changes = self._changes(common.config, first.config)
            second_changes = self._changes(common.config, second.config)
            if not first_changes or not second_changes or set(first_changes) & set(second_changes):
                continue
            key = "+".join(sorted((first.candidate_id, second.candidate_id)))
            merged = _with_parameters(common.config, {**first_changes, **second_changes})
            if key in tried or merged in evaluated:
                continue
            score = first.selection_score + second.selection_score
            if best_pair is None or score > best_pair[0]:
                best_pair = (score, key, first, second, merged)
        if best_pair is None:
            return None
        _, key, first, second, merged = best_pair
        tried.add(key)
        reference = max((first, second), key=lambda member: member.selection_score)
        sources = [first.candidate_id, second.candidate_id]
        return {
            "iteration": iteration,
            "candidate_id": f"c{iteration:03d}m",
            "parent": reference,
            "level": "merge",
            "plan": {
                "level": "merge",
                "module": None,
                "scope": "merge",
                "technique": "merge",
                "hypothesis": f"Combining {sources[0]} and {sources[1]} keeps both of their separate gains.",
                "target_case_ids": [],
            },
            "merge_of": sources,
            "config": merged,
        }

    def _changes(self, base: Mapping[str, Any], other: Mapping[str, Any]) -> Dict[str, Any]:
        """Dotted paths of the prompt modules and parameters in ``other`` that differ from ``base``."""
        paths = [f"chain.config.prompt_paths.{module}" for module in self.modules]
        paths += [spec.path for spec in self.policy.parameter_space]
        return {
            path: _get_path(other, path) for path in paths if _get_path(other, path) != _get_path(base, path)
        }

    def _final_selection(
        self,
        pool: Sequence[CandidateState],
        records: Sequence[Mapping[str, Any]],
    ) -> CandidateState:
        """Re-evaluate the top pool members and return the best fresh score.

        A single high score is biased upward, so finalists are compared on new
        runs only. On resume, an earlier selection is reused only when its
        finalists are still the top pool members.
        """
        by_id = {member.candidate_id: member for member in pool}
        finalists = sorted(pool, key=_rank, reverse=True)
        finalists = finalists[: self.policy.selection.finalists]
        if len(finalists) < 2:
            return finalists[0]
        previous = next(
            (record for record in reversed(records) if record.get("type") == "final_selection"), None
        )
        finalist_ids = [member.candidate_id for member in finalists]
        if previous is not None and [row["candidate_id"] for row in previous["finalists"]] == finalist_ids:
            return by_id[previous["chosen_id"]]
        split = "val" if self.policy.val_dataset else "train"
        rows: List[Dict[str, Any]] = []
        for member in finalists:
            fresh, _, _ = self._evaluate(
                f"{member.candidate_id}-final", member.config, split, repeats=self.policy.selection.repeats
            )
            rows.append(
                {
                    "candidate_id": member.candidate_id,
                    "selection_score": member.selection_score,
                    "reevaluation": fresh.to_dict(),
                }
            )
        chosen = max(
            zip(finalists, rows),
            key=lambda pair: (pair[1]["reevaluation"]["score"], *_rank(pair[0])),
        )[0]
        self._append(
            {"type": "final_selection", "split": split, "finalists": rows, "chosen_id": chosen.candidate_id}
        )
        return chosen

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
            "max_plans": self.policy.search.candidates,
            "history": [_history_entry(entry) for entry in _entries(history)][-HISTORY_LIMIT:],
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
    ) -> Tuple[SplitScore, List[Mapping[str, Any]], Dict[str, float]]:
        """Evaluate ``config`` on ``split``.

        Returns:
            The aggregate score, the first repeat's results, and per-case scores
            averaged over repeats.
        """
        dataset = {
            "train": self.policy.train_dataset,
            "val": self.policy.val_dataset,
            "test": self.policy.test_dataset,
        }[split]
        total = 0.0
        output_dirs: List[str] = []
        first_results: List[Mapping[str, Any]] = []
        case_totals: Dict[str, float] = {}
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
            for case_id, score in _case_scores(results).items():
                case_totals[case_id] = case_totals.get(case_id, 0.0) + score
        case_scores = {case_id: value / repeats for case_id, value in case_totals.items()}
        return SplitScore(total / repeats, cases, failed, output_dirs), first_results, case_scores

    def _evaluate_baseline(self) -> CandidateState:
        config = copy.deepcopy(self.base_config)
        train, train_results, _ = self._evaluate(BASELINE_ID, config, "train")
        val = None
        val_case_scores: Dict[str, float] = {}
        if self.policy.val_dataset:
            val, _, val_case_scores = self._evaluate(
                BASELINE_ID, config, "val", repeats=self.policy.acceptance.val_repeats
            )
        return CandidateState(BASELINE_ID, config, train, val, train_results, val_case_scores=val_case_scores)

    def _final_test(self, baseline: CandidateState, best: CandidateState) -> Dict[str, Any]:
        # Written first, so an interrupted test run can never be resumed into a second one.
        self._append({"type": "test_started", "best_candidate_id": best.candidate_id})
        test = {"baseline": self._evaluate(BASELINE_ID, baseline.config, "test")[0].to_dict()}
        if best.candidate_id != baseline.candidate_id:
            test["best"] = self._evaluate(best.candidate_id, best.config, "test")[0].to_dict()
        return test

    # -- persistence ------------------------------------------------------

    def _restore(self, record: Mapping[str, Any]) -> CandidateState:
        """Rebuild a pool member from its ledger record and saved run bundles."""
        train = SplitScore.from_dict(record["train"])
        bundle = load_run_bundle(Path(train.output_dirs[0]))
        val = SplitScore.from_dict(record["val"]) if record.get("val") else None
        val_case_scores: Dict[str, float] = {}
        if val is not None:
            for output_dir in val.output_dirs:
                for case_id, score in _case_scores(load_run_bundle(Path(output_dir)).results).items():
                    val_case_scores[case_id] = val_case_scores.get(case_id, 0.0) + score
            val_case_scores = {key: value / len(val.output_dirs) for key, value in val_case_scores.items()}
        return CandidateState(
            candidate_id=record["candidate_id"],
            config=copy.deepcopy(record["config"]),
            train=train,
            val=val,
            train_results=list(bundle.results),
            parent_id=record.get("parent_id"),
            val_case_scores=val_case_scores,
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


def _best(pool: Sequence[CandidateState]) -> CandidateState:
    """The pool member with the highest selection score, then train score; the earliest wins ties."""
    return max(pool, key=_rank)


def _rank(member: CandidateState) -> Tuple[float, float]:
    return (member.selection_score, member.train.score)


def _train_score(entry: Mapping[str, Any]) -> float:
    return float(entry["train"]["score"])


def _candidate_id(iteration: int, index: int, per_iteration: int) -> str:
    suffix = chr(ord("a") + index) if per_iteration > 1 else ""
    return f"c{iteration:03d}{suffix}"


def _entries(records: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """Every candidate an iteration tried: the selected one, then its alternatives."""
    entries: List[Mapping[str, Any]] = []
    for record in records:
        if record.get("candidate_id") is not None or record.get("reason") == "role_error":
            entries.append(record)
        entries.extend(record.get("alternatives") or [])
    return entries


def _entry_record(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """Ledger fields for one candidate, without in-memory state."""
    record = {key: value for key, value in entry.items() if key not in ("parent", "train_results")}
    record["parent_id"] = entry["parent"].candidate_id
    record.setdefault("accepted", False)
    return record


def _count_misses(
    record: Mapping[str, Any],
    misses: Dict[str, int],
    techniques: Dict[str, List[str]],
) -> None:
    """Add one rejection to every level an iteration tried, and record its techniques."""
    tried = [record, *(record.get("alternatives") or [])]
    for level in {entry.get("level") for entry in tried if entry.get("level") in misses}:
        misses[level] += 1
    for entry in tried:
        if entry.get("level") in techniques and entry.get("plan"):
            techniques[entry["level"]].append(entry["plan"]["technique"])


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
        else:
            _count_misses(record, misses, techniques)
    return misses, techniques


def _history_entry(record: Mapping[str, Any]) -> Dict[str, Any]:
    plan = record.get("plan") or {}
    return {
        "iteration": record.get("iteration"),
        "candidate_id": record.get("candidate_id"),
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
        "p_improve": record.get("p_improve"),
        "merge_of": record.get("merge_of"),
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


def _case_scores(results: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    return {str(result["case_id"]): _case_score(result) for result in results}


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
