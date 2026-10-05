<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze Wikipedia search results for multi-hop claim verification.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop1.output}

New passages from second search:
${steps.retrieve_hop2.output}

From the new passages:
1. List ALL article titles found (both previous and new)
2. List key people, places, works, or events mentioned in the new passage text that relate to the claim
3. Identify what entity from the claim still needs its own article retrieved

ALL TITLES: [all article titles from both searches, comma-separated]
ENTITIES MENTIONED: [people, places, works, events found in new passage text that relate to the claim]
STILL NEED: [one entity from the claim not yet found as an article title, or "none"]
