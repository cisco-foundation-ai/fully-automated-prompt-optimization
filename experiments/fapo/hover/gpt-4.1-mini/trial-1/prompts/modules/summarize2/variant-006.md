<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles via keyword search. Analyze new passages given prior context and extract every possible article title.

User: Claim: ${claim}

Prior analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Instructions:
1. Briefly state what new information these passages provide (2-3 sentences).
2. List ALL potential Wikipedia article titles you can identify from the new passages. Include:
   - Every person, place, organization, creative work, or event explicitly named
   - Entities DESCRIBED but not named (e.g., "the studio that produced X" → name the studio if you can identify it)
   - Parent/child entities (parent companies, directors, creators, related works)
   - Any entity from the claim that still hasn't been directly retrieved

List each on its own line as:
ENTITY: <exact Wikipedia article title>

Include disambiguation where needed (e.g., "Fargo (TV series)", "Splash (1984 film)"). List at least 10 entities.
