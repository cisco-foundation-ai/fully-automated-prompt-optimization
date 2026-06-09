<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You find missing Wikipedia articles for claim verification. The claim mentions several entities — some by name, some indirectly (e.g., "the director of X"). Your job is to identify one entity whose Wikipedia article has not been retrieved yet and output its name as a search query.

User: Claim: ${claim}

What has been found: ${steps.summarize_hop1.output}

Strategy:
- First, check if any entity NAMED in the claim is missing from TITLES FOUND
- If all named entities are found, use the retrieved facts to identify an entity referenced INDIRECTLY in the claim (e.g., if the claim says "the director of X" and X's article reveals the director is "John Smith", search for "John Smith")

Output ONLY the entity name to search (1-5 words):
