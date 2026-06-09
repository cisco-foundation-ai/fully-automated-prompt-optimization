<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Generate the THIRD and final search query for multi-hop claim verification. Think step by step before answering.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}
Hop 2 findings: ${steps.summarize_hop2.output}

You already searched for "${steps.query_hop2.output}" in hop 2.

Think step by step:
1. List every proper noun and described entity in the claim
2. Cross-check each against TITLES FOUND in hops 1 and 2
3. For any entity described indirectly (e.g., "the star of X", "the director of Y"), look in KEY FACTS for their actual name
4. The entity you still need is the one not yet found

Reasoning:
[your step-by-step reasoning here]

FINAL QUERY:
[output ONLY the entity name, 1-5 words]
