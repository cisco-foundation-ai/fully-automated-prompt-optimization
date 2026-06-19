<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words) for the entity still missing from the claim. Look for proper nouns mentioned in the passages below that could be the missing entity. Never output "N/A".

User: Claim: ${claim}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

Passages from previous searches:
${steps.retrieve_hop3.output}

Scan the passages above for a proper noun that names the entity described in the claim but not yet found as a Wikipedia article title. Output that name as your search query (1-5 words).
