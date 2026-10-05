<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify a missing Wikipedia article and output a search query for it. Output ONLY the query, nothing else.

User: Claim: ${claim}

ALREADY RETRIEVED ARTICLE TITLES (do NOT search for any of these):
${steps.summarize_hop2.output}

The claim references multiple Wikipedia articles. The titles listed above have ALREADY been found. Your task: identify which entity from the claim is NOT among the already-retrieved titles, then output a search query for that entity's Wikipedia article.

Rules:
- Do NOT output a title that appears in the ALREADY RETRIEVED list above
- Output the missing entity's full name as it would appear on Wikipedia
- For people: full name (e.g., "Kevin Alejandro")
- For films: title with year disambiguation (e.g., "Splash (film)")
- For disambiguation: include the qualifier (e.g., "Fargo (TV series)")

Output ONLY the search query. Never output placeholder text like {claim}.
