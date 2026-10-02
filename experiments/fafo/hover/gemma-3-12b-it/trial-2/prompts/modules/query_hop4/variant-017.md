<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. This is a RECOVERY search — previous queries may have missed the target. Output ONLY the query, nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Previous queries generated:
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}

Your job: find the MISSING article. The previous queries used exact entity names but failed. Try ONE of these strategies:
1. Use a LONGER query (8-12 words) with multiple keywords from the claim that relate to the missing entity
2. Use a different spelling or transliteration of the entity name
3. Search for a closely associated entity whose article will contain the missing information

Output only the search query.
