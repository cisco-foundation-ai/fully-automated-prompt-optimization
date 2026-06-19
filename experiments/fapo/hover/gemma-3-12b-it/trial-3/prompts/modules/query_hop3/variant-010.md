<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words) to find the missing Wikipedia article. Copy a proper noun directly from the claim if possible. Never output "N/A".

User: Claim: ${claim}

What has been found so far:
${steps.summarize_hop2.output}

The claim needs a Wikipedia article that hasn't been found yet. What entity name should I search for? Just the query, nothing else.
