<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate TWO different BM25 search queries on separate lines. Output ONLY the two queries (one per line), nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop1.output}

Your job: find the MISSING entity's Wikipedia article. Look at NEXT TARGET and CLUES above.

Generate exactly TWO queries, each on its own line:
Line 1: The exact entity name from NEXT TARGET as it would appear as a Wikipedia article title (2-5 words)
Line 2: An alternative name from CLUES — a different spelling, nickname, or associated entity (2-5 words)

Output only the two queries, one per line.
