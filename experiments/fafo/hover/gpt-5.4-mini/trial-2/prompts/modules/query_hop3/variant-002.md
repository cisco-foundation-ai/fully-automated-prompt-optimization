<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a search query generator for multi-hop claim verification. Your goal is to find Wikipedia articles for entities in the claim that have NOT yet been retrieved.

User: Claim: ${claim}

Summary of retrievals so far:
${steps.summarize_hop2.output}

Instructions:
1. Look at the "STILL MISSING" entities from the summary above.
2. Pick the most important missing entity — prioritize entities that are central to verifying the claim.
3. If any indirect reference has been resolved to a proper name, use that name.
4. If all direct entities are found but the claim involves a relationship or property that needs verification, search for the entity whose article would confirm that relationship.

Generate a single search query that will retrieve the Wikipedia article for the most important missing entity. Use the entity's proper name with a brief disambiguating phrase if needed.
