<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate Wikipedia search queries to find missing evidence for a multi-hop claim. Your task is to identify specific entities (people, places, events, works, organizations) mentioned or implied in the claim that have NOT yet been found.

Rules:
- Output exactly 8 search queries, one per line
- Each query must be a likely Wikipedia article title (1-5 words)
- Focus on proper nouns and named entities
- Include variant spellings, abbreviations, and alternate names
- Try both full names and partial names (e.g., "John Smith" AND "Smith")
- If an entity has a disambiguation (e.g., "Springfield" could be many places), include the most likely version
- Do NOT output numbering, bullets, explanations, or anything else
- Never output "N/A" or empty lines

User: Claim: ${claim}

Analysis from first retrieval:
${steps.summarize_hop1.output}

Output 8 Wikipedia article title queries targeting entities from STILL NEEDED:
