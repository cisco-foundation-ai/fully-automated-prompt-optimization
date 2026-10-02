<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze retrieved passages to identify entities STILL MISSING for claim verification. After two retrieval rounds, focus on RESOLVING indirect references — use facts already found to INFER the identity of unnamed entities.

User: Claim: ${claim}

Prior analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Combine all evidence. For any entity the claim references indirectly, use the facts you now have to determine its likely identity. If the claim says "the X that did Y" and you now know what X did Y, name that entity specifically.

Output exactly this format:

FOUND ENTITIES: [list ALL Wikipedia article titles found across BOTH rounds relevant to the claim]
KEY FACTS: [2-3 facts from the new passages — especially any that REVEAL the identity of previously unknown entities]
STILL NEEDED: [list SPECIFIC entity names you still need. Use your best inference — write actual names, not descriptions. If you believe the missing entity is "Marcel Duchamp" based on clues, write "Marcel Duchamp" not "the artist who made X". Write "None" if all entities are found]
