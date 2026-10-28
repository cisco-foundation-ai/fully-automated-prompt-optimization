# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.hephaestus.optimization.policy import OptimizationPolicy, ParameterSpec
from src.hephaestus.optimization.roles import (
    RoleClient,
    RoleError,
    parse_analysis,
    parse_prompt_proposal,
    parse_review,
)

POLICY = OptimizationPolicy(
    base_config="base.json",
    train_dataset="train.jsonl",
    levels=["prompt", "parameter"],
    parameter_space=[ParameterSpec("provider_settings.temperature", "float", 0.0, 1.0)],
)


def _analysis(plan: Dict[str, Any], **kwargs: Any) -> Any:
    options: Dict[str, Any] = {
        "allowed_levels": ["prompt", "parameter"],
        "modules": ["answer"],
        "current_values": {"provider_settings.temperature": 1.0},
        "policy": POLICY,
    }
    options.update(kwargs)
    return parse_analysis({"clusters": [{"label": "x"}, "junk"], "plan": plan}, **options)


class TestParseAnalysis:
    def test_prompt_plan(self) -> None:
        """A prompt plan keeps its module and drops malformed clusters."""
        analysis = _analysis(
            {"level": "prompt", "module": "answer", "technique": " decomposition ", "hypothesis": "h"}
        )
        assert analysis.clusters == [{"label": "x"}]
        assert analysis.plan.to_dict() == {
            "level": "prompt",
            "module": "answer",
            "scope": "edit",
            "parameter_changes": None,
            "technique": "decomposition",
            "hypothesis": "h",
            "target_case_ids": [],
        }

    def test_rewrite_scope(self) -> None:
        """A prompt plan can ask for a whole-prompt rewrite."""
        plan = {"level": "prompt", "module": "answer", "scope": "rewrite"}
        plan.update(technique="t", hypothesis="h")
        assert _analysis(plan).plan.scope == "rewrite"

    def test_parameter_plan_is_validated_against_space(self) -> None:
        """Parameter plans must stay inside the declared parameter space."""
        plan = {
            "level": "parameter",
            "module": "answer",
            "parameter_changes": {"provider_settings.temperature": 0.2},
            "technique": "lower temperature",
            "hypothesis": "h",
        }
        analysis = _analysis(plan)
        assert analysis.plan.module is None
        assert analysis.plan.parameter_changes == {"provider_settings.temperature": 0.2}

        with pytest.raises(ValueError, match="must be <= 1.0"):
            _analysis(dict(plan, parameter_changes={"provider_settings.temperature": 3}))

    @pytest.mark.parametrize(
        ("plan", "kwargs", "message"),
        [
            ({"level": "parameter"}, {"allowed_levels": ["prompt"]}, "plan.level must be one of"),
            ({"level": "prompt", "module": "other", "technique": "t", "hypothesis": "h"}, {}, "plan.module"),
            ({"level": "prompt", "module": "answer", "hypothesis": "h"}, {}, "plan.technique"),
            ({"level": "parameter", "technique": "t", "hypothesis": "h"}, {}, "parameter_changes must be"),
            (
                {"level": "prompt", "module": "answer", "scope": "redo", "technique": "t", "hypothesis": "h"},
                {},
                "plan.scope must be one of",
            ),
        ],
    )
    def test_rejects_out_of_scope_plans(
        self, plan: Dict[str, Any], kwargs: Dict[str, Any], message: str
    ) -> None:
        """Plans outside the allowed levels or modules are rejected."""
        with pytest.raises(ValueError, match=message):
            _analysis(plan, **kwargs)


class TestParseOutputs:
    def test_prompt_proposal(self) -> None:
        """A proposal needs a non-empty prompt; the summary is optional."""
        assert parse_prompt_proposal({"prompt": "p"}).change_summary == ""
        with pytest.raises(ValueError):
            parse_prompt_proposal({"prompt": " "})

    def test_review_issues_are_prefixed_and_normalized(self) -> None:
        """Reviewer issues are namespaced, and unknown severities become warnings."""
        issues = parse_review(
            {"verdict": "warn", "issues": [{"check": "focus", "severity": "minor", "description": "d"}]}
        )
        assert [(issue.check, issue.severity) for issue in issues] == [("llm_focus", "warn")]

    def test_fail_verdict_always_blocks(self) -> None:
        """A 'fail' verdict blocks even when the reviewer forgot to mark an issue as blocking."""
        issues = parse_review({"verdict": "fail", "issues": []})
        assert [issue.severity for issue in issues] == ["block"]
        with pytest.raises(ValueError, match="verdict"):
            parse_review({"verdict": "maybe"})


class _Generator:
    def __init__(self, responses: List[Any]) -> None:
        self.responses = list(responses)
        self.payloads: List[Dict[str, Any]] = []
        self._metadata: List[Dict[str, Any]] = []

    def generate_json(self, system_prompt: str, payload: Dict[str, Any]) -> Any:
        self.payloads.append(dict(payload))
        self._metadata.append({"usage": {"input_tokens": 10, "output_tokens": 5}})
        return self.responses.pop(0)

    def drain_call_metadata(self) -> List[Dict[str, Any]]:
        rows, self._metadata = self._metadata, []
        return rows


class TestRoleClient:
    def test_retries_with_errors_then_succeeds(self) -> None:
        """An invalid response is retried once with the validation error attached."""
        generator = _Generator([{"prompt": ""}, {"prompt": "ok"}])
        client = RoleClient(generator)

        proposal = client.call("prompt_proposer", "system", {"module": "answer"}, parse_prompt_proposal)

        assert proposal.prompt == "ok"
        assert generator.payloads[0] == {"module": "answer", "role": "prompt_proposer"}
        assert generator.payloads[1]["previous_errors"] == ["prompt must be a non-empty string"]
        usage = client.take_usage()
        assert usage == {"prompt_proposer": {"calls": 2, "input_tokens": 20, "output_tokens": 10}}
        assert client.take_usage() == {}

    def test_raises_role_error_after_last_attempt(self) -> None:
        """Persistently invalid output raises RoleError."""
        client = RoleClient(_Generator([["not", "an", "object"], {"prompt": ""}]))

        with pytest.raises(RoleError, match="prompt_proposer returned invalid output"):
            client.call("prompt_proposer", "system", {}, parse_prompt_proposal)
