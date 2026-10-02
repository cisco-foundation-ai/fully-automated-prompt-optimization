<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a BM25 keyword search query to find a specific Wikipedia article. Output ONLY the query text, nothing else.

User: Claim: ${claim}

Analysis of what was found so far:
${steps.summarize_hop1.output}

Your task: Look at NEXT TARGET above. Generate a search query (3-8 words) that would find the Wikipedia article for that specific entity. Use the entity's proper name exactly as it would appear as a Wikipedia article title.

Rules:
- Output ONLY the search query, no explanation
- Use proper nouns and specific names
- Do NOT use generic terms like "filmography" or "director of"
- If NEXT TARGET names a person, use their full name
- If NEXT TARGET names a work, use the work's exact title
