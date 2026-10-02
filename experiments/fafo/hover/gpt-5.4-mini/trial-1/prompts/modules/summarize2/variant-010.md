<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an information extraction assistant. Your job is to extract facts from new passages AND produce an explicit list of Wikipedia article titles already found across all retrievals.

User: Claim: ${claim}

Prior findings: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Instructions:
1. Extract relevant facts from the new passages. Note article titles and key information.
2. Then produce a complete list of all Wikipedia article titles that have been successfully retrieved so far (from BOTH the first retrieval and this second retrieval). Format as:

FOUND TITLES:
- [exact title 1]
- [exact title 2]
- ...

3. Now re-read the claim. Identify every entity, work, or topic in the claim that should have its own Wikipedia article. Check which one is NOT in your FOUND TITLES list.

MISSING ENTITY: [the exact name as it would appear as a Wikipedia article title, including disambiguation like (film), (TV series), (band), (book), (album) if applicable]

If all entities are found, write: MISSING ENTITY: none
