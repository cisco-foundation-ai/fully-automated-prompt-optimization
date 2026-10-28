<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO style guide

Coding standards for the FAFO evaluation engine. They follow existing patterns
in the codebase; apply them to all new code.

## Python and tooling

- **Python 3.10+.** Use modern syntax where available.
- **pytest** for all testing.
- `from __future__ import annotations` at the top of every module. It enables
  PEP 604 unions on older runtimes and defers annotation evaluation.
- Type hints on all function signatures and return types.

## Data modeling

- Prefer `@dataclass` for data containers (see `src/hephaestus/types.py`).
- Use `Optional[T]` with a `= None` default for optional fields.
- Use `field(default_factory=...)` for mutable defaults (dicts, lists).
- Keep dataclasses focused: one responsibility per class.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class ChainConfig:
    """Configuration for a LangGraph chain."""

    path: str
    fn: str = "build_chain"
    config: Dict[str, Any] = field(default_factory=dict)
```

## Code style

- **Docstrings:** Google style on public functions and classes. Start with a
  short summary line; add detail paragraphs only when behavior is non-obvious.
- **Test docstrings:** a one-line description of what each test method tests.
- **Inline comments:** only where logic is non-obvious. Prefer self-documenting
  code.
- **Import order:**
  1. `__future__`
  2. Standard library
  3. Third-party packages
  4. Local imports (`src.hephaestus.*`)

## Testing

- **File naming:** test files mirror source paths with a `test_` prefix:
  - `src/hephaestus/chains/nodes.py` → `tests/test_chain_nodes.py`
  - `src/hephaestus/chains/loader.py` → `tests/test_chain_loader.py`
- **Class grouping:** group tests in classes by the function or class under
  test (for example, `TestBuildNodeContext`, `TestMakeLlmNode`).
- **Method names:** descriptive `test_<scenario>` names (for example,
  `test_empty_state`, `test_custom_output_key`,
  `test_missing_placeholders_no_crash`).
- **Fixtures:** use pytest fixtures (`tmp_path`) and `unittest.mock.MagicMock`
  for isolation.
- **Run tests:** `python -m pytest`

## Project structure

```text
src/hephaestus/    # Core evaluation engine and provider interfaces
hephaestus/        # Public package shim for `python -m hephaestus.cli`
tenants/<id>/      # Tenant-specific prompts, datasets, source artifacts
tests/             # Automated tests for core modules
docs/              # Product-level architecture and usage docs
```

## Security

- **No secrets in committed files.** Use environment variables or secret
  managers.
- **Tenant data isolation.** Tenant-specific information must never appear
  outside `tenants/<tenant_id>/`. See the Tenant Data Safety section in
  `CLAUDE.md`.
- **Protected artifacts.** Treat `tenants/*/source_artifacts/` as read-only
  unless explicitly asked to modify them.
