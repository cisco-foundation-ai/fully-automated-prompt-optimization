<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a single search query to find a Wikipedia article that has NOT yet been retrieved. Output ONLY the query text, nothing else.

User: Claim: ${claim}

Articles already retrieved in hop 1:
${steps.retrieve_hop1.output}

Articles already retrieved in hop 2:
${steps.retrieve_hop2.output}

Analysis of what was found and what is missing: ${steps.summarize_hop2.output}

Look at the MISSING ENTITY identified above. Generate a search query for that entity's Wikipedia article.

STRICT RULES:
- Output 3-6 words only
- Use the entity's proper name exactly as Wikipedia would title the article
- Include disambiguation in parentheses when needed: (film), (band), (TV series), (book), (album), (song)
- NEVER include the words "Wikipedia", "article", "page", or "encyclopedia"
- NEVER search for an entity whose article title already appears in the retrieved passages above
- If summarize says the missing entity is a film, add "(film)" after the title
- If summarize says the missing entity is a band or musician, add "(band)" or the instrument/genre

Output ONLY the search query.
