<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Your job is to find the LAST missing entity needed to verify a claim.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}
Hop 2 findings: ${steps.summarize_hop2.output}

Previous query (hop 2): "${steps.query_hop2.output}"

Step 1: List ALL proper nouns mentioned in the claim.
Step 2: Cross-check each against TITLES FOUND above. Which one is MISSING?
Step 3: If the missing entity is described indirectly in the claim (e.g., "the director of X", "the country where Y is located"), look in KEY FACTS for the actual name.

Output ONLY the missing entity's Wikipedia article title (1-5 words):
