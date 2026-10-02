<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words). Your goal: find the Wikipedia article for an entity that was DESCRIBED but not NAMED in the claim. Think about what role or relationship is implied. Never output "N/A".

User: Claim: ${claim}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

The missing entity is probably described by a phrase like "the director of...", "the country where...", "the team that...". Think about WHAT that entity actually IS (its proper name), not how it's described. Output just the proper name as a query.
