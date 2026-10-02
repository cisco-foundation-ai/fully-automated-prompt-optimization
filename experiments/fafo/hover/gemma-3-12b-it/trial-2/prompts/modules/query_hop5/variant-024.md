<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. This is the FINAL search attempt — all previous queries using entity names have failed. Use a completely different approach. Output ONLY the query, nothing else.

User: Claim: ${claim}

Analysis after 4 hops: ${steps.summarize_hop4.output}

Previous queries that ALL FAILED:
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}
- Query 4: ${steps.query_hop4.output}

Look at NEXT TARGET and FAILED APPROACHES above. Generate ONE search query (5-15 words) using a COMPLETELY DIFFERENT angle — NOT the entity name that already failed. Try:
- Descriptive keywords about what the entity IS or DOES
- A broader category or "list of" page
- A closely related entity whose article links to the target

Output only the search query.
