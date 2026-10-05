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

Articles already retrieved in hop 3:
${steps.retrieve_hop3.output}

The claim involves multiple Wikipedia articles. Some have already been retrieved above. If there is still an entity from the claim whose Wikipedia article is NOT among those retrieved, generate a different search query for it. Try an alternative name, abbreviation, or description.

Format: [Alternative name or description of the entity] (3-8 words)

FORBIDDEN words: Wikipedia, article, page, encyclopedia, about, information.
Do NOT repeat the same query used before.
Output ONLY the search query. Never output placeholder text like {claim}.
