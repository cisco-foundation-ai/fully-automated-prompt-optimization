<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding all relevant Wikipedia articles. Your task is to analyze retrieved passages and identify entities that might have their own Wikipedia articles and are relevant to verifying the claim.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Instructions:
1. First, briefly state which parts of the claim are already supported by the passages and which parts still need evidence (2-3 sentences).
2. Then, list Wikipedia article titles that are referenced or implied by the passages and could help verify the remaining parts of the claim. Focus on entities that BRIDGE between what we already know and what we still need to verify. List each on its own line prefixed with "ENTITY:" using the exact Wikipedia article title format.

Focus especially on: people, films, albums, TV shows, sports events, organizations, and geographic locations that connect different parts of the claim.
