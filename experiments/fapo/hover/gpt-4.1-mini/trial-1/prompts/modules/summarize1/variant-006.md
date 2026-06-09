<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles via keyword search. Your job is to extract every possible Wikipedia article title from the retrieved passages.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Instructions:
1. Briefly state what the passages reveal about the claim (2-3 sentences).
2. List ALL potential Wikipedia article titles you can identify. Include:
   - Every person, place, organization, creative work, or event explicitly named in the passages
   - Entities DESCRIBED but not named (e.g., "the director of X" → name them if you can identify who it is)
   - Parent/child entities (e.g., if a band is mentioned, also list their notable albums; if a subsidiary is mentioned, list the parent company)
   - Entities from the claim itself that haven't been retrieved yet

List each on its own line as:
ENTITY: <exact Wikipedia article title>

Include disambiguation where needed (e.g., "Fargo (TV series)", "Splash (1984 film)"). List at least 10 entities. More is better — the search system will filter irrelevant ones.
