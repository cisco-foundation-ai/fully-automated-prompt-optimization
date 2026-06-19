<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop3.output}

Previous queries that failed:
- ${steps.query_hop2.output}
- ${steps.query_hop3.output}

Generate a search query using a COMPLETELY DIFFERENT approach. Pick a name from MENTIONED that hasn't been searched yet, or try:
- A broader category (e.g., the genre, era, or field)
- An associated person or work discovered in the passages
- The target entity's alternative name or nickname
