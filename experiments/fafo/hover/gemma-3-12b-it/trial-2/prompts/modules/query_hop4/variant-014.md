<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a BM25 keyword search query to find a specific Wikipedia article. Output ONLY the query text, nothing else.

User: Claim: ${claim}

Analysis of what was found so far:
${steps.summarize_hop3.output}

Previous queries used:
- Query 1 (from claim): ${claim}
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}

Your task: Look at NEXT TARGET above. Generate a search query (3-8 words) that would find the Wikipedia article for that entity. Try a COMPLETELY DIFFERENT approach from the previous queries.

Rules:
- Output ONLY the search query, no explanation
- Your query MUST be DIFFERENT from ALL previous queries
- Try alternative names, synonyms, or related concepts for the target
- If previous queries failed to find the target, try a broader or narrower variant of the entity name
- Consider that Wikipedia titles often include disambiguation like "(film)", "(musician)", etc.
