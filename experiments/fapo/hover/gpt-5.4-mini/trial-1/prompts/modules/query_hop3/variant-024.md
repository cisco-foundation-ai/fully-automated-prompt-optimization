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

The claim involves multiple Wikipedia articles. Some have already been retrieved above. Identify the entity from the claim whose Wikipedia article is NOT yet among those retrieved. Generate a search query that would match the TITLE of that entity's Wikipedia article.

Format your query as: [Entity Name] ([disambiguation])
Examples of good queries: "Splash (film)", "Fargo (TV series)", "Moonwalk (book)", "Cell (band)"

Think about what the exact Wikipedia article title would be. Wikipedia titles use the entity's most common name followed by a disambiguation in parentheses if needed.

FORBIDDEN words in your query: Wikipedia, article, page, encyclopedia, about, information.
Do NOT search for an entity that already appears as a retrieved article title above.
Output ONLY the search query (3-6 words). Never output placeholder text like {claim}.
