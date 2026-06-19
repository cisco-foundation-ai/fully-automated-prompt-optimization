<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a single search query to find a specific Wikipedia article. Output ONLY the query text, nothing else.

User: Claim: ${claim}

Analysis of what has been found and what is missing:
${steps.summarize_hop2.output}

The analysis above identifies a MISSING ARTICLE. Your job is to produce an effective BM25 search query for that missing article.

Rules:
- Read the MISSING ARTICLE line from the analysis above
- Output a query that is the entity's Wikipedia article title (e.g., "Splash (film)" or "Fargo (TV series)" or "Moonwalk (book)")
- If the missing article has a disambiguation suffix, INCLUDE it: (film), (band), (TV series), (book), (album), (song), etc.
- Keep the query short: just the article title, 2-6 words maximum
- Do NOT include extra keywords like "Wikipedia" or "article"
- Do NOT repeat entities that are already found
- Never output placeholder text like {claim}

Output ONLY the search query.
