# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
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


def test_stress_report_preserves_history_and_marks_verified_remediation() -> None:
    """Strike annotations preserve the ce7 audit and match verified PR1 scope."""
    repo_root = Path(__file__).resolve().parents[1]
    report = (
        repo_root / "docs/processes/evaluation-asset-studio-stress-test.md"
    ).read_text(encoding="utf-8")
    historical_lines = report.splitlines(keepends=True)[:599]
    restored_history = "".join(historical_lines).replace("~~", "")

    assert hashlib.sha256(restored_history.encode("utf-8")).hexdigest() == (
        "b178ab4357e5a89447b874458891c106f5a23f12347a8e6a0f61c3cc389a338d"
    )
    assert "~~**Fix and check.** Ignore the entire current asset runtime tree" in report
    assert "~~**Fix and check.** Make redaction schema-aware" in report
    assert "~~**Fix and check.** Remove or deprecate the alternate commands" in report
    assert "~~The code checks whether `cluster_count` fits the data only in Stage 4" in report
    assert "~~The default unlabeled-to-trusted ratio is `20.0`" in report
    assert "~~Restrict sources to the chosen tenant" in report
    assert "~~1. **Prevent data exposure.**" in report
    assert "~~**Preserve IDs.** Redact only content fields" in report
    assert "~~2. **Give every public command the same rules.**" in report
    assert "~~sound embedding shapes/indices~~" in report
    assert (
        "- [x] Remove/deprecate alternate asset commands or route them through "
        "the same contract, matching, splitting, and regression policies (EA-09)."
    ) in report
    assert "~~Add a broader privacy screen and review hold.~~" not in report
    assert "~~Before remote use, add authentication" not in report
    assert "~~Treat trace text as untrusted instructions" not in report
    assert "~~Group near-duplicates before splitting" not in report
