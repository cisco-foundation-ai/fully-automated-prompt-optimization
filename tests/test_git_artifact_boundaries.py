# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "relative_path",
    [
        "tenants/example/evaluation_assets/v1/config.json",
        "tenants/example/evaluation_assets/v1/stages/01_raw_inputs/input.jsonl",
        "tenants/example/datasets/evaluation_assets/v1/train.jsonl",
    ],
)
def test_evaluation_asset_runtime_files_are_ignored(relative_path: str) -> None:
    """Git ignores Studio workspaces and every published dataset payload."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", relative_path],
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 0


def test_customer_artifact_payloads_are_not_git_tracked():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    allowed_suffixes = {
        "source_artifacts/.gitkeep",
        "datasets/.gitkeep",
    }

    violations = []
    for path in tracked:
        if (
            path.startswith("tenants/")
            and "/source_artifacts/" in f"/{path}"
            and not any(path.endswith(s) for s in allowed_suffixes)
        ):
            violations.append(path)
        if (
            path.startswith("tenants/")
            and "/datasets/" in f"/{path}"
            and not any(path.endswith(s) for s in allowed_suffixes)
        ):
            violations.append(path)
        if (
            path.startswith("tenants/")
            and "/evaluation_assets/" in f"/{path}"
        ):
            violations.append(path)

    assert not violations, f"Tracked customer artifact payload files found: {violations}"
