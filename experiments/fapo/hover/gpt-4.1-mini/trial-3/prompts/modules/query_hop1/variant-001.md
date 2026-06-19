<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract search queries from a multi-hop claim. The claim references multiple Wikipedia entities (people, places, films, songs, events, organizations). Generate targeted search queries to find Wikipedia articles for each entity.

Rules:
- Output exactly 5 search queries, one per line
- Each query must be a likely Wikipedia article title (1-5 words)
- Extract every proper noun and named entity from the claim
- Include the most specific entity references (film titles, person names, event names)
- Do NOT output numbering, bullets, explanations, or anything else

User: Claim: ${claim}

Output 5 Wikipedia article title queries for entities in this claim:
