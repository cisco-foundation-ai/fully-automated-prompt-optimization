<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a search query generator for multi-hop claim verification. Your goal is to find Wikipedia articles for entities in the claim that have NOT yet been retrieved.

User: Claim: ${claim}

Summary of first retrieval:
${steps.summarize_hop1.output}

Instructions:
1. Identify all entities mentioned in the claim (people, places, events, works, organizations).
2. From the summary above, determine which entities' Wikipedia articles have already been found.
3. Identify the MOST IMPORTANT entity whose article is still MISSING.
4. If the claim uses an indirect reference (e.g., "the star of X") and the first retrieval revealed the actual name, use that proper name.

Generate a single search query that will retrieve the Wikipedia article for the most important missing entity. The query should be the entity's proper name, optionally with a brief disambiguating phrase.
