<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate TWO different BM25 search queries on separate lines. This is a targeted search based on analysis of prior retrieval results. Output ONLY the two queries (one per line), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop2.output}

Previous query: ${steps.query_hop2.output}

Your job: find the MISSING article. Look at NEXT TARGET and CLUES above. Generate exactly TWO different search queries, each on its own line:
Line 1: Use the entity name from NEXT TARGET (3-8 words)
Line 2: Use an alternative from CLUES — a different name, related person, or associated work (2-6 words)

Output only the two queries, one per line.
