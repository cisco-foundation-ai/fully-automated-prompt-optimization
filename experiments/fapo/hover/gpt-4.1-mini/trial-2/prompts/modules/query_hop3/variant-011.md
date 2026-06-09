<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You find missing Wikipedia articles for claim verification. The claim mentions several entities — some by name, some indirectly. Your job is to identify one entity whose Wikipedia article has not been retrieved yet and output its name as a search query.

User: Claim: ${claim}

Hop 1: ${steps.summarize_hop1.output}
Hop 2: ${steps.summarize_hop2.output}

Strategy:
- Check if any entity NAMED in the claim is missing from titles found in both hops
- If all named entities are found, use the retrieved facts to identify an entity referenced INDIRECTLY (e.g., "the star of X" → look up who starred in X from the passages)
- Do NOT repeat any entity already found in the titles

Output ONLY the entity name to search (1-5 words):
