# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.hephaestus.runs.git_evidence import collect_git_evidence


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "runtime.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "other.txt").write_text("a\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


class TestCollectGitEvidence:
    def test_clean_checkout(self, repo: Path) -> None:
        """A clean checkout reports its commit and tree and no dirty state."""
        evidence = collect_git_evidence(repo, ["runtime.py"])

        assert len(evidence["commit"]) in (40, 64)
        assert len(evidence["committed_tree"]) in (40, 64)
        assert evidence["repository_dirty"] is False
        assert evidence["dependency_set_dirty"] is False

    def test_unrelated_change_leaves_dependency_set_clean(self, repo: Path) -> None:
        """Changes outside the member list mark only the repository dirty."""
        (repo / "other.txt").write_text("b\n", encoding="utf-8")

        evidence = collect_git_evidence(repo, ["runtime.py"])

        assert (evidence["repository_dirty"], evidence["dependency_set_dirty"]) == (True, False)

    def test_member_change_marks_dependency_set_dirty(self, repo: Path) -> None:
        """A change to a listed member marks the dependency set dirty."""
        (repo / "runtime.py").write_text("x = 2\n", encoding="utf-8")

        evidence = collect_git_evidence(repo, ["runtime.py"])

        assert (evidence["repository_dirty"], evidence["dependency_set_dirty"]) == (True, True)

    def test_non_worktree_returns_unavailable_markers(self, tmp_path: Path) -> None:
        """A directory that is not a Git worktree yields unavailable markers."""
        evidence = collect_git_evidence(tmp_path, ["runtime.py"])

        marker = {"status": "unavailable", "reason": "not_a_git_worktree"}
        assert evidence == {
            "commit": marker,
            "committed_tree": marker,
            "repository_dirty": marker,
            "dependency_set_dirty": marker,
        }
