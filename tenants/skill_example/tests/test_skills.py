# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for skill files and their runtime injection at the agentic layer.

skill_example is the agentic-skills demonstration tenant: reusable procedural
knowledge lives in skills/<name>/variant-NNN.md and is loaded at the agentic
layer — injected into the conversation as a distinct ``<available_skills>``
context message — rather than baked into the authored system prompt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.hephaestus.engine.skills import (
    build_skills_message,
    inject_skills_message,
    render_skills_block,
)

TENANT = Path(__file__).resolve().parent.parent
SKILLS_DIR = TENANT / "skills"
PROMPT = TENANT / "prompts" / "modules" / "agent" / "variant-001.md"

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def _skill_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/variant-*.md"))


def test_skill_files_exist() -> None:
    files = _skill_files()
    assert files, "skill_example must ship at least one skill file"


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.parent.name)
def test_skill_has_frontmatter(skill_path: Path) -> None:
    """Each skill must declare name + description, and name must match its dir."""
    text = skill_path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    assert match, f"{skill_path}: missing YAML frontmatter"
    fm = match.group(1)
    assert re.search(r"^name:\s*(\S+)", fm, re.MULTILINE), f"{skill_path}: missing name"
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE), f"{skill_path}: missing description"
    name = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE).group(1)
    assert name == skill_path.parent.name, (
        f"{skill_path}: frontmatter name {name!r} != directory {skill_path.parent.name!r}"
    )


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.parent.name)
def test_skill_body_has_no_placeholders(skill_path: Path) -> None:
    """Skill bodies are injected verbatim — they must not introduce ${...}."""
    text = skill_path.read_text(encoding="utf-8")
    body = _FRONTMATTER.sub("", text)
    assert "${" not in body, f"{skill_path}: skill body must not contain ${{...}} placeholders"


def test_prompt_does_not_inline_skills() -> None:
    """Skills load at the agentic layer — the authored prompt stays clean."""
    text = PROMPT.read_text(encoding="utf-8")
    assert "${skills}" not in text, "skills must not be inlined into the prompt template"
    # None of the skill headings should appear in the human-authored prompt.
    assert "Superlative Index Questions" not in text
    # The case placeholder is still present for per-case rendering.
    assert "${task}" in text


def test_render_skills_block_concatenates_all_skills() -> None:
    """render_skills_block strips frontmatter and concatenates skill bodies."""
    paths = [str(p) for p in _skill_files()]
    block = render_skills_block(paths)
    # Frontmatter must be stripped (no YAML delimiter / raw key leaks).
    assert "---" not in block
    assert "description:" not in block
    # Each skill contributes a heading derived from its directory name.
    assert "### Superlative Index Questions" in block
    assert "### Answer Formatting" in block
    # Representative body content from the skills is present.
    assert "splunk_get_index_info" in block
    assert "Answer:" in block


def test_skills_injected_as_runtime_message() -> None:
    """Skills are wrapped in an <available_skills> context message."""
    paths = [str(p) for p in _skill_files()]
    block = render_skills_block(paths)
    message = build_skills_message(block)
    assert message is not None
    assert message["role"] == "system"
    assert "<available_skills>" in message["content"]
    assert "loaded into your environment" in message["content"]
    assert "### Superlative Index Questions" in message["content"]


def test_inject_skills_message_after_system_prompt() -> None:
    """The skills message is inserted right after the leading system prompt."""
    paths = [str(p) for p in _skill_files()]
    message = build_skills_message(render_skills_block(paths))
    convo = [
        {"role": "system", "content": "You are a Splunk assistant."},
        {"role": "user", "content": "What indexes do I have?"},
    ]
    injected = inject_skills_message(list(convo), message)
    assert [m["role"] for m in injected] == ["system", "system", "user"]
    assert "<available_skills>" in injected[1]["content"]
    # The authored system prompt and the user task are preserved.
    assert injected[0]["content"] == convo[0]["content"]
    assert injected[2]["content"] == convo[1]["content"]


def test_no_skills_is_noop() -> None:
    """Empty skills -> no message, conversation unchanged."""
    assert build_skills_message("") is None
    convo = [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}]
    assert inject_skills_message(list(convo), None) == convo
