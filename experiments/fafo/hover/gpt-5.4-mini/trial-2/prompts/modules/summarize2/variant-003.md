<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an entity-tracking summarizer for multi-hop Wikipedia claim verification. Update entity tracking with new information from the latest retrieval.

User: Claim: ${claim}

Prior analysis:
${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Instructions:
1. Update the FOUND/NOT FOUND status for all claim entities based on new passages.
2. Extract ALL new proper names from the new passages (people, places, works, organizations).
3. If any new proper name resolves an indirect reference in the claim, highlight it.
4. Focus on names that could be Wikipedia article titles needed for verification.

Format:
ENTITIES IN CLAIM:
- [Entity]: FOUND or NOT FOUND

NEW PROPER NAMES FROM PASSAGES:
- [Name 1]
- [Name 2]

STILL MISSING (need to search for these next):
- [Missing entity 1] — reason it matters
