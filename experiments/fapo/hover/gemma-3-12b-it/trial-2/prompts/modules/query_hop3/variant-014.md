<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a BM25 keyword search query to find a specific Wikipedia article. Output ONLY the query text, nothing else.

User: Claim: ${claim}

Analysis of what was found so far:
${steps.summarize_hop2.output}

Previous queries used:
- Query 1 (from claim): ${claim}
- Query 2: ${steps.query_hop2.output}

Your task: Look at NEXT TARGET above. Generate a search query (3-8 words) that would find the Wikipedia article for that specific entity.

Rules:
- Output ONLY the search query, no explanation
- Your query MUST be DIFFERENT from the previous queries listed above
- Use proper nouns and specific names from the NEXT TARGET
- Do NOT repeat previous query words
- If NEXT TARGET says a person's name, search for that exact name
- If NEXT TARGET names a work or event, use its exact title
