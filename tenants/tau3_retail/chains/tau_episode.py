# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Run one fresh Tau episode for each FAPO evaluation case."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.types import ChainState


def _last_assistant_text(messages: list[dict[str, Any]]) -> str:
    """Return the last textual assistant response from a Tau episode."""
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("content"):
            return str(message["content"])
    return ""


def build_chain(provider: Any, config: Dict[str, Any]) -> Any:
    """Build a single-node chain that delegates execution to the pinned Tau runtime."""
    del provider  # Tau owns task-agent and user-simulator provider calls.

    prompt_path = Path(config["prompt_paths"]["agent"]).resolve()
    tau_runtime = Path(config["tau_runtime_path"]).resolve()
    tau_python = tau_runtime / ".venv/bin/python"
    episode_runner = Path(config["episode_runner_path"]).resolve()
    timeout_seconds = int(config.get("episode_timeout_seconds", 660))

    if not prompt_path.is_file():
        raise FileNotFoundError(f"Tau prompt variant not found: {prompt_path}")
    if not tau_python.is_file():
        raise FileNotFoundError(f"Tau Python runtime not found: {tau_python}")
    if not episode_runner.is_file():
        raise FileNotFoundError(f"Tau episode runner not found: {episode_runner}")

    def run_episode(state: ChainState) -> Dict[str, Any]:
        context = state.get("context") or {}
        runtime_raw = context.get("runtime_json")
        if not isinstance(runtime_raw, str):
            raise ValueError("Tau case context is missing runtime_json")
        runtime = json.loads(runtime_raw)
        task_id = str(runtime["task_id"])
        seed = int(runtime["seed"])

        command = [
            str(tau_python),
            str(episode_runner),
            "--task-id",
            task_id,
            "--seed",
            str(seed),
            "--prompt-path",
            str(prompt_path),
        ]
        environment = dict(os.environ)
        environment["PYTHONUNBUFFERED"] = "1"
        completed = subprocess.run(
            command,
            cwd=tau_runtime,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()[-4000:]
            raise RuntimeError(
                f"Tau episode failed for task {task_id} with exit code "
                f"{completed.returncode}: {stderr}"
            )
        try:
            episode = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Tau episode returned invalid JSON for task {task_id}: "
                f"{completed.stdout[-1000:]}"
            ) from exc

        messages = episode.get("messages") or []
        output_text = _last_assistant_text(messages)
        diagnostics = [
            f"tau_task={task_id}",
            f"tau_seed={seed}",
            f"tau_termination={episode.get('termination_reason')}",
            "training_agent_inferences=1",
        ]
        return {
            "output_text": output_text,
            "step_outputs": {
                "tau_episode": json.dumps(
                    episode,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            },
            "diagnostics": diagnostics,
        }

    graph = StateGraph(ChainState)
    graph.add_node("tau_episode", run_episode)
    graph.set_entry_point("tau_episode")
    graph.add_edge("tau_episode", END)
    return graph.compile()
