#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Run the pinned Tau Retail development or final-holdout task partition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

TAU_COMMIT = "fc0055dc4e0a316c3f83133267fbd6faaa770992"
AGENT_MODEL = "gpt-4.1-2025-04-14"
USER_MODEL = "gpt-4.1-2025-04-14"
TENANT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TENANT_ROOT.parents[1]
DEFAULT_RUNTIME = REPO_ROOT.parent / "tau2-bench"
DEFAULT_SPLIT = TENANT_ROOT / "recipe/retail-split.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dotenv_has_key(path: Path, name: str) -> bool:
    if not path.is_file():
        return False
    prefix = f"{name}="
    return any(
        line.strip().startswith(prefix)
        and bool(line.strip()[len(prefix) :].strip().strip("'\""))
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def _validate_runtime(runtime: Path, split: dict[str, Any], *, require_key: bool) -> None:
    tau2 = runtime / ".venv/bin/tau2"
    if not tau2.is_file():
        raise FileNotFoundError(
            f"Tau executable not found at {tau2}; run setup_tau_runtime.py first"
        )
    actual_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=runtime,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_commit != TAU_COMMIT:
        raise ValueError(f"Tau revision mismatch: expected {TAU_COMMIT}, got {actual_commit}")
    for source in split["source_files"].values():
        source_path = runtime / source["path_at_release"]
        if _sha256(source_path) != source["sha256"]:
            raise ValueError(f"Tau source hash mismatch: {source_path}")
    if require_key and not (
        os.getenv("OPENAI_API_KEY") or _dotenv_has_key(runtime / ".env", "OPENAI_API_KEY")
    ):
        raise ValueError(
            "OPENAI_API_KEY is absent from the process and the Tau runtime .env"
        )


def _partition_task_ids(split: dict[str, Any], partition: str) -> list[str]:
    try:
        values = split["partitions"][partition]["task_ids"]
    except KeyError as exc:
        raise ValueError(f"Unknown partition: {partition}") from exc
    return [str(value) for value in values]


def build_command(
    *,
    runtime: Path,
    task_ids: list[str],
    trials: int,
    seed: int,
    save_to: str,
    max_concurrency: int,
    prompt: Path | None,
) -> list[str]:
    """Build the secret-free Tau CLI command."""
    tau2 = runtime / ".venv/bin/tau2"
    command = [
        str(tau2),
        "run",
        "--domain",
        "retail",
        "--task-set-name",
        "retail",
        "--task-split-name",
        "base",
        "--task-ids",
        *task_ids,
        "--num-trials",
        str(trials),
        "--agent",
        "llm_agent",
        "--agent-llm",
        AGENT_MODEL,
        "--agent-llm-args",
        json.dumps({"temperature": 0.0}, separators=(",", ":")),
        "--user",
        "user_simulator",
        "--user-llm",
        USER_MODEL,
        "--user-llm-args",
        json.dumps({"temperature": 0.0}, separators=(",", ":")),
        "--max-steps",
        "200",
        "--max-errors",
        "10",
        "--timeout",
        "600",
        "--max-retries",
        "3",
        "--retry-delay",
        "1",
        "--max-concurrency",
        str(max_concurrency),
        "--seed",
        str(seed),
        "--log-level",
        "ERROR",
        "--save-to",
        save_to,
        "--auto-resume",
    ]
    if prompt is None:
        return command
    launcher = TENANT_ROOT / "scripts/tau_prompt_cli.py"
    return [
        str(runtime / ".venv/bin/python"),
        str(launcher),
        str(prompt.resolve()),
        *command[1:],
    ]


def main() -> int:
    """Validate controls and run one frozen task partition."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument(
        "--partition",
        choices=("development", "final_holdout"),
        default="development",
    )
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--num-trials", type=int, default=4)
    parser.add_argument("--seed", type=int, default=300)
    parser.add_argument("--max-concurrency", type=int, default=3)
    parser.add_argument("--save-to")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.num_trials < 1 or args.max_concurrency < 1:
        raise ValueError("num-trials and max-concurrency must be positive")
    runtime = args.runtime.resolve()
    split = _load_json(args.split.resolve())
    _validate_runtime(runtime, split, require_key=not args.dry_run)
    if args.prompt and not args.prompt.resolve().is_file():
        raise FileNotFoundError(f"Prompt not found: {args.prompt.resolve()}")
    task_ids = _partition_task_ids(split, args.partition)
    save_to = args.save_to or f"fafo_v3_{args.partition}_{args.num_trials}trials"
    command = build_command(
        runtime=runtime,
        task_ids=task_ids,
        trials=args.num_trials,
        seed=args.seed,
        save_to=save_to,
        max_concurrency=args.max_concurrency,
        prompt=args.prompt,
    )
    print(
        f"Tau {args.partition}: {len(task_ids)} tasks x {args.num_trials} trials; "
        f"agent={AGENT_MODEL}; user={USER_MODEL}; temperature=0"
    )
    print(shlex.join(command))
    if args.dry_run:
        return 0
    return subprocess.run(command, cwd=runtime, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
