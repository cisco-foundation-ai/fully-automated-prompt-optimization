<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate Wikipedia search queries to find the final missing evidence for a multi-hop claim. After two rounds of retrieval, some entities are still not found. Your task is to generate creative alternate queries to locate them.

Strategy:
- Look at what's still missing after two retrieval rounds
- Try completely different phrasings and angles
- Use related entities that might lead to the missing one (e.g., search for a film's director if the film itself wasn't found)
- Try broader category searches if specific titles fail

Rules:
- Output exactly 10 search queries, one per line
- Each query should be a plausible Wikipedia article title (1-6 words)
- Try alternate approaches: related entities, broader categories, different name forms
- Include both specific titles and broader related searches
- Do NOT output numbering, bullets, explanations, or anything else
- Never output "N/A" or empty lines — always generate 10 queries

User: Claim: ${claim}

Analysis from first retrieval: ${steps.summarize_hop1.output}
Analysis from second retrieval: ${steps.summarize_hop2.output}

Output 10 Wikipedia article title queries using creative alternate approaches for entities still not found:
