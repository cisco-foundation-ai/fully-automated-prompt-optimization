<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: This is the FINAL search attempt. Generate Wikipedia search queries for the last missing entities using every possible approach. After three retrieval rounds, any remaining entities are hard to find — use creative alternate queries.

Strategy:
- Try completely different name forms than previous rounds
- Use related entities (directors, producers, locations) that link to the missing title
- Try disambiguation variants: "(film)", "(TV series)", "(song)", "(album)", "(city)", "(band)"
- Try partial names, nicknames, maiden names, translated names
- If an entity type is known but not found, try the category (e.g., "List of films by X")

Rules:
- Output exactly 10 search queries, one per line
- Each query should be a plausible Wikipedia article title (1-8 words)
- Do NOT output numbering, bullets, explanations, or anything else
- Never output "N/A" or empty lines — always generate 10 queries

User: Claim: ${claim}

First analysis: ${steps.summarize_hop1.output}
Second analysis: ${steps.summarize_hop2.output}
Third analysis: ${steps.summarize_hop3.output}

Output 10 creative alternate queries for the STILL NEEDED entities:
