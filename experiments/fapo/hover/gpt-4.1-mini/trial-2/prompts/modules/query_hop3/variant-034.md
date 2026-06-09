<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for multi-hop fact verification.

User: Claim: ${claim}

What we've found so far:
${steps.summarize_hop1.output}
${steps.summarize_hop2.output}

Previous search: "${steps.query_hop2.output}"

Task: Find the ONE entity still missing. Think about what the claim is asking you to verify — which Wikipedia article would let you confirm or deny it?

Rules:
- Do NOT output any entity already in TITLES FOUND
- Do NOT repeat "${steps.query_hop2.output}"
- If the claim uses an indirect description like "the lead actor of [Movie]" or "the city where [Event] took place", look at KEY FACTS to resolve it to a proper name

Entity name:
