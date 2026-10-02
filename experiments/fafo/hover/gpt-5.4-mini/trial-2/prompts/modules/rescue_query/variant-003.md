<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia article titles for multi-hop claim verification. Output ONLY the exact proper names of entities whose articles are missing — one per line, nothing else.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Task: Compare each entity in the claim against the retrieved titles. Output the proper name of each entity whose Wikipedia article is NOT in the list above.

Rules:
- Output one entity name per line
- Use the exact Wikipedia article title format (e.g., "Kevin Alejandro" not "kevin alejandro")
- Include disambiguators when needed (e.g., "Cassadaga (film)" not just "Cassadaga")
- If an entity in the claim is described indirectly (e.g., "the director of X"), output the actual person's name if you know it
- If all entities are found, output only: "NONE"
- Do NOT output explanations, just names
