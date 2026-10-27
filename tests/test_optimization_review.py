# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Dict, List

from src.hephaestus.optimization.policy import OptimizationPolicy, ParameterSpec
from src.hephaestus.optimization.review import (
    has_blocking,
    review_parameter_changes,
    review_prompt_variant,
)
from src.hephaestus.types import EvalCase

PREVIOUS = """\
System: Answer the question.

User: ${question}"""


def _case(case_id: str, question: str, answer: str = "yes") -> EvalCase:
    return EvalCase(
        case_id=case_id,
        task_type="qa",
        context={"question": question},
        expected={"answer": answer},
        metadata={},
    )


CASES = [
    _case("case-0001", "Which river flows through the ancient walled city of Carcassonne in France?"),
    _case("case-0002", "Is the tallest mountain on the island of Honshu an active volcano today?"),
]


def _checks(proposed: str, cases: List[EvalCase] = CASES) -> List[str]:
    return [issue.check for issue in review_prompt_variant(PREVIOUS, proposed, cases)]


class TestReviewPromptVariant:
    def test_general_change_passes(self) -> None:
        """A general instruction change with the same placeholders and sections passes."""
        proposed = PREVIOUS.replace("Answer the question.", "Answer the question with one word.")
        assert _checks(proposed) == []

    def test_empty_and_unchanged_are_blocked(self) -> None:
        """Empty or identical proposals are blocked."""
        assert _checks("  ") == ["non_empty"]
        assert _checks(PREVIOUS + "\n") == ["no_change"]

    def test_placeholder_changes_are_blocked(self) -> None:
        """Added, removed, or renamed placeholders are blocked."""
        renamed = PREVIOUS.replace("${question}", "${query}")
        issues = review_prompt_variant(PREVIOUS, renamed, CASES)
        assert [issue.check for issue in issues] == ["placeholder_integrity"]
        assert "added: ['query'], removed: ['question']" in issues[0].description

    def test_dropped_section_marker_is_blocked(self) -> None:
        """Dropping a System:/User: marker the renderer relies on is blocked."""
        assert _checks("Answer the question.\n\nUser: ${question}") == ["section_structure"]

    def test_case_id_reference_is_blocked(self) -> None:
        """Newly referencing a training case ID is blocked, including hyphenated IDs."""
        assert _checks(PREVIOUS + "\nRemember case-0002.") == ["case_id_reference"]
        assert _checks(PREVIOUS + "\nRemember case-00021.") == []

    def test_copied_training_text_is_blocked(self) -> None:
        """Copying an 8-word span from a training case is blocked as leakage."""
        proposed = PREVIOUS + "\nExample: flows through the ancient walled city of Carcassonne -> Aude"
        assert _checks(proposed) == ["train_example_leakage"]

    def test_copied_short_training_input_is_blocked(self) -> None:
        """Naming a short training input (such as a product name) is blocked, case-sensitively."""
        cases = [_case("case-0003", "Quillforge", answer="writing_tool"), _case("case-0004", "Lantern")]
        named = PREVIOUS + "\nFor example, Quillforge is a writing tool."
        assert _checks(named, cases) == ["train_input_copy"]
        assert _checks(PREVIOUS + "\nA lantern-like hint is not a writing_tool.", cases) == []

    def test_heldout_input_is_blocked_without_revealing_it(self) -> None:
        """Naming a val/test input blocks the variant with a message that does not name it."""
        heldout = [_case("case-0009", "Copper Kettle")]
        proposed = PREVIOUS + "\nFor example, Copper Kettle brews tea."
        issues = review_prompt_variant(PREVIOUS, proposed, CASES, heldout)
        assert [issue.check for issue in issues] == ["specific_input_reference"]
        assert "Copper Kettle" not in issues[0].description
        assert review_prompt_variant(PREVIOUS, PREVIOUS + "\nBe concise.", CASES, heldout) == []

    def test_text_shared_by_many_cases_is_not_leakage(self) -> None:
        """Boilerplate present in many training cases is not treated as case-specific."""
        boilerplate = "Read the passage below carefully and then answer the question"
        cases = [_case(f"case-{index:04d}", f"{boilerplate} number {index}") for index in range(3)]
        proposed = PREVIOUS + f"\n{boilerplate}."
        assert _checks(proposed, cases) == []

    def test_text_already_in_previous_prompt_is_not_leakage(self) -> None:
        """Spans the parent prompt already contained are not new leakage."""
        previous = PREVIOUS + "\nflows through the ancient walled city of Carcassonne in France"
        proposed = previous + "\nBe concise."
        assert review_prompt_variant(previous, proposed, CASES) == []


class TestReviewParameterChanges:
    POLICY = OptimizationPolicy(
        base_config="base.json",
        train_dataset="train.jsonl",
        levels=["parameter"],
        parameter_space=[ParameterSpec("chain.config.retrieval_k", "int", 3, 20)],
    )

    def _checks(self, changes: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
        issues = review_parameter_changes(changes, current, self.POLICY)
        assert has_blocking(issues) == bool(issues)
        return [issue.check for issue in issues]

    def test_in_space_change_passes(self) -> None:
        """A change inside the declared bounds passes."""
        assert self._checks({"chain.config.retrieval_k": 10}, {"chain.config.retrieval_k": 7}) == []

    def test_out_of_scope_bounds_and_no_ops_are_blocked(self) -> None:
        """Unknown paths, out-of-bounds values, empty, and no-op changes are blocked."""
        assert self._checks({"provider_settings.model": "x"}, {}) == ["parameter_scope"]
        assert self._checks({"chain.config.retrieval_k": 50}, {}) == ["parameter_bounds"]
        assert self._checks({}, {}) == ["non_empty"]
        assert self._checks({"chain.config.retrieval_k": 7}, {"chain.config.retrieval_k": 7}) == ["no_change"]
