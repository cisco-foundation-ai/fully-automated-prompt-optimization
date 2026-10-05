# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Execute one Tau Retail episode with a file-backed agent instruction prompt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tau2.agent import llm_agent
from tau2.data_model.simulation import TextRunConfig
from tau2.runner.build import build_text_orchestrator
from tau2.runner.helpers import get_tasks

AGENT_MODEL = "gpt-4.1-2025-04-14"
USER_MODEL = "gpt-4.1-2025-04-14"
_PROMPT_LICENSE_HEADER = (
    "# Copyright 2026 Cisco Systems, Inc. and its affiliates\n"
    "#\n"
    "# SPDX-License-Identifier: Apache-2.0\n\n"
)


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_prompt(path: Path) -> tuple[str, str]:
    """Return the executable prompt and its license-header-stripped body."""
    body = path.read_text(encoding="utf-8")
    if body.startswith(_PROMPT_LICENSE_HEADER):
        body = body.removeprefix(_PROMPT_LICENSE_HEADER)
    prompt = body.strip()
    if not prompt:
        raise ValueError("The Tau agent prompt must not be empty")
    return prompt, body


def _message_payload(message: Any) -> dict[str, Any]:
    """Serialize a Tau message without exposing hidden task specifications."""
    return message.model_dump(mode="json", exclude_none=True)


def run(task_id: str, seed: int, prompt_path: Path) -> dict[str, Any]:
    """Run and sanitize one pinned Tau episode."""
    prompt_text, prompt_body = _read_prompt(prompt_path)

    llm_agent.AGENT_INSTRUCTION = prompt_text
    config = TextRunConfig(
        domain="retail",
        task_set_name="retail",
        task_split_name="base",
        task_ids=[task_id],
        num_trials=1,
        seed=seed,
        agent="llm_agent",
        llm_agent=AGENT_MODEL,
        llm_args_agent={"temperature": 0.0},
        user="user_simulator",
        llm_user=USER_MODEL,
        llm_args_user={"temperature": 0.0},
        max_steps=200,
        max_errors=10,
        timeout=600,
        max_retries=3,
        retry_delay=1,
        hallucination_retries=0,
        enforce_communication_protocol=False,
        verbose_logs=False,
        log_level="ERROR",
    )
    task = get_tasks(
        task_set_name="retail",
        task_split_name="base",
        task_ids=[task_id],
    )[0]
    orchestrator = build_text_orchestrator(config, task, seed=seed)
    simulation = orchestrator.run()

    runtime_root = Path.cwd()
    policy_path = runtime_root / "data/tau2/domains/retail/policy.md"
    tools_path = runtime_root / "src/tau2/domains/retail/tools.py"
    messages = [_message_payload(message) for message in simulation.messages]
    return {
        "schema_version": "tau3-fafo-episode-v1",
        "task_id": task_id,
        "seed": seed,
        "agent_model": AGENT_MODEL,
        "agent_temperature": 0.0,
        "user_simulator_model": USER_MODEL,
        "user_simulator_temperature": 0.0,
        "prompt_sha256": hashlib.sha256(prompt_body.encode("utf-8")).hexdigest(),
        "policy_sha256": _sha256(policy_path),
        "tools_sha256": _sha256(tools_path),
        "termination_reason": simulation.termination_reason.value,
        "agent_cost": simulation.agent_cost,
        "user_cost": simulation.user_cost,
        "messages": messages,
    }


def main() -> int:
    """Parse arguments, run one episode, and print exactly one JSON object."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--prompt-path", required=True, type=Path)
    args = parser.parse_args()

    payload = run(args.task_id, args.seed, args.prompt_path.resolve())
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
