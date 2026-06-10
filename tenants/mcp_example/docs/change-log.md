<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Change Log

## 2026-06-10
- Summary: Added the full required tenant doc set (tenant-profile, data-contract, prompt-contract, eval-operations, change-log, docs-index) and restructured the iteration playbook to satisfy tenant-docs-contract checks.
- Why: mcp_example previously only had an iteration playbook; CI validates tenant doc alignment.
- Files/configs: docs/tenant-profile.md, docs/data-contract.md, docs/prompt-contract.md, docs/eval-operations.md, docs/change-log.md, docs/docs-index.yaml, docs/iteration-playbook.md.
- Eval impact: None — documentation only.
- Rollback notes: N/A.

## 2026-06-10
- Summary: Established mcp_example as the reference tenant for MCP/agentic evaluation — ReAct agent chain, 30-case tool/reasoning dataset, tool-aware scorer, and eval config wired to the bundled mock MCP server.
- Why: Provide a runnable, credential-free demonstration and template for MCP-backed tenants.
- Files/configs: chains/react_agent.py, prompts/modules/agent/variant-001.md, datasets/tool_tasks.jsonl, code/scorers/task_scorer.py, configs/eval.json.
- Eval impact: Baseline established with variant-001 on gpt-4o-mini.
- Rollback notes: N/A — initial tenant setup.
