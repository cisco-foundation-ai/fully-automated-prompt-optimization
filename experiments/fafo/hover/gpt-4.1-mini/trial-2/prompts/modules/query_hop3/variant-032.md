<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Generate the THIRD and final search query for multi-hop claim verification.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}
Hop 2 findings: ${steps.summarize_hop2.output}

You already searched for "${steps.query_hop2.output}" in hop 2. Now find the LAST missing entity.

Instructions:
- Look at proper nouns in the claim not yet in TITLES FOUND above
- If the claim refers to someone indirectly (e.g., "the star of X"), use the KEY FACTS above to find their actual name
- Do NOT repeat "${steps.query_hop2.output}" or any title already found
- Output must be a real entity name, not a variable or placeholder

Search query (1-5 words, entity name only):
