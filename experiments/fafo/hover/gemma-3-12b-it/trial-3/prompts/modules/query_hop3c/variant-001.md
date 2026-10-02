<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words) for the entity still missing from the claim. Use a completely different approach than both previous queries. Never output "N/A".

User: Claim: ${claim}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

Neither query found the missing entity. Try a COMPLETELY DIFFERENT proper noun, title, or name from the claim. Or try a synonym or alternate name. Output just the query, nothing else.
