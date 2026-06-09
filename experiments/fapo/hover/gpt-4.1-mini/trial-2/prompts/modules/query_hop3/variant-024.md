<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You find a missing Wikipedia article for claim verification. Two searches have been done. Read the claim and passage facts carefully to determine what entity is still missing.

User: Claim: ${claim}

Hop 1 titles and facts:
${steps.summarize_hop1.output}

Hop 2 titles and facts:
${steps.summarize_hop2.output}

The claim connects multiple entities. Two have been found. The third is either:
- A proper noun in the claim not yet in any title above, OR
- A person/thing referenced INDIRECTLY in the claim (e.g., "the star of X") whose name appears in the KEY FACTS above

Read the KEY FACTS — if they mention a person, place, or work that the claim refers to indirectly, that is your answer.

Output ONLY the entity name (1-5 words):
