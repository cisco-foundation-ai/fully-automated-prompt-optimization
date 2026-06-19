<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia articles for multi-hop claim verification. You must find articles whose TITLES are not yet in the retrieved list — even if information about those entities appeared in OTHER articles' passages.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Facts and relationships discovered during retrieval:
${steps.summarize_hop3.output}

Task: The claim requires SPECIFIC Wikipedia articles to verify. An article is MISSING if its exact title does not appear in the retrieved title list above — even if the entity was mentioned inside another article's passage.

IMPORTANT: The title list above is what matters. If the facts section mentions "Craig Nicholls" as found, but "Craig Nicholls" is NOT in the title list, then you STILL NEED to search for "Craig Nicholls".

ALSO IMPORTANT: A season page (e.g., "Fargo (season 3)") is NOT the same as the main series page ("Fargo (TV series)"). An album page is NOT the person's page. A subcategory is NOT the main category. Check for the MAIN article about each entity.

Think step by step:
1. What entities does the claim mention or IMPLY? List them ALL.
2. For EACH entity, check: is its MAIN Wikipedia article title in the list above? Be exact.
3. Use the facts section to identify proper names of IMPLICIT entities (e.g., if facts say "the director is X", you need X's article).
4. Output every entity whose main article title is NOT in the retrieved list.

Rules:
- Check the TITLE LIST, not the facts section, to determine what's missing
- Use facts/relationships to RESOLVE indirect references to proper names
- Output exact Wikipedia article titles with disambiguators when appropriate
- One query per line, most important first (up to 12 lines)
- For each entity, also output alternative name forms on separate lines
- If truly ALL needed main articles are in the list, output only: "NONE"
- Do NOT output explanations, just Wikipedia article titles or search queries
