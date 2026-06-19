<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a short search query (1-5 words) to find the missing entity. Use proper nouns from the claim. Do not explain. Never output "N/A".

User: Claim: ${claim}

What has been found so far:
${steps.summarize_hop2.output}

Output a search query to find the entity that is still missing. Just the query, nothing else.
