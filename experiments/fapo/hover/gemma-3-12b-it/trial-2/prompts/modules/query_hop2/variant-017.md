<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query to find a Wikipedia article. Output ONLY the query (3-10 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop1.output}

Your job: find the MISSING article. Look at NEXT TARGET and CLUES above. Generate a search query that uses:
- The entity name from NEXT TARGET as it would appear as a Wikipedia article title
- If CLUES suggest an alternative name or spelling, prefer that

Output only the search query.
