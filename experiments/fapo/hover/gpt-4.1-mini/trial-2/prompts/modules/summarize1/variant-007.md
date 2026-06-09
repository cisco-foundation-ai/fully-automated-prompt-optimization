<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze Wikipedia search results for multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

From the retrieved passages:
1. List the article titles
2. List key people, places, works, or events mentioned IN the passage text that relate to the claim
3. Identify what entity from the claim still needs its own article retrieved

TITLES: [article titles, comma-separated]
ENTITIES MENTIONED: [people, places, works, events found in passage text that relate to the claim]
STILL NEED: [one entity from the claim not yet found as an article title]
