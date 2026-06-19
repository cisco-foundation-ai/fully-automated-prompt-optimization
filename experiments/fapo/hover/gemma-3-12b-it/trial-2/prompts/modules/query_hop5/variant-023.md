<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. This is a LAST RESORT search — all previous queries using entity names have failed. Try a completely different approach. Output ONLY the query, nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Previous queries that FAILED to find the missing article:
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}
- Query 4: ${steps.query_hop4.output}

Since direct name searches failed, try ONE of these alternative strategies:
1. Search for a BROADER CATEGORY that would contain the missing entity (e.g., "list of X" or "X discography" or "X filmography")
2. Use DESCRIPTIVE KEYWORDS from the claim that describe what the entity IS rather than its name
3. Search for a RELATED entity that would be linked to the missing one
4. Try a PARTIAL name match or abbreviation

Output only the search query (5-15 words).
