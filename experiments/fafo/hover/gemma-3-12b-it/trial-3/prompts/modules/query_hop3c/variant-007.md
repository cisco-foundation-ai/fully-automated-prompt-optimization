<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words). You must pick from the entity list below. Never output "N/A".

User: Claim: ${claim}

Entity names found in passages:
${steps.extract_entities.output}

What is still missing (from summarize2):
${steps.summarize_hop2.output}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

RULES:
- Pick ONE entity from the list above that matches what summarize2 says is MISSING.
- Do NOT pick entities that are the same as previous queries.
- Do NOT pick the entity that is already clearly retrieved (the one summarize2 says was FOUND).
- The missing entity is the one that verifies the part of the claim we haven't confirmed yet.

Output just the entity name, nothing else.
