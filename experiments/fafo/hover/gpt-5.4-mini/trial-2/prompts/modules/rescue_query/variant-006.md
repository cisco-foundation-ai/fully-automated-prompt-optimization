<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia articles for multi-hop claim verification. Think carefully about WHICH ARTICLE is missing — not just which entity is mentioned.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Task: The claim makes assertions that require SPECIFIC Wikipedia articles to verify. For each entity or concept in the claim, determine whether its article has been retrieved.

Think step by step:
1. What entities does the claim mention? (people, films, places, events, organizations, albums, species, etc.)
2. What entities are IMPLIED but not named? (e.g., "the film" implies a specific film title, "the city where X was born" implies a specific city)
3. For EACH entity, does the retrieved title list contain its Wikipedia article?
4. Output ALL missing articles, most important first.

Critical rules:
- Think about WORKS (films, albums, books, songs) not just PEOPLE — if the claim says "the film directed by X", the missing article might be the FILM, not the director
- Think about EVENTS and PLACES — if the claim mentions a year, draft, tournament, or location, its article might be needed
- If you know the actual name of an implied entity (e.g., you know which film was directed by that person), output the SPECIFIC TITLE
- Use exact Wikipedia article title format with disambiguators: "The Dark Knight (film)", "2013 NHL Entry Draft", "Cairo"
- Output one query per line — list ALL missing articles you can identify
- For each entity, also output alternative name forms on separate lines (e.g., both "The Fantastic Mr Fox" and "Fantastic Mr. Fox (film)")
- If ALL entities are found, output only: "NONE"
- Do NOT output explanations, just Wikipedia article titles or search queries
