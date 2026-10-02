<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles. Your job is to identify entities from new passages that have not been covered yet.

User: Claim: ${claim}

Prior knowledge: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Analyze the new passages and produce:
1. A brief summary of new facts relevant to the claim not already known (2-3 sentences)
2. A list of specific entity names (people, places, organizations, films, albums, events, etc.) that are mentioned or implied and could have their own Wikipedia article but have NOT been directly retrieved yet. List each on its own line prefixed with "ENTITY:" — use the exact name as it would appear as a Wikipedia article title.
