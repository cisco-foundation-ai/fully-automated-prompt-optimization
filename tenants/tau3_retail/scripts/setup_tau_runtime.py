#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Create and validate a pinned Tau-3 checkout beside the FAPO repository."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


TAU_REPOSITORY = "https://github.com/sierra-research/tau2-bench.git"
TAU_RELEASE = "v1.0.1"
TAU_COMMIT = "fc0055dc4e0a316c3f83133267fbd6faaa770992"
TENANT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TENANT_ROOT.parents[1]
DEFAULT_RUNTIME = REPO_ROOT.parent / "tau2-bench"
TRUSTSTORE_PATCH = TENANT_ROOT / "patches/tau3-v1.0.1-truststore.patch"


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    capture: bool = False,
) -> str:
    """Run one command or print it during a dry run."""
    prefix = f"(cd {shlex.quote(str(cwd))} && " if cwd else ""
    suffix = ")" if cwd else ""
    print(prefix + shlex.join(command) + suffix)
    if dry_run:
        return ""
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=capture,
        text=True,
    )
    return completed.stdout.strip() if capture else ""


def _is_patch_applied(runtime: Path) -> bool:
    """Return whether the exact truststore patch is already present."""
    completed = subprocess.run(
        ["git", "apply", "--reverse", "--check", str(TRUSTSTORE_PATCH)],
        cwd=runtime,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _working_tree_matches_patch(runtime: Path) -> bool:
    """Return whether the only checkout changes are the published patch."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=runtime,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if not status:
        return False
    diff = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--binary"],
        cwd=runtime,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return _is_patch_applied(runtime) and diff == TRUSTSTORE_PATCH.read_text(
        encoding="utf-8"
    )


def setup(runtime: Path, *, truststore: bool, dry_run: bool) -> None:
    """Clone, pin, optionally patch, sync, and validate Tau."""
    runtime = runtime.resolve()
    if not runtime.exists():
        _run(
            ["git", "clone", TAU_REPOSITORY, str(runtime)],
            dry_run=dry_run,
        )
    elif not (runtime / ".git").is_dir():
        raise ValueError(f"Existing runtime is not a Git checkout: {runtime}")

    if not dry_run:
        dirty = _run(
            ["git", "status", "--porcelain"],
            cwd=runtime,
            capture=True,
        )
        if dirty and not (truststore and _working_tree_matches_patch(runtime)):
            raise ValueError(
                "Tau checkout has unrelated local changes; use a clean checkout"
            )

    _run(["git", "fetch", "--tags", "origin"], cwd=runtime, dry_run=dry_run)
    _run(["git", "checkout", "--detach", TAU_COMMIT], cwd=runtime, dry_run=dry_run)

    if truststore and not dry_run and not _is_patch_applied(runtime):
        _run(
            ["git", "apply", "--check", str(TRUSTSTORE_PATCH)],
            cwd=runtime,
        )
        _run(["git", "apply", str(TRUSTSTORE_PATCH)], cwd=runtime)
    elif truststore and dry_run:
        _run(["git", "apply", str(TRUSTSTORE_PATCH)], cwd=runtime, dry_run=True)

    _run(["uv", "sync", "--frozen"], cwd=runtime, dry_run=dry_run)
    _run([str(runtime / ".venv/bin/tau2"), "check-data"], cwd=runtime, dry_run=dry_run)

    if not dry_run:
        actual = _run(
            ["git", "rev-parse", "HEAD"],
            cwd=runtime,
            capture=True,
        )
        if actual != TAU_COMMIT:
            raise ValueError(f"Tau revision mismatch: expected {TAU_COMMIT}, got {actual}")
        print(f"Tau {TAU_RELEASE} is ready at {runtime}")


def main() -> int:
    """Parse command-line arguments and prepare the sibling runtime."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument(
        "--use-system-truststore",
        action="store_true",
        help="Apply the pinned optional TLS truststore patch before syncing.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup(
        args.runtime,
        truststore=args.use_system_truststore,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
