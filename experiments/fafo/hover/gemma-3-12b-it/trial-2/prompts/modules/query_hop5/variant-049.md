<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate TWO different BM25 search queries on separate lines. This is a LAST RESORT search — all previous approaches failed. Output ONLY the two queries (one per line), nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Previous queries that ALL FAILED:
- ${steps.query_hop2.output}
- ${steps.query_hop3.output}
- ${steps.query_hop4.output}

The missing entity could NOT be found with direct name searches. Look at the CLUES above — they contain alternative names, associated people, related works, or different spellings. Use CLUES to construct queries that approach the missing entity from a completely different angle.

Generate exactly TWO queries, each on its own line:
Line 1: Use an alternative name or related entity from CLUES combined with a category keyword (3-8 words)
Line 2: Use a different CLUE — another spelling, associated person, or the title of a related work (2-5 words)

Output only the two queries, one per line.
