# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Skill-file loading and runtime injection for agentic chains.

A *skill* is a reusable block of procedural knowledge stored as markdown at
``tenants/<id>/skills/<skill-name>/variant-NNN.md``. Skills are a textual
optimization granularity, co-equal with prompt text: the optimization agent
clones them to new variants and evaluates them the same way it does prompts.

Skills are loaded **at the agentic layer**, not baked into the authored system
prompt. The chain renders the configured skills and the agentic node injects
them into the conversation as a distinct, runtime-framed ``<available_skills>``
context message — mimicking an agent harness that discovers and loads skills
into its environment at session start. They remain fully in context for every
model call (deterministic, unlike on-demand progressive disclosure), but a
reader of the authored prompt template never sees them inlined there.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Matches an optional YAML frontmatter block at the very start of a file:
#   ---\n ... \n---\n
_FRONTMATTER_PATTERN = re.compile(r"\A﻿?---\r?\n.*?\r?\n---\r?\n", re.DOTALL)

# Matches a leading HTML/license comment block (the repo's copyright header).
_LEADING_COMMENT_PATTERN = re.compile(r"\A\s*<!--.*?-->\s*", re.DOTALL)

# Runtime preamble that frames the injected skills as environment context the
# agent loaded — not part of the human-authored prompt.
_SKILLS_PREAMBLE = (
    "The following reusable skills have been loaded into your environment for "
    "this session. Each is a proven procedure for a class of tasks. Apply the "
    "relevant skill whenever the current task matches its scope."
)


def _strip_metadata(text: str) -> str:
    """Remove a leading YAML frontmatter block and/or HTML license comment."""
    stripped = _FRONTMATTER_PATTERN.sub("", text, count=1)
    stripped = _LEADING_COMMENT_PATTERN.sub("", stripped, count=1)
    return stripped.strip()


def _skill_title(skill_path: Path) -> str:
    """Derive a human-readable heading from a skill file path.

    Skill files live at ``skills/<skill-name>/variant-NNN.md``, so the parent
    directory name is the skill's identity. Falls back to the file stem.
    """
    name = skill_path.parent.name or skill_path.stem
    return name.replace("-", " ").replace("_", " ").strip().title()


def render_skills_block(skill_paths: Iterable[str]) -> str:
    """Read and concatenate skill files into a single content block.

    Each skill's metadata (frontmatter / license comment) is stripped and its
    body is rendered under a ``###`` heading derived from the skill directory
    name. Returns an empty string when no skill paths are given so that callers
    degrade to a no-op for tenants that do not use skills.

    The returned string is the *content* of the skills — the runtime framing
    that marks it as loaded-at-the-agentic-layer is added by
    :func:`build_skills_message`.

    Raises:
        FileNotFoundError: if a configured skill file does not exist. Validation
            in the eval runner surfaces this earlier with a clearer message;
            this is a defensive backstop.
    """
    paths = [Path(p) for p in skill_paths if p]
    if not paths:
        return ""

    sections: List[str] = []
    for path in paths:
        body = _strip_metadata(path.read_text(encoding="utf-8"))
        if not body:
            continue
        sections.append(f"### {_skill_title(path)}\n\n{body}")

    return "\n\n".join(sections)


def build_skills_message(skills_text: str) -> Optional[Dict[str, str]]:
    """Wrap rendered skills content into a runtime-injected context message.

    Returns a ``system``-role message dict whose content frames the skills as
    capabilities loaded into the agent's environment, or ``None`` when there is
    no skill content (so callers can skip injection entirely).

    The agentic/LLM node inserts this message into the conversation just after
    the authored system prompt, so the skills live in the agent's runtime
    context rather than in the human-authored prompt template.
    """
    if not skills_text or not skills_text.strip():
        return None
    content = (
        "<available_skills>\n"
        f"{_SKILLS_PREAMBLE}\n\n"
        f"{skills_text.strip()}\n"
        "</available_skills>"
    )
    return {"role": "system", "content": content}


def inject_skills_message(
    messages: List[Dict[str, str]], skills_message: Optional[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Return *messages* with the loaded-skills message inserted at the front.

    The skills message is placed immediately after the leading system prompt (or
    at the very start if there is no system prompt), so it sits in the agent's
    standing context for every model call. A fresh copy of the message dict is
    inserted so concurrent cases never share mutable state. When
    *skills_message* is ``None`` the original list is returned unchanged.
    """
    if not skills_message:
        return messages
    insert_at = 1 if messages and messages[0].get("role") == "system" else 0
    messages.insert(insert_at, dict(skills_message))
    return messages
