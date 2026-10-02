<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for fact-checking. Given a claim and articles already found, you identify the next entity to search for.

User: Claim: ${claim}

Titles already retrieved: ${steps.summarize_hop1.output}

Instructions:
- Read the claim and the TITLES FOUND above
- List proper nouns in the claim (people, places, movies, bands, organizations, events)
- Pick the proper noun most important for verifying this claim that does NOT appear in TITLES FOUND
- If the claim describes someone indirectly (e.g., "the star of X"), and you can identify them from KEY FACTS, use their actual name
- Output ONLY that name (1-5 words, nothing else)

Search query:
