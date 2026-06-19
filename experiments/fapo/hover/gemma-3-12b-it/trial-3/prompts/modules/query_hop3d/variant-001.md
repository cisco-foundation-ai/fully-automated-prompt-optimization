<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words). Use a proper noun from the passages that answers the description in the claim. Never output "N/A".

User: Claim: ${claim}

Passages found so far mention these topics:
${steps.summarize_hop1.output}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}
3. ${steps.query_hop3c.output}

The claim describes an entity. Look at the passages — what proper noun (person, place, film, organization) is described by the claim but hasn't been searched yet? Output just the name.
