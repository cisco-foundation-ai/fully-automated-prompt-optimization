<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: ABSOLUTE FINAL search attempt (hop 5 of 5). The remaining entity has resisted 4 rounds of search. Use MAXIMUM creativity and lateral thinking.

You MUST try fundamentally different approaches from all previous rounds:
1. If you've been searching by entity name, try searching by CONTEXT (events, works, places associated with it)
2. If you've been searching specific names, try BROADER CATEGORIES (lists, filmographies, discographies)
3. Try the entity's ALTERNATE IDENTITIES: pen names, stage names, married names, translated names
4. Try RELATED WORKS or EVENTS that would mention this entity in their Wikipedia article
5. Try the entity with EVERY disambiguation you can think of
6. Try just a SINGLE WORD from the entity name — sometimes BM25 matches better on partial queries

Rules:
- Output exactly 15 search queries, one per line
- Each query should be a plausible Wikipedia article title or category (1-8 words)
- NONE of these queries should repeat previous attempts
- First 5: your top guesses for the exact article title (with various disambiguation)
- Next 5: related entities whose Wikipedia articles would MENTION the missing one
- Last 5: category pages, list pages, or single-word/partial-name variants
- Do NOT output numbering, bullets, explanations, or anything else
- Never output "N/A" or empty lines

User: Claim: ${claim}

First analysis: ${steps.summarize_hop1.output}
Second analysis: ${steps.summarize_hop2.output}
Third analysis: ${steps.summarize_hop3.output}
Fourth analysis: ${steps.summarize_hop4.output}

Output 15 maximally creative queries — this is your LAST CHANCE to find the missing entity:
