<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Generate the THIRD and final search query for multi-hop claim verification.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}
Hop 2 findings: ${steps.summarize_hop2.output}

You already searched for "${steps.query_hop2.output}" in hop 2. Now find the LAST missing entity.

- Check MISSING above — if it names a real person/place/work, use that
- If the claim describes someone indirectly (e.g., "the star of X"), look in PEOPLE/ENTITIES IN PASSAGES for their actual name
- Do NOT repeat any title already found or the hop 2 query

Output ONLY the entity name (1-5 words):
