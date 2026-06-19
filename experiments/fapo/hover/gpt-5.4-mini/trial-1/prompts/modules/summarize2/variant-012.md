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

3. Now list every distinct entity or topic explicitly mentioned in the claim:

CLAIM ENTITIES:
- [entity 1]
- [entity 2]
- [entity 3]
- ...

4. Cross-reference FOUND TITLES against CLAIM ENTITIES. State which entity still has NO matching article:

MISSING ENTITY: [the entity whose Wikipedia article is not yet among FOUND TITLES]
