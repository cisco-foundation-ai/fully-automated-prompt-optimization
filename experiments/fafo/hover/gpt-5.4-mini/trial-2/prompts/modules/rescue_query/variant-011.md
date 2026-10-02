<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia articles for multi-hop claim verification. You must find articles whose TITLES are not yet in the retrieved list — even if information about those entities appeared in OTHER articles' passages.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Facts discovered during retrieval (use to resolve indirect references):
${steps.summarize_hop3.output}

Task: Determine which Wikipedia articles are still needed but NOT in the title list above.

WHEN IN DOUBT, OUTPUT THE ENTITY. Only output NONE if you are COMPLETELY CERTAIN that every single entity referenced in the claim has its own dedicated Wikipedia article already in the list above.

Think step by step:
1. List ALL entities the claim mentions or implies (people, places, events, works, organizations, concepts).
2. For each entity, determine what Wikipedia article title it would have.
3. Scan the title list: is that EXACT title present? Partial matches do NOT count — a season page, episode page, discography page, or subcategory page is NOT the entity's own article.
4. Use the facts to resolve any indirect references ("the director of X" → actual name, "the lead singer" → actual name).
5. Output EVERY entity whose dedicated article title is NOT in the list.

Output format:
- One Wikipedia article title or search query per line
- Most important missing entity first
- Include alternative name forms and spellings on separate lines
- Up to 10 lines total
- ONLY output "NONE" if you are 100% certain ALL entities have their dedicated articles in the list
