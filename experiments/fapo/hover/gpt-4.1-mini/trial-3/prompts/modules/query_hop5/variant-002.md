<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: ABSOLUTE FINAL search attempt (hop 5 of 5). The remaining entity has resisted 4 rounds of search. You MUST use completely different strategies from all previous rounds.

MANDATORY REASONING STEP (do this internally before generating queries):
1. What does the claim say about the missing entity?
2. What specific facts from your analyses narrow down what it could be?
3. What is your SINGLE BEST GUESS for the Wikipedia article title?
4. What are 5 alternate names or disambiguation forms for that guess?
5. What articles would LINK TO the missing entity?

Query strategies — you MUST try ALL of these approaches:
- Your best guess with every disambiguation: (film), (TV series), (band), (album), (song), (person), (footballer)
- The entity's ALTERNATE IDENTITIES: stage name, birth name, married name, nickname, abbreviation
- RELATED WORKS: films, albums, TV shows that would mention this entity
- RELATED PEOPLE: collaborators, family, co-stars whose articles mention the missing entity
- CATEGORY PAGES: "List of...", "...discography", "...filmography"
- SINGLE WORD queries from the entity name (BM25 sometimes matches better on fragments)
- BROADER TOPIC queries that contain the entity as a subtopic

Rules:
- Output exactly 20 search queries, one per line
- Each query should be a plausible Wikipedia article title (1-8 words)
- NONE of these queries should repeat previous attempts
- Queries 1-5: your top guesses for the exact article title (with disambiguation variants)
- Queries 6-10: related entities whose articles MENTION the missing entity
- Queries 11-15: category/list pages and broader topics
- Queries 16-20: single words, fragments, and creative alternates
- Do NOT output numbering, bullets, explanations, or anything else
- Never output "N/A" or empty lines

User: Claim: ${claim}

First analysis: ${steps.summarize_hop1.output}
Second analysis: ${steps.summarize_hop2.output}
Third analysis: ${steps.summarize_hop3.output}
Fourth analysis: ${steps.summarize_hop4.output}

Output 20 maximally diverse queries — your LAST CHANCE:
