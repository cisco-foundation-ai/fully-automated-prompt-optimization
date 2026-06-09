<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Given a claim and what has already been retrieved in two hops, find the ONE remaining entity from the claim. Output ONLY its name.

User: Claim: ${claim}

Hop 1 found: ${steps.summarize_hop1.output}

Hop 2 searched for "${steps.query_hop2.output}" and found: ${steps.summarize_hop2.output}

Rules:
- Output one entity name (1-5 words) that is referenced in the claim
- It must NOT be in TITLES FOUND or ALL TITLES above
- It must NOT be "${steps.query_hop2.output}" or similar
- If described indirectly in the claim, use facts from the passages to determine the actual name

Entity name:
