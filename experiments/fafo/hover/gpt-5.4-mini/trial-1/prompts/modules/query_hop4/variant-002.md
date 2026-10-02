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

The claim involves multiple Wikipedia articles. Some have already been retrieved above. Identify the entity from the claim whose Wikipedia article is NOT yet among those retrieved.

Previous search attempt: ${steps.query_hop3.output}

That search did not find the right article. Try a DIFFERENT query:
- Use a different spelling, abbreviation, or alternate name for the entity
- Or describe what the entity IS rather than its name (e.g., "1984 romantic comedy mermaid" instead of "Splash film")
- Do NOT repeat the previous query above

Format your query as: [Entity Name] ([disambiguation])
FORBIDDEN words: Wikipedia, article, page, encyclopedia, about, information.
Output ONLY the search query (3-8 words). Never output placeholder text like {claim}.
