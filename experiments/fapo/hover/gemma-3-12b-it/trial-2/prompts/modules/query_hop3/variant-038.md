<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate THREE different BM25 search queries on separate lines. This is a targeted search based on analysis of prior retrieval results. Output ONLY the three queries (one per line), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop2.output}

Previous query: ${steps.query_hop2.output}

Your job: find the MISSING article. Look at NEXT TARGET and CLUES above. Generate exactly THREE different search queries, each on its own line:
Line 1: Use the entity name from NEXT TARGET exactly (3-6 words)
Line 2: Use an alternative name or related entity from CLUES (2-5 words)
Line 3: Use descriptive keywords about the entity's characteristics (4-8 words)

Output only the three queries, one per line.
