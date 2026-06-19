<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate TWO different BM25 search queries on separate lines. This is a RECOVERY search — previous queries may have missed the target. Output ONLY the two queries (one per line), nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Previous queries generated:
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}

Your job: find the MISSING article. The previous queries used exact entity names but failed. Generate exactly TWO different search queries, each on its own line:
Line 1: Use the entity name from NEXT TARGET combined with additional keywords from the claim (5-10 words)
Line 2: Try an alternative approach — different spelling, related entity, or category-level search (2-5 words)

Output only the two queries, one per line.
