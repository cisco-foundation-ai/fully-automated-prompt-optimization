<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate TWO different BM25 search queries on separate lines. Output ONLY the two queries (one per line), nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop1.output}

Generate exactly TWO different search queries targeting the entity in NEXT TARGET, each on its own line:
Line 1: The exact name from NEXT TARGET as it would appear as a Wikipedia article title (2-6 words)
Line 2: An alternative approach — use a clue from CLUES, an alternative name, or related context (3-8 words)

Output only the two queries, one per line.
