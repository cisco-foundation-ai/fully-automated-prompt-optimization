<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles. Your job is to identify entities mentioned in retrieved passages that could lead to finding additional relevant articles.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Analyze the passages and produce:
1. A brief summary of the key facts relevant to the claim (2-3 sentences)
2. A list of specific entity names (people, places, organizations, films, albums, events, etc.) that are mentioned or implied by the passages and could have their own Wikipedia article. List each on its own line prefixed with "ENTITY:" — use the exact name as it would appear as a Wikipedia article title.
