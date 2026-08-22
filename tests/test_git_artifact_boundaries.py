# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
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
    """Strike annotations preserve the ce7 audit and match verified stack scope."""
    repo_root = Path(__file__).resolve().parents[1]
    report = (
        repo_root / "docs/processes/evaluation-asset-studio-stress-test.md"
    ).read_text(encoding="utf-8")
    license_header = (
        "<!--\n"
        "Copyright 2026 Cisco Systems, Inc. and its affiliates\n"
        "\n"
        "SPDX-License-Identifier: Apache-2.0\n"
        "-->\n"
        "\n"
    )
    assert report.startswith(license_header)
    historical_lines = report.removeprefix(license_header).splitlines(
        keepends=True
    )[:599]
    restored_history = "".join(historical_lines).replace("~~", "")

    assert hashlib.sha256(restored_history.encode("utf-8")).hexdigest() == (
        "b178ab4357e5a89447b874458891c106f5a23f12347a8e6a0f61c3cc389a338d"
    )
    assert all(line.count("~~") % 2 == 0 for line in historical_lines)
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
    assert "#### ~~FAPO-01: saved results omit facts needed to explain failures~~" in report
    assert "#### ~~FAPO-02: the comparison tool can compare different experiments~~" in report
    assert "#### ~~FAPO-03: duplicate case IDs are accepted~~" in report
    assert "#### ~~FAPO-04: provider or chain initialization failures can be masked~~" in report
    assert "#### ~~FAPO-05: infrastructure failures can look like completed model regressions~~" in report
    assert "#### ~~Run artifacts and failure status need stronger reproducibility semantics~~" in report
    assert "#### ~~Tool and skill capabilities are not uniformly provider-neutral~~" not in report
    assert "~~The paper correctly describes tenant isolation" not in report
    assert "| ~~FAPO compares variants fairly~~ |" in report
    assert "| ~~Attribution locates failures~~ |" in report
    assert "PR_LINK_PLACEHOLDER" not in report
    assert (
        "- [x] Preserve privacy-safe diagnostic evidence in FAPO results or "
        "verified joins"
    ) in report
    assert "PR: [#28]" in report
    assert "implementation commit: [`78dd591f`]" in report
    assert (
        "- [ ] Add and validate semantic/paraphrase duplicate detection"
    ) in report
    assert "- [ ] Provide or capability-check executable scorers" in report
    assert "- [ ] Run the minimum falsifiable four-condition study" in report

    immediate_checklist = report.split(
        "### Successor checklist: immediate engineering and release gates",
        maxsplit=1,
    )[1].split(
        "### Successor checklist: research-dependent validation",
        maxsplit=1,
    )[0]
    checked_rows = [
        line
        for line in immediate_checklist.splitlines()
        if line.startswith("- [x] ")
    ]
    assert len(checked_rows) == 31
    for row in checked_rows:
        assert "PR: [#" in row or "PRs: [#" in row
        assert (
            "implementation commit: [" in row
            or "implementation commits: [" in row
        )
        assert any(label in row for label in ("test: ", "tests: ", "verification: "))

    cited_tests = {
        name
        for row in checked_rows
        for name in re.findall(r"`(test_[a-zA-Z0-9_]+)`", row)
    }
    test_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (repo_root / "tests").rglob("test_*.py")
    )
    unresolved = sorted(
        name for name in cited_tests if f"def {name}(" not in test_source
    )
    assert not unresolved, f"Unresolved checklist tests: {unresolved}"
