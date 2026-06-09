<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: FINAL search attempt. Generate queries for the last missing entity using INFERENCE and LATERAL THINKING. After three rounds, the missing entity is almost certainly referenced indirectly in the claim.

Strategy — think step by step:
1. What does the claim say about the missing entity? (its role, relationship, property)
2. What facts have you gathered that narrow down what it could be?
3. What is your BEST GUESS for the actual Wikipedia article title?
4. Generate queries for that guess AND for related/nearby entities

Query approaches:
- Your #1 query should be your best guess for the exact article title
- Try the entity with different disambiguation: (film), (TV series), (band), (album), (novel)
- Try related entities that would link to it (e.g., if missing a film, try its director or studio)
- Try category/list pages: "List of films by X", "X discography", "X filmography"
- Try parent entities: the broader topic/organization/series it belongs to
- If a person, try: full name, last name only, stage name, birth name

Rules:
- Output exactly 12 search queries, one per line
- Each query should be a plausible Wikipedia article title (1-8 words)
- First 4 queries: your best guesses for the exact missing entity
- Next 4 queries: related entities that would link to it
- Last 4 queries: creative alternates (categories, lists, broader topics)
- Do NOT output numbering, bullets, explanations, or anything else
- Never output "N/A" or empty lines

User: Claim: ${claim}

First analysis: ${steps.summarize_hop1.output}
Second analysis: ${steps.summarize_hop2.output}
Third analysis: ${steps.summarize_hop3.output}

Output 12 queries — your best inferences for the missing entity:
