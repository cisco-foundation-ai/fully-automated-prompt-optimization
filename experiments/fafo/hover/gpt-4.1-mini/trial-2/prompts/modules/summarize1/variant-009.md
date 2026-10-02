<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract information from Wikipedia search results for multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

From the retrieved passages:
1. List the article titles found
2. Note any entities mentioned in the claim that are described indirectly (e.g., "the director of X", "the star of Y") — if the passages reveal who that entity is, state their name
3. Identify what entity from the claim still needs its own article retrieved

TITLES FOUND: [article titles from passages, comma-separated]
KEY FACTS: [facts from passages relevant to the claim, including resolved indirect references — e.g., "the director of X is John Smith"]
MISSING: [one entity/person/event from the claim not yet found as an article title]
