<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a single search query to find a Wikipedia article that has NOT yet been retrieved. Output ONLY the query text, nothing else.

User: Claim: ${claim}

What has been found and what is still missing:
${steps.summarize_hop2.output}

Above is the analysis showing which articles have been found (under FOUND TITLES) and which entity is still missing (under MISSING ENTITY). Generate a search query for the MISSING ENTITY's Wikipedia article.

Your query must be:
- The entity's Wikipedia article title (2-6 words)
- Include disambiguation when needed: (film), (TV series), (band), (book), (album), (song)
- NEVER include: Wikipedia, article, page, encyclopedia, about
- NEVER search for an entity listed under FOUND TITLES

Output ONLY the search query. Never output placeholder text like {claim}.
