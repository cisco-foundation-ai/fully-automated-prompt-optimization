# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Deterministic guardrail checks for proposed prompt and parameter variants.

These are the mechanical subset of the variant-reviewer checklist. They run
on every candidate before any eval, so they are runtime-enforced rather than
agent-enforced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from src.hephaestus.optimization.policy import OptimizationPolicy
from src.hephaestus.types import EvalCase

PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}]*)\}")
SECTION_PATTERN = re.compile(r"(?m)^[ \t]*(System|User):")
_WORD_PATTERN = re.compile(r"\w+")
LEAKAGE_NGRAM = 8
# N-grams shared by more cases than this are boilerplate, not case-specific text.
LEAKAGE_MAX_CASES_PER_NGRAM = 2
MIN_CASE_ID_LENGTH = 4
# Inputs shorter than an n-gram (for example a product or entity name) are
# matched whole, case-sensitively, so ordinary lowercase words do not collide.
MIN_SHORT_INPUT_LENGTH = 4


@dataclass
class ReviewIssue:
    """One finding from a variant review."""

    check: str
    severity: str  # "block" | "warn"
    description: str

    def to_dict(self) -> Dict[str, str]:
        return {"check": self.check, "severity": self.severity, "description": self.description}


def has_blocking(issues: Iterable[ReviewIssue]) -> bool:
    """Return True when any issue blocks evaluation."""
    return any(issue.severity == "block" for issue in issues)


def placeholders(text: str) -> Set[str]:
    """Return the set of ``${placeholder}`` names in ``text``."""
    return set(PLACEHOLDER_PATTERN.findall(text))


def review_prompt_variant(
    previous: str,
    proposed: str,
    train_cases: Sequence[EvalCase],
    heldout_cases: Sequence[EvalCase] = (),
) -> List[ReviewIssue]:
    """Check a proposed prompt body against its parent and the dataset splits.

    Args:
        previous: Parent prompt body (license header removed).
        proposed: Proposed prompt body.
        train_cases: Training cases, used to detect copied case content.
        heldout_cases: Val and test cases. A strong model can name held-out
            inputs from its own knowledge (for example the best-known product of
            a kind), which inflates held-out scores. Matches block the variant
            with a message that does not reveal the held-out input.

    Returns:
        Review issues; empty when the variant passes.
    """
    if not proposed.strip():
        return [ReviewIssue("non_empty", "block", "proposed prompt is empty")]
    if proposed.strip() == previous.strip():
        return [ReviewIssue("no_change", "block", "proposed prompt is identical to the current prompt")]

    issues: List[ReviewIssue] = []
    added = sorted(placeholders(proposed) - placeholders(previous))
    removed = sorted(placeholders(previous) - placeholders(proposed))
    if added or removed:
        issues.append(
            ReviewIssue(
                "placeholder_integrity",
                "block",
                f"placeholders must not change (added: {added}, removed: {removed})",
            )
        )

    missing_sections = sorted(set(SECTION_PATTERN.findall(previous)) - set(SECTION_PATTERN.findall(proposed)))
    if missing_sections:
        issues.append(
            ReviewIssue(
                "section_structure",
                "block",
                f"proposed prompt drops section markers the renderer relies on: {missing_sections}",
            )
        )

    for case in train_cases:
        if len(case.case_id) < MIN_CASE_ID_LENGTH:
            continue
        pattern = re.compile(rf"(?<![\w-]){re.escape(case.case_id)}(?![\w-])")
        if pattern.search(proposed) and not pattern.search(previous):
            issues.append(
                ReviewIssue("case_id_reference", "block", f"prompt references case ID {case.case_id!r}")
            )

    copied_inputs = _copied_short_inputs(previous, proposed, train_cases)
    if copied_inputs:
        issues.append(
            ReviewIssue(
                "train_input_copy",
                "block",
                f"prompt names training inputs {copied_inputs[:5]}; describe the kind of input instead",
            )
        )

    copied = _copied_case_text(previous, proposed, train_cases)
    if copied:
        issues.append(
            ReviewIssue(
                "train_example_leakage",
                "block",
                f"prompt copies training-case text: {' | '.join(copied[:3])!r}",
            )
        )

    if heldout_cases and (
        _copied_short_inputs(previous, proposed, heldout_cases)
        or _copied_case_text(previous, proposed, heldout_cases)
    ):
        issues.append(
            ReviewIssue(
                "specific_input_reference",
                "block",
                "prompt names specific inputs (such as product or entity names) or quotes input text; "
                "remove named examples and describe the kind of input instead",
            )
        )
    return issues


def review_parameter_changes(
    changes: Mapping[str, Any],
    current: Mapping[str, Any],
    policy: OptimizationPolicy,
) -> List[ReviewIssue]:
    """Check proposed parameter changes against the policy's parameter space.

    Args:
        changes: Proposed ``{dotted_path: value}`` changes.
        current: Current ``{dotted_path: value}`` values for the same paths.
        policy: Active policy.

    Returns:
        Review issues; empty when the changes pass.
    """
    if not changes:
        return [ReviewIssue("non_empty", "block", "no parameter changes proposed")]
    issues: List[ReviewIssue] = []
    for path, value in changes.items():
        spec = policy.parameter(path)
        if spec is None:
            issues.append(ReviewIssue("parameter_scope", "block", f"{path} is not in the parameter space"))
            continue
        error = spec.validate(value)
        if error:
            issues.append(ReviewIssue("parameter_bounds", "block", error))
    if not issues and all(current.get(path) == value for path, value in changes.items()):
        issues.append(ReviewIssue("no_change", "block", "proposed values equal the current values"))
    return issues


def _copied_case_text(
    previous: str,
    proposed: str,
    train_cases: Sequence[EvalCase],
) -> List[str]:
    new_ngrams = _ngrams(proposed) - _ngrams(previous)
    if not new_ngrams:
        return []
    owners: Dict[Tuple[str, ...], int] = {}
    for case in train_cases:
        case_text = " ".join(_strings(case.context) + _strings(case.expected))
        for ngram in _ngrams(case_text) & new_ngrams:
            owners[ngram] = owners.get(ngram, 0) + 1
    return [
        " ".join(ngram)
        for ngram, count in sorted(owners.items())
        if count <= LEAKAGE_MAX_CASES_PER_NGRAM
    ]


def _copied_short_inputs(
    previous: str,
    proposed: str,
    train_cases: Sequence[EvalCase],
) -> List[str]:
    copied = set()
    for case in train_cases:
        for value in _strings(case.context):
            value = value.strip()
            if len(value) < MIN_SHORT_INPUT_LENGTH or len(_WORD_PATTERN.findall(value)) >= LEAKAGE_NGRAM:
                continue
            pattern = re.compile(rf"(?<![\w-]){re.escape(value)}(?![\w-])")
            if pattern.search(proposed) and not pattern.search(previous):
                copied.add(value)
    return sorted(copied)


def _ngrams(text: str) -> Set[Tuple[str, ...]]:
    words = [word.lower() for word in _WORD_PATTERN.findall(text)]
    return {tuple(words[i : i + LEAKAGE_NGRAM]) for i in range(len(words) - LEAKAGE_NGRAM + 1)}


def _strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [text for item in value.values() for text in _strings(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _strings(item)]
    return []
