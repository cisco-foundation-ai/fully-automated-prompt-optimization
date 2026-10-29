# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Bounded Git facts recorded with each eval run."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Sequence

_GIT_OBJECT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_TIMEOUT_SECONDS = 5
_EVIDENCE_KEYS = ("commit", "committed_tree", "repository_dirty", "dependency_set_dirty")


def collect_git_evidence(repository_root: Path, members: Sequence[str]) -> Dict[str, Any]:
    """Return the checkout's commit, tree, and dirty flags.

    Args:
        repository_root: Root of the Git checkout.
        members: Repository-relative paths whose working-tree state sets
            ``dependency_set_dirty``, normally the eval runtime's own sources.

    Returns:
        ``commit``, ``committed_tree``, ``repository_dirty``, and
        ``dependency_set_dirty``. Every value is an ``unavailable`` marker when
        Git is missing or the root is not the top of a worktree.
    """
    root = repository_root.resolve()
    reason = "not_a_git_worktree"
    try:
        if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise ValueError("wrong Git root")
        commit = _git(root, "rev-parse", "--verify", "HEAD")
        tree = _git(root, "rev-parse", "--verify", "HEAD^{tree}")
        if not _GIT_OBJECT.fullmatch(commit) or not _GIT_OBJECT.fullmatch(tree):
            raise ValueError("malformed Git object identity")
        status = ("status", "--porcelain=v1", "-z", "--untracked-files=all")
        repository_dirty = bool(_git(root, *status))
        dependency_set_dirty = bool(_git(root, *status, "--", *members)) if members else False
    except FileNotFoundError:
        reason = "git_command_unavailable"
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        pass
    else:
        return {
            "commit": commit,
            "committed_tree": tree,
            "repository_dirty": repository_dirty,
            "dependency_set_dirty": dependency_set_dirty,
        }
    return {key: {"status": "unavailable", "reason": reason} for key in _EVIDENCE_KEYS}


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        cwd=root,
        capture_output=True,
        timeout=_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("Git command failed")
    return completed.stdout.decode("utf-8").strip()
