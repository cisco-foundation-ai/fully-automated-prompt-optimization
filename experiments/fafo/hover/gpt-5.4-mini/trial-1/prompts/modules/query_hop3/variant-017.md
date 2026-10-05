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

Your query should be the entity's Wikipedia article title with disambiguation if needed: (film), (TV series), (band), (book), (album), (song). Keep it to 2-6 words.

Do NOT search for an entity that already appears as a retrieved article title above. Do NOT include the words Wikipedia, article, or page. Output ONLY the search query. Never output placeholder text like {claim}.
