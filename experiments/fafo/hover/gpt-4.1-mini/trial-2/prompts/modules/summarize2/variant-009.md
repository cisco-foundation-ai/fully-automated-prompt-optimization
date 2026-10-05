<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract information from Wikipedia search results for multi-hop claim verification.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

From all information gathered:
1. List ALL article titles found (both previous and new)
2. Note any entities mentioned in the claim that are described indirectly — if the passages reveal who that entity is, state their name
3. Identify what entity from the claim still needs its own article retrieved

ALL TITLES: [all article titles from both searches, comma-separated]
KEY FACTS: [new facts from passages, including resolved indirect references]
MISSING: [one entity from the claim not yet found as an article title, or "none"]
