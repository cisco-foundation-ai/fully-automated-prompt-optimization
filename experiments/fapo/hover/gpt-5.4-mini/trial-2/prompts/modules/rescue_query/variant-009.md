<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia articles for multi-hop claim verification. Your job is to find articles whose exact TITLE is not in the retrieved list — even if a RELATED article exists.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Facts and relationships discovered during retrieval:
${steps.summarize_hop3.output}

Task: The claim requires SPECIFIC Wikipedia articles. For each entity in the claim, the MAIN article about that entity must be in the title list above. Related articles DO NOT count.

CRITICAL DISTINCTION — these are DIFFERENT articles:
- "Fargo (TV series)" ≠ "Fargo (season 3)" — season page is NOT the series page
- "Michael Jackson" ≠ "Michael Jackson's This Is It" — an album page is NOT the person's page
- "Lily Allen" ≠ "Lily Allen discography" — the discography is a separate article
- "Computer security" ≠ "Computer security incident management" — a subfield is NOT the main topic

Think step by step:
1. List ALL entities the claim mentions or implies (people, places, events, works, concepts).
2. For each entity, determine what its MAIN Wikipedia article title would be.
3. Check EXACTLY: is that EXACT title (not a variant, season, album, or subpage) in the list?
4. Use the facts section to resolve indirect references ("the director of X" → actual name).
5. Output every entity whose MAIN article title is NOT exactly in the list.

Rules:
- A related article (season, album, episode, subcategory) does NOT satisfy the need for the main article
- Output exact Wikipedia article titles with disambiguators when appropriate
- One query per line, most important first (up to 10 lines)
- For each entity, also output alternative name forms on separate lines
- If truly ALL needed MAIN titles are in the list, output only: "NONE"
- Do NOT output explanations, just Wikipedia article titles or search queries
