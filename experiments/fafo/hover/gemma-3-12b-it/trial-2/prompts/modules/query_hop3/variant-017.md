<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. This is a targeted search based on analysis of prior retrieval results. Output ONLY the query, nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop2.output}

Previous query: ${steps.query_hop2.output}

Your job: find the MISSING article. Look at NEXT TARGET and CLUES above. Generate a search query (3-10 words) that:
- Uses the entity name from NEXT TARGET
- If a previous query already tried that name, use an alternative from CLUES instead

Output only the search query.
