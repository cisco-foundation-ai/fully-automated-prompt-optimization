#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Run the Tau CLI after replacing only the standard agent instruction."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Load a prompt file, patch Tau's agent instruction, and delegate to Tau."""
    if len(sys.argv) < 3:
        raise SystemExit("usage: tau_prompt_cli.py PROMPT_PATH run [tau arguments ...]")

    prompt_path = Path(sys.argv[1]).resolve()
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"Agent prompt is empty: {prompt_path}")

    import tau2.agent.llm_agent as llm_agent

    llm_agent.AGENT_INSTRUCTION = prompt

    from tau2.cli import main as tau_main

    sys.argv = ["tau2", *sys.argv[2:]]
    tau_main()


if __name__ == "__main__":
    main()
