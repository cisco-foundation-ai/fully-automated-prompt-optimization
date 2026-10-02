<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia articles for multi-hop claim verification. You receive both the titles already retrieved AND the knowledge discovered during retrieval. Use both to deduce which specific articles are still needed.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Knowledge gathered during retrieval:
${steps.summarize_hop3.output}

Task: The claim makes assertions that require SPECIFIC Wikipedia articles to verify. Some of these articles may be entities that are NAMED in the knowledge above but whose articles were never retrieved. Others may require reasoning about relationships between found entities.

Think step by step:
1. What entities does the claim mention or IMPLY? (people, films, places, events, organizations, albums, species, songs, etc.)
2. From the knowledge gathered, what entity names were RESOLVED from indirect references? (e.g., "the brother-in-law of X is Y" means you need Y's article)
3. What BRIDGING entities connect two found entities but are not themselves retrieved? (e.g., if a film connects an actor to a director, you need the film's article)
4. For EACH entity — is its Wikipedia article in the title list above? Be exact: "Suncoast Casino" is NOT the same article as "Suncoast Hotel and Casino".
5. Output ALL missing articles, most important first.

Critical rules:
- MINE THE KNOWLEDGE SECTION: if it names a person, place, film, or event that is relevant to the claim, CHECK whether that exact title is in the retrieved list. If not, output it.
- Think about WORKS (films, albums, books, songs) — if the claim mentions "the film" or "a movie", the knowledge section may name it.
- Think about RELATIONSHIPS — brother-in-law, co-star, director, team member, replacement, predecessor/successor.
- Think about CATEGORIES — if the claim says "a genus containing X", and the knowledge says X is found in genus Y, you need Y's article.
- Use exact Wikipedia article title format with disambiguators: "The Dark Knight (film)", "2013 NHL Entry Draft", "Suncoast Hotel and Casino"
- Output one query per line — list ALL missing articles you can identify (up to 8)
- For each entity, also output alternative name forms on separate lines
- If ALL entities are found, output only: "NONE"
- Do NOT output explanations, just Wikipedia article titles or search queries
