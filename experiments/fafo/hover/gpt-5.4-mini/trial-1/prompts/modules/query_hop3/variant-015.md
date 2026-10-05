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

Analysis of what was found: ${steps.summarize_hop2.output}

The claim involves multiple Wikipedia articles. Some have already been retrieved above. Identify the entity from the claim whose Wikipedia article is NOT yet among those retrieved. Generate a search query containing that entity's exact name.

BAD queries (do NOT do this):
- "Splash Wikipedia article" ← contains forbidden words
- "David Thewlis Wonder Woman Anomalisa Fargo premiere date Wikipedia" ← too many words, contains forbidden words
- "Michael Jackson" ← too vague, already retrieved

GOOD queries (do this):
- "Splash (film)"
- "Fargo (TV series)"
- "Moonwalk (book)"
- "Cell (American band)"

Rules:
- 2-6 words maximum
- Use Wikipedia article title format with disambiguation: (film), (band), (TV series), (book), (album)
- NEVER include: Wikipedia, article, page, encyclopedia, about
- Do NOT search for an entity that already appears as a retrieved article title above
- Never output placeholder text like {claim}

Output ONLY the search query.
