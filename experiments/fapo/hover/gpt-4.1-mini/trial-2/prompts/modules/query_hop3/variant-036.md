<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Generate the THIRD and final search query for multi-hop claim verification.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}
Hop 2 findings: ${steps.summarize_hop2.output}

Previous search (hop 2): "${steps.query_hop2.output}"

Find the LAST missing entity needed to verify this claim.

- Check which proper nouns from the claim are NOT yet in TITLES FOUND
- If the claim uses an indirect reference (e.g., "the star of X"), use KEY FACTS to resolve it to the actual name
- Do NOT repeat any title already found or "${steps.query_hop2.output}"
- Pick the MOST IMPORTANT remaining entity for verifying the claim

Output ONLY the entity name (1-5 words):
