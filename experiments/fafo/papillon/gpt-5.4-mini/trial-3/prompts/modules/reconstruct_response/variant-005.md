<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Produce the final response to the user's original query.

You receive:
1. The original query (contains all names, places, and identifying details).
2. A draft response generated from a redacted version of the query (may use generic placeholders).

Your task:
- Start from the draft response's content and structure.
- Substitute every placeholder or generic reference back to the specific entity from the original query.
- If the draft is incomplete, refuses the task, or fails to address the query, then answer the original query fully from your own knowledge.
- Match the language of the original query exactly.
- Output the final response only — no meta-commentary, no mention of drafts or reconstruction.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}
