<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for fact-checking. Given a claim and what has been found so far, generate a search query for the next missing entity.

User: Claim: ${claim}

Titles already retrieved: ${steps.summarize_hop1.output}

Instructions:
- Read the claim and identify all proper nouns (people, places, works, organizations, events)
- Check which ones are already in TITLES FOUND above
- Pick one that is NOT in TITLES FOUND — prefer the one most central to verifying the claim
- If the claim references someone indirectly (e.g., "the director of X"), check KEY FACTS for their actual name

Search query (1-5 words, entity name only):
