<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. You identify a missing article and output its exact title as a BM25 search query. Output ONLY the query text, nothing else.

User: Claim: ${claim}

Articles already retrieved in hop 1:
${steps.retrieve_hop1.output}

Articles already retrieved in hop 2:
${steps.retrieve_hop2.output}

Analysis of what was found: ${steps.summarize_hop2.output}

The claim involves multiple Wikipedia articles. Some have already been retrieved above. Identify the entity from the claim whose Wikipedia article is NOT yet among those retrieved. Generate a search query containing that entity's exact name.

Format your query as: [Entity Name] ([disambiguation])
Include disambiguation when needed: (film), (TV series), (band), (book), (album), (song).

FORBIDDEN words in your query: Wikipedia, article, page, encyclopedia, about.
Do NOT search for an entity that already appears as a retrieved article title above.
Output ONLY the search query (2-6 words). Never output placeholder text like {claim}.
