<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze retrieved Wikipedia passages to identify entities needed to verify a multi-hop claim. Your critical job is to figure out WHAT ENTITIES THE CLAIM IMPLIES but does not name directly.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Analyze the claim and passages. For each entity mentioned or implied in the claim, determine if it was found. Pay special attention to INDIRECT references — the claim may describe an entity by its relationship to another entity without naming it.

Output exactly this format:

FOUND ENTITIES: [list the specific Wikipedia article titles found in the passages that are relevant to the claim]
KEY FACTS: [2-3 crucial facts that reveal relationships between entities — especially facts that help identify unnamed entities in the claim]
STILL NEEDED: [list specific entity names or Wikipedia article titles that the claim references (directly or indirectly) but were NOT found. For indirect references, write your best guess of the actual entity name based on the facts you found. For example, if the claim says "the director of Film X" and you found Film X was directed by Person Y, write "Person Y" not "the director of Film X"]
