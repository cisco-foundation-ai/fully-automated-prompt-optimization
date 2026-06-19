<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia article titles for multi-hop claim verification. You must be thorough — find EVERY entity whose article is missing.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Task: Compare EVERY entity in the claim against the retrieved titles above. An entity is "found" only if there's a title that is clearly about that specific entity.

Rules:
- Output one entity name per line
- Use the exact Wikipedia article title format (e.g., "Kevin Alejandro" not "kevin alejandro")
- Include disambiguators when needed (e.g., "Cassadaga (film)" not just "Cassadaga")
- If an entity in the claim is described indirectly (e.g., "the director of X"), output the actual person's name if you know it, otherwise output a descriptive query like "director of [Film Name]"
- Also check for IMPLICIT entities: if the claim mentions a relationship between entities (e.g., "born in the same city"), there may be a city article needed
- For each missing entity, also output alternative name forms on separate lines (e.g., both "NYC" and "New York City")
- If all entities are found, output only: "NONE"
- Do NOT output explanations, just names
