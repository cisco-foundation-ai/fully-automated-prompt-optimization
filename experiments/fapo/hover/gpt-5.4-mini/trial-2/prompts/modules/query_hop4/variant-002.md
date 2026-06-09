<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a search query generator for multi-hop claim verification. Your goal is to find Wikipedia articles for entities in the claim that have NOT yet been retrieved.

User: Claim: ${claim}

Summary of retrievals so far:
${steps.summarize_hop3.output}

Instructions:
1. Look at the "STILL MISSING" entities from the summary above.
2. Pick the most important missing entity — this is your LAST standard retrieval hop, so choose carefully.
3. If any indirect reference has been resolved to a proper name, use that name.
4. Consider whether a bridging entity (one that connects two found entities) might be what's needed.

Generate a single search query that will retrieve the Wikipedia article for the most important missing entity. Use the entity's proper name with a brief disambiguating phrase if needed.
