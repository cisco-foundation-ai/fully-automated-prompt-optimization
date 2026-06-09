<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate THREE different BM25 search queries on separate lines. This is a LAST RESORT search. Output ONLY the three queries (one per line), nothing else.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Previous queries that FAILED:
- ${steps.query_hop2.output}
- ${steps.query_hop3.output}
- ${steps.query_hop4.output}

Generate exactly THREE different search queries, each on its own line:
Line 1: A LONGER query (8-15 words) using multiple keywords from the claim that describe the missing entity
Line 2: A SHORT query (2-4 words) using an alternative name, abbreviation, or closely related entity
Line 3: A contextual query (4-8 words) using descriptive attributes, dates, or category of the entity

Output only the three queries, one per line.
