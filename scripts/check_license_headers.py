#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Validate that all .py and .md files carry the required Cisco copyright header."""

from __future__ import annotations

import sys
from pathlib import Path

SKIP_DIRS = {
    ".venv",
    ".direnv",
    ".git",
    "__pycache__",
    ".egg-info",
    "hephaestus.egg-info",
    ".pytest_cache",
    "node_modules",
}

COPYRIGHT_LINE = "Copyright 2026 Cisco Systems, Inc. and its affiliates"
SPDX_LINE = "SPDX-License-Identifier: Apache-2.0"


def _is_generated_experiment_output(path: Path) -> bool:
    """Return True for machine-generated experiment artifacts under an
    ``experiments/.../evals/`` directory (e.g. eval-runner ``summary.md`` files).

    These are reference data — the verbatim output of evaluation and
    optimization runs — not licensed source, so they are exempt from the
    header requirement. Hand-authored docs elsewhere under ``experiments/``
    (such as ``experiments/README.md``) are still checked.
    """
    parts = path.parts
    return "experiments" in parts and "evals" in parts


def _should_skip(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    return _is_generated_experiment_output(path)


def _has_header(path: Path) -> bool:
    """Return True if the file contains both required header lines."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True  # skip unreadable files
    return COPYRIGHT_LINE in text and SPDX_LINE in text


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    failures: list[str] = []

    for ext in ("py", "md"):
        for path in sorted(root.rglob(f"*.{ext}")):
            if _should_skip(path):
                continue
            if not _has_header(path):
                failures.append(str(path))

    if failures:
        print(f"Missing license headers in {len(failures)} file(s):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1

    print("All files have required license headers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
