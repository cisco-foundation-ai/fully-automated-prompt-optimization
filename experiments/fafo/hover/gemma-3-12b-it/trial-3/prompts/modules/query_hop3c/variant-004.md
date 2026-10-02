<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words). Look at the names and titles mentioned in the earlier summaries below. Find one that was MENTIONED but not yet retrieved as its own article. Never output "N/A".

User: Claim: ${claim}

Titles found in first retrieval:
${steps.summarize_hop1.output}

What is still missing:
${steps.summarize_hop2.output}

Previous queries tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

Look at the names listed in the summaries above. Pick a proper noun, person name, or title that was MENTIONED but whose Wikipedia article has not been retrieved yet. Output just that name as the query.
