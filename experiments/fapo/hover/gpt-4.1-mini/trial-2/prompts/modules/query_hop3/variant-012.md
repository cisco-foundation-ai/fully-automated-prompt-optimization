<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Given a claim and two rounds of retrieved information, identify one entity referenced in the claim that has NOT been found yet. Output ONLY that entity name as a search query. It must be DIFFERENT from what was searched in hop 2.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}

Hop 2 search produced: ${steps.summarize_hop2.output}

The hop 2 query was: ${steps.query_hop2.output}

Rules:
- Output exactly one entity name (1-5 words)
- It must be referenced (directly or indirectly) in the claim
- It must NOT appear in any TITLES list above
- It must be DIFFERENT from the hop 2 query: "${steps.query_hop2.output}"
- Prefer proper nouns (person names, place names, work titles)

Search query:
