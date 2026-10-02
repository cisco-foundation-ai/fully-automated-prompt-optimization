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

TASK: Find the ONE Wikipedia article still needed to verify this claim.

Step 1 (internal): List every distinct entity/topic in the claim.
Step 2 (internal): Cross-check each against the retrieved article titles above. Identify which entity has NO matching article.
Step 3: Output a search query for that missing entity.

Format: [Entity's proper name] [1-2 distinguishing words]
Examples: "Splash 1984 film", "Fargo TV series", "Moonwalk Michael Jackson book"

RULES:
- NEVER search for an entity that already appears as a retrieved article title
- NEVER use these words: Wikipedia, article, page, encyclopedia, about, information
- Output ONLY the search query (3-6 words)
- Never output placeholder text like {claim}
