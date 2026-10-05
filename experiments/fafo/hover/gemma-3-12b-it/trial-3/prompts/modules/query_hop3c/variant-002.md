<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words) for the entity still missing from the claim. Look for a proper noun that is DESCRIBED but not named in the claim. Never output "N/A".

User: Claim: ${claim}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

The missing entity might be described in the claim without being named directly. Think about what person, place, work, or event the claim describes but doesn't name. Output your best guess for that entity's name (1-5 words).
