<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. This is a RECOVERY search — previous queries missed the target. Output ONLY the query, nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Previous queries that FAILED:
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}

Your job: find the MISSING article. Look at the CLUES and NEXT TARGET above. The previous queries used the obvious entity name and failed — do NOT repeat them. Instead, use the CLUES to construct a query with an alternative name, related person, associated work, or different spelling. Use the exact alternative as it would appear in a Wikipedia article title.

Output only the search query (3-8 words).
