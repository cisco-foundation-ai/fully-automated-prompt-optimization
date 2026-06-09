<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words). Pick from the extracted entity names below — choose one that has NOT been retrieved as its own article yet. Never output "N/A".

User: Claim: ${claim}

Entity names found in passages:
${steps.extract_entities.output}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

Pick ONE entity name from the list above that is DIFFERENT from the previous queries. This entity should be one whose Wikipedia article would help verify the claim. Output just the name, nothing else.
